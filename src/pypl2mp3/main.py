#!/usr/bin/env python3
"""
This file is part of PYPL2MP3 software, 
a YouTube playlist MP3 converter that can also shazam, tag and play songs.

@author    Thierry Thiers <webcoder31@gmail.com>
@copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
@license   http://www.cecill.info  CeCILL-C License
@link      https://github.com/webcoder31/pypl2mp3
"""

# NOTE: MP3 files are saved in ID3v2.3 only, without ID3v1 (default is ID3v2.4)

# Python core modules
import argparse
import asyncio
import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys


# Third party packages
from colorama import Fore, Style, init
from rich_argparse import RichHelpFormatter
from rich.markdown import Markdown # NOTE: installed along with rich_argparse package

# pypl2mp3 libs
from pypl2mp3.libs.song import SongError


def sigintHandler(signal, frame = None):
    """
    Handle CTRL+C (sigint) to exit properly
    """
    
    sys.stderr.write(f'\n\n{Fore.RED}PYPL2MP3 EXITED AT ' 
        + f'{(datetime.datetime.now()).time().strftime("%H:%M:%S")}{Fore.RESET}\n\n')
    sys.exit(0)


class CliParser(argparse.ArgumentParser):
    """
    Extends Argparse argument parser to define custom error handler
    """
        
    def error(self, message):
        """
        Custom error handler for argument parser
        """
        sys.stderr.write(f'{Fore.RED}Error: {message}{Fore.RESET}\n\n')
        self.print_usage()
        print('\n ')
        sys.exit(2)


def main():
    """
    Parse cli and run the module corrresponding to the invoked command
    """

    # Get the default repository path from environment variable or user home
    defaultRepositoryPath = os.environ.get('PYPL2MP3_DEFAULT_REPOSITORY_PATH')
    if defaultRepositoryPath == None:
        defaultRepositoryPath = Path.home().joinpath('pypl2mp3')
    else:
        defaultRepositoryPath = Path(defaultRepositoryPath.replace('~', str(Path.home())))

    # Get the default playlist ID from environment variable
    defaultPlaylistId = os.environ.get('PYPL2MP3_DEFAULT_PLAYLIST_ID')

    # CLI main parser
    programDescription = Markdown(markup = f"""
**PYPL2MP3 - YouTube playlist MP3 converter that can also shazam, tag and play songs.**

**Features:**
- Import songs of YouTube playlists in MP3 format 
- Automatically "shazam" songs to get and set confirmed ID3 tags with proper cover art
- Manually set or fix ID3 tags to "junk" songs when no match found on Shazam
- List imported songs and playlists with detailed information
- Play MP3 songs from CLI and open related videos in your default web browser
- Filter and sort songs via fuzzy search in MP3 playlists

**Your current configuration:**
- MP3 playlists repository: {defaultRepositoryPath}
- Favorite playlist ID: {defaultPlaylistId}
""")

    programEpilog = Markdown(markup = """
PYPL2MP3 © 2025 - **Thierry Thiers** (<webcoder31@gmail.com>)
""")

    cliParser = CliParser(
        add_help = False,
        description = programDescription,
        epilog = programEpilog, 
        formatter_class=RichHelpFormatter)

    cliParser.add_argument(
        '-h', '--help', 
        action = 'help', 
        default = argparse.SUPPRESS,
        help = 'Get help (for a command, type: <command> -h)')


    # Add command subparsers to main parser
    subparsers = cliParser.add_subparsers(dest = 'command', help = 'commands', required = True)

    # Option shared by all program commands PYPL2MP3_DEFAULT_REPOSITORY_PATH
    sharedArgumentParser = argparse.ArgumentParser(add_help = False)
    sharedArgumentParser.add_argument(
        '-r', '--repo', 
        metavar = 'path', 
        type = str,
        default = str(defaultRepositoryPath),
        help = 'Repository (folder) where playlists are stored (DEFAULT: "' + str(defaultRepositoryPath) + '")')

    # CLI for command "IMPORT"
    importPlaylistCommand = subparsers.add_parser(
        'import', 
        parents = [sharedArgumentParser],
        help = 'Import a YouTube playlist in MP3 format',
        description = 'Import a YouTube playlist in MP3 format',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    isPlaylistIdMandatory = 1
    if defaultPlaylistId:
        isPlaylistIdMandatory = '?'
    importPlaylistCommand.add_argument(
        'playlist', 
        nargs = isPlaylistIdMandatory,
        metavar = 'playlist', 
        type = str,
        default = defaultPlaylistId,
        help = f'YouTube playlist ID or URL or INDEX (DEFAULT: "{defaultPlaylistId}")')

    importPlaylistCommand.add_argument(
        '-t', '--thresh', 
        metavar = 'level', 
        type = int,
        default = 50,
        help = 'Shazam match threshold (0-100, DEFAULT: 50)')

    importPlaylistCommand.add_argument(
        '-f', '--filter', 
        metavar = 'keywords', 
        dest = 'keywords',
        type = str,
        default = '',
        help = 'Filter songs using keywords')
    
    importPlaylistCommand.add_argument(
        '-m', '--match', 
        metavar = 'level', 
        type = int,
        default = 45,
        help = 'Minimum filter match level (0-100, DEFAULT: 45)')

    importPlaylistCommand.add_argument(
        '-p', '--prompt', 
        action = 'store_true',
        default = False,
        help = 'Prompt to import each new song discovered in YouTube playlist')

    def importPlaylistCommandRunner(args):
        from pypl2mp3.commands.importPlaylist import importPlaylist
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(importPlaylist(args))
        except KeyboardInterrupt:
            sys.stdout.write('\010\010  ')
            sigintHandler(signal.SIGINT)
        # # Handler to cancel a task
        # def cancelTask(task):
        #     sys.stdout.write('\010\010  ')
        #     print(f'\n\n{Fore.RED}Task cancelled by user!{Fore.RESET}')
        #     task.cancel()
        #     sigintHandler(signal.SIGINT)
        # # Run command function into an event loop and wait for it to complete
        # task = asyncio.ensure_future(importPlaylist(args))
        # loop = asyncio.get_event_loop()
        # loop.add_signal_handler(signal.SIGINT, lambda: cancelTask(task))
        # loop.add_signal_handler(signal.SIGTERM, lambda: cancelTask(task))
        # loop.run_until_complete(task)
    importPlaylistCommand.set_defaults(func = importPlaylistCommandRunner)

    # CLI for command "PLAYLISTS"
    listPlaylistsCommand = subparsers.add_parser(
        'playlists', 
        parents = [sharedArgumentParser],
        help = 'List created MP3 playlists',
        description = 'List created MP3 playlists',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    def listPlaylistsCommandRunner(args):
        from pypl2mp3.commands.listPlaylists import listPlaylists
        signal.signal(signal.SIGINT, sigintHandler) # Register "sigint" handler
        signal.signal(signal.SIGTERM, sigintHandler) # Register "sigterm" handler
        listPlaylists(args)
    listPlaylistsCommand.set_defaults(func = listPlaylistsCommandRunner)

    # CLI for command "SONGS"
    listSongsCommand = subparsers.add_parser(
        'songs', 
        parents = [sharedArgumentParser],
        help = 'List songs in MP3 playlists',
        description = 'List songs in MP3 playlists',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    listSongsCommand.add_argument(
        '-l', '--list', 
        metavar = 'playlist', 
        dest = 'playlist',
        type = str,
        default = None,
        help = 'Specify a particular playlist by its ID or URL or INDEX')

    listSongsCommand.add_argument(
        '-f', '--filter', 
        metavar = 'keywords', 
        dest = 'keywords',
        type = str,
        default = '',
        help = 'Filter songs using keywords')
    
    listSongsCommand.add_argument(
        '-m', '--match', 
        metavar = 'level', 
        type = int,
        default = 45,
        help = 'Minimum filter match level (0-100, DEFAULT: 45)')

    listSongsCommand.add_argument(
        '-v', '--verbose', 
        action = 'store_true',
        default = False,
        help = 'Enable verbose output')

    def listSongsCommandRunner(args):
        from pypl2mp3.commands.listSongs import listSongs
        signal.signal(signal.SIGINT, sigintHandler) # Register "sigint" handler
        signal.signal(signal.SIGTERM, sigintHandler) # Register "sigterm" handler
        listSongs(args)
    listSongsCommand.set_defaults(func = listSongsCommandRunner)

    # CLI for command "JUNKS"
    listJunkSongsCommand = subparsers.add_parser(
        'junks', 
        parents = [sharedArgumentParser],
        help = 'List junk songs in MP3 playlists',
        description = 'List junk songs in MP3 playlists',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    listJunkSongsCommand.add_argument(
        '-l', '--list', 
        metavar = 'playlist', 
        dest = 'playlist',
        type = str,
        default = None,
        help = 'Specify a particular playlist by its ID or URL or INDEX')

    listJunkSongsCommand.add_argument(
        '-f', '--filter', 
        metavar = 'keywords', 
        dest = 'keywords',
        type = str,
        default = '',
        help = 'Filter songs using keywords')
    
    listJunkSongsCommand.add_argument(
        '-m', '--match', 
        metavar = 'level', 
        type = int,
        default = 45,
        help = 'Minimum filter match level (0-100, DEFAULT: 45)')

    listJunkSongsCommand.add_argument(
        '-v', '--verbose', 
        action = 'store_true',
        default = False,
        help = 'Enable verbose output')

    def listJunkSongsCommandRunner(args):
        from pypl2mp3.commands.listJunkSongs import listJunkSongs
        signal.signal(signal.SIGINT, sigintHandler) # Register "sigint" handler
        signal.signal(signal.SIGTERM, sigintHandler) # Register "sigterm" handler
        listJunkSongs(args)
    listJunkSongsCommand.set_defaults(func = listJunkSongsCommandRunner)

    # CLI for command "TAG"
    tagJunkSongsCommand = subparsers.add_parser(
        'tag', 
        parents = [sharedArgumentParser],
        help = 'Tag junk songs of MP3 playlists',
        description = 'Add ID3 tags and cover art then rename junk songs',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    tagJunkSongsCommand.add_argument(
        '-l', '--list', 
        metavar = 'playlist', 
        dest = 'playlist',
        type = str,
        default = None,
        help = 'Specify a particular playlist by its ID or URL or INDEX')

    tagJunkSongsCommand.add_argument(
        '-t', '--thresh', 
        metavar = 'level', 
        type = int,
        default = 50,
        help = 'Shazam match threshold (0-100, DEFAULT: 50)')

    tagJunkSongsCommand.add_argument(
        '-f', '--filter', 
        metavar = 'keywords', 
        dest = 'keywords',
        type = str,
        default = '',
        help = 'Filter songs using keywords')
    
    tagJunkSongsCommand.add_argument(
        '-m', '--match', 
        metavar = 'level', 
        type = int,
        default = 45,
        help = 'Minimum filter match level (0-100, DEFAULT: 45)')

    tagJunkSongsCommand.add_argument(
        '-p', '--prompt', 
        action = 'store_true',
        default = False,
        help = 'Prompt to tag each junk songs')

    def tagJunkSongsCommandRunner(args):
        from pypl2mp3.commands.tagJunkSongs import tagJunkSongs
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(tagJunkSongs(args))
        except KeyboardInterrupt:
            sys.stdout.write('\010\010  ')
            sigintHandler(signal.SIGINT)
        # # Handler to cancel a task
        # def cancelTask(task):
        #     sys.stdout.write('\010\010  ')
        #     print(f'\n\n{Fore.RED}Task cancelled by user!{Fore.RESET}')
        #     task.cancel()
        #     sigintHandler(signal.SIGINT)
        # # Run command function into an event loop and wait for it to complete
        # task = asyncio.ensure_future(tagJunkSongs(args))
        # loop = asyncio.get_event_loop()
        # loop.add_signal_handler(signal.SIGINT, lambda: cancelTask(task))
        # loop.add_signal_handler(signal.SIGTERM, lambda: cancelTask(task))
        # loop.run_until_complete(task)
    tagJunkSongsCommand.set_defaults(func = tagJunkSongsCommandRunner)

    # CLI for command "UNTAG"
    untagSongsCommand = subparsers.add_parser(
        'untag', 
        parents = [sharedArgumentParser],
        help = 'Untag playlist MP3 files',
        description = 'Remove ID3 tags and cover art then rename songs as junk',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    untagSongsCommand.add_argument(
        '-l', '--list', 
        metavar = 'playlist', 
        dest = 'playlist',
        type = str,
        default = None,
        help = 'Specify a particular playlist by its ID or URL or INDEX')

    untagSongsCommand.add_argument(
        '-f', '--filter', 
        metavar = 'keywords', 
        dest = 'keywords',
        type = str,
        default = '',
        help = 'Filter songs using keywords')
    
    untagSongsCommand.add_argument(
        '-m', '--match', 
        metavar = 'level', 
        type = int,
        default = 45,
        help = 'Minimum filter match level (0-100, DEFAULT: 45)')

    untagSongsCommand.add_argument(
        '-p', '--prompt', 
        action = 'store_true',
        default = False,
        help = 'Prompt to untag each songs')

    def untagSongsCommandRunner(args):
        from pypl2mp3.commands.untagSongs import untagSongs
        signal.signal(signal.SIGINT, sigintHandler) # Register "sigint" handler
        signal.signal(signal.SIGTERM, sigintHandler) # Register "sigterm" handler
        untagSongs(args)
    untagSongsCommand.set_defaults(func = untagSongsCommandRunner)

    # CLI for command "VISIT"
    visitSongUrlsCommand = subparsers.add_parser(
        'visit', 
        parents = [sharedArgumentParser],
        help = 'Open song\'s YouTube URL in browser',
        description = 'Open song\'s YouTube URL in browser',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    visitSongUrlsCommand.add_argument(
        '-l', '--list', 
        metavar = 'playlist', 
        dest = 'playlist',
        type = str,
        default = None,
        help = 'Specify a particular playlist by its ID or URL or INDEX')

    visitSongUrlsCommand.add_argument(
        '-f', '--filter', 
        metavar = 'keywords', 
        dest = 'keywords',
        type = str,
        default = '',
        help = 'Filter songs using keywords')
    
    visitSongUrlsCommand.add_argument(
        '-m', '--match', 
        metavar = 'level', 
        type = int,
        default = 45,
        help = 'Minimum filter match level (0-100, DEFAULT: 45)')

    visitSongUrlsCommand.add_argument(
        '-v', '--verbose', 
        action = 'store_true',
        default = False,
        help = 'Enable verbose output')

    def visitSongUrlsCommandRunner(args):
        from pypl2mp3.commands.visitSongUrls import visitSongUrls
        signal.signal(signal.SIGINT, sigintHandler) # Register "sigint" handler
        signal.signal(signal.SIGTERM, sigintHandler) # Register "sigterm" handler
        visitSongUrls(args)
    visitSongUrlsCommand.set_defaults(func = visitSongUrlsCommandRunner)

    # CLI for command "PLAY"
    playSongsCommand = subparsers.add_parser(
        'play', 
        parents = [sharedArgumentParser],
        help = 'Play MP3 files stored in playlists',
        description = 'Play MP3 files stored in playlists',
        epilog = programEpilog, 
        formatter_class=cliParser.formatter_class)

    playSongsCommand.add_argument(
        'keywords', 
        nargs = '?',
        metavar = 'filter', 
        type = str,
        default = '',
        help = 'Filter songs using keywords')
    
    playSongsCommand.add_argument(
        '-m', '--match', 
        metavar = 'level', 
        type = int,
        default = 45,
        help = 'Minimum filter match level (0-100, DEFAULT: 45)')

    playSongsCommand.add_argument(
        'index', 
        nargs = '?',
        metavar = 'index', 
        type = int,
        default = None,
        help = 'INDEX of song to play among selected songs (0: random song)')

    playSongsCommand.add_argument(
        '-l', '--list', 
        metavar = 'playlist', 
        dest = 'playlist',
        type = str,
        default = None,
        help = 'Specify a particular playlist by its ID or URL or INDEX')

    playSongsCommand.add_argument(
        '-s', '--shuffle', 
        dest = 'shuffle',
        action='store_true',
        default = False,
        help = 'Play songs in random order')

    playSongsCommand.add_argument(
        '-v', '--verbose', 
        action = 'store_true',
        default = False,
        help = 'Enable verbose output')

    def playSongCommandRunner(args):
        from pypl2mp3.commands.playSongs import playSongs
        signal.signal(signal.SIGINT, sigintHandler) # Register "sigint" handler
        signal.signal(signal.SIGTERM, sigintHandler) # Register "sigterm" handler
        playSongs(args)
    playSongsCommand.set_defaults(func = playSongCommandRunner)

    # Parse CLI
    print()
    args = cliParser.parse_args(args=None if sys.argv[1:] else ['--help'])

    # Automatically reset sequences to turn off color changes at the end of every print
    init(autoreset = True)

    # Log start of program execution
    print(f'{Fore.LIGHTGREEN_EX}PYPL2MP3 STARTED AT ' 
        + f'{(datetime.datetime.now()).time().strftime("%H:%M:%S")}{Fore.RESET}\n')
    print(f'{Fore.WHITE + Style.DIM} ⇨ Playlists repository:  {Style.RESET_ALL}'
        + f'{Fore.LIGHTBLUE_EX}{defaultRepositoryPath}{Fore.RESET}')
    print(f'{Fore.WHITE + Style.DIM} ⇨ Favorite playlist ID:  {Style.RESET_ALL}'
        + f'{Fore.LIGHTBLUE_EX}{defaultPlaylistId}{Fore.RESET}')

    # Check required binaries for some commands
    if args.command in ['import', 'tag', 'untag']:
        isMissingBinaries = False
        try:
            subprocess.check_output(['which', 'ffmpeg'])
        except Exception as e:
            sys.stderr.write('Error: PYPL2MP3 requires ffmpeg to be installed')
            isMissingBinaries = True
        try:
            subprocess.check_output(['which', 'ffprobe'])
        except Exception as e:
            sys.stderr.write('Error: PYPL2MP3 requires ffprobe to be installed')
            isMissingBinaries = True
        try:
            subprocess.check_output(['which', 'node'])
        except Exception as e:
            sys.stderr.write('Error: PYPL2MP3 requires nodejs to be installed')
            isMissingBinaries = True
        if isMissingBinaries:
            sys.exit(1)

    # Execute invoked command
    try:
        # Run command as a regular synchronous function
        args.func(args)
    except SongError as error:
        # Catch any Song error, print it and exit
        print(f'\n{Fore.RED}FATAL ERROR!', error, f'{Fore.RESET}')
        # raise
    except Exception as error:
        # Catch any unhandled error, print it and raise it
        print(f'\n{Fore.RED}FATAL ERROR!', type(error).__name__, '-', error, f'{Fore.RESET}')
        raise

    # Log end of program execution
    print(f'\n{Fore.LIGHTGREEN_EX}PYPL2MP3 FINISHED AT ' 
        + f'{(datetime.datetime.now()).time().strftime("%H:%M:%S")}{Fore.RESET}\n\n')


# Only parse CLI and run command if program is invoked directly from the shell command line
if __name__ == '__main__':
    main()
