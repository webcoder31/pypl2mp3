#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides the main entry point for the pypl2mp3 application.
It handles command-line interface (CLI) parsing and execution of various
commands including importing playlists, listing songs, tagging, and 
playing music.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
import argparse
import asyncio
import datetime
import os
from pathlib import Path
import shutil
import signal
import sys

# Third party packages
from colorama import Fore, Style, init
from rich_argparse import RichHelpFormatter
from rich.markdown import Markdown # NOTE: installed along with rich_argparse package

# pypl2mp3 libs
from pypl2mp3.libs.song import SongError


def _handle_sigint(signal, frame = None):
    """
    Handle CTRL+C (sigint) to exit properly
    """

    sys.stderr.write(f"\n\n{Fore.RED}PYPL2MP3 EXITED AT " 
        + f"{(datetime.datetime.now()).time().strftime('%H:%M:%S')}{Fore.RESET}\n\n")
    sys.exit(0)


def _check_required_binaries(commands: list[str]) -> None:
    """
    Verify required system binaries are installed.

    Args:
        commands: List of binaries to check via "which".

    Raises:
        SystemExit: Exits with code 1 if any binary is missing.
    """

    missing = False

    for cmd in commands:

        if shutil.which(cmd) is None:
            sys.stderr.write(f"Error: PYPL2MP3 requires \"{cmd}\" to be installed\n")
            missing = True

    if missing:
        sys.exit(1)


async def _run_import_playlist(args: argparse.Namespace) -> None:
    """
    Runner for the "import" command.

    Args:
        args: Parsed arguments.
    """

    from pypl2mp3.commands.import_playlist import import_playlist

    try:
        await import_playlist(args)
    except KeyboardInterrupt:
        sys.stdout.write("\010\010  ")
        _handle_sigint(signal.SIGINT)


def _run_list_playlists(args: argparse.Namespace) -> None:
    """
    Runner for the "playlists" command.

    Args:
        args: Parsed arguments.
    """

    from pypl2mp3.commands.list_playlists import list_playlists

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)
    list_playlists(args)


def _run_list_songs(args: argparse.Namespace) -> None:
    """
    Runner for the "songs" command.

    Args:
        args: Parsed arguments.
    """

    from pypl2mp3.commands.list_songs import list_songs

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)
    list_songs(args)


def _run_list_junk_songs(args: argparse.Namespace) -> None:
    """
    Runner for the "junks" command.

    Args:
        args: Parsed arguments.
    """
    from pypl2mp3.commands.list_junk_songs import list_junk_songs

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)
    list_junk_songs(args)


async def _run_tag_junk_songs(args: argparse.Namespace) -> None:
    """
    Runner for the "tag" command.

    Args:
        args: Parsed arguments.
    """

    from pypl2mp3.commands.tag_junk_songs import tag_junk_songs

    try:
        await tag_junk_songs(args)
    except KeyboardInterrupt:
        sys.stdout.write("\010\010  ")
        _handle_sigint(signal.SIGINT)


def _run_untag_songs(args: argparse.Namespace) -> None:
    """
    Runner for the "untag" command.

    Args:
        args: Parsed arguments.
    """

    from pypl2mp3.commands.untag_songs import untag_songs

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)
    untag_songs(args)


def _run_browse_videos(args: argparse.Namespace) -> None:
    """
    Runner for the "videos" command.

    Args:
        args: Parsed arguments.
    """

    from pypl2mp3.commands.browse_videos import browse_videos
    
    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)
    browse_videos(args)


def _run_play_songs(args: argparse.Namespace) -> None:
    """
    Runner for the "play" command.

    Args:
        args: Parsed arguments.
    """

    from pypl2mp3.commands.play_songs import play_songs

    try:
        play_songs(args)
    except KeyboardInterrupt:
        sys.stdout.write("\010\010  ")
        _handle_sigint(signal.SIGINT)


class CliParser(argparse.ArgumentParser):
    """
    Extends Argparse argument parser to define custom error handler
    """

    def error(self, message):
        """
        Custom error handler for argument parser
        """
        
        sys.stderr.write(f"{Fore.RED}Error: {message}{Fore.RESET}\n\n")
        self.print_usage()
        print("\n ")
        sys.exit(2)


def main():
    """
    Parse cli and run the module corrresponding to the invoked command
    """

    # Get the default repository path from environment variable or user home
    defaul_rRepository_path = os.environ.get("PYPL2MP3_DEFAULT_REPOSITORY_PATH")

    if defaul_rRepository_path == None:
        defaul_rRepository_path = Path.home().joinpath("pypl2mp3")
    else:
        defaul_rRepository_path = Path(defaul_rRepository_path.replace("~", str(Path.home())))

    # Get the default playlist ID from environment variable
    default_playlist_id = os.environ.get("PYPL2MP3_DEFAULT_PLAYLIST_ID")

    # CLI main parser
    description_md = Markdown(
        markup=(
            f"**PYPL2MP3 - YouTube playlist MP3 converter that can "
            "also shazam, tag and play songs.**\n"
            "\n**Features:**\n"
            "- Import songs of YouTube playlists in MP3 format\n"
            "- Automatically \"shazam\" songs for ID3 tags with cover art\n"
            "- Manually set or fix ID3 tags for unmatched songs\n"
            "- List playlists and songs with detailed information\n"
            "- Play MP3 songs from CLI and open videos in browser\n"
            "- Filter and sort via fuzzy search in MP3 playlists\n"
            "\n**Current configuration:**\n"
            f"- Repository: {defaul_rRepository_path}\n"
            f"- Favorite playlist ID: {default_playlist_id}\n"
        )
    )

    epilog_md = Markdown(
        markup="PYPL2MP3 © 2025 - **Thierry Thiers** (<webcoder31@gmail.com>)"
    )

    cliParser = CliParser(
        add_help=False,
        description=description_md,
        epilog=epilog_md, 
        formatter_class=RichHelpFormatter
    )
    cliParser.add_argument(
        "-h", "--help", 
        action="help", 
        default=argparse.SUPPRESS,
        help="Get help (for a command, type: <command> -h)"
    )


    # Add command subparsers to main parser
    subparsers = cliParser.add_subparsers(
        dest="command", 
        help=f"{Fore.LIGHTGREEN_EX}--- AVAILABLE COMMANDS ---", 
        required=True
    )

    # Set options shared by all program commands
    shared_options_parser = argparse.ArgumentParser(add_help=False)
    shared_options_parser.add_argument(
        "-r", "--repo", 
        metavar="path", 
        type=str,
        default=str(defaul_rRepository_path),
        help="Folder where playlists are stored (DEFAULT: \"" \
            + str(defaul_rRepository_path) + "\")"
    )


    # CLI parser for command "import"
    import_playlist_command = subparsers.add_parser(
        "import", 
        parents=[shared_options_parser],
        help="Import a YouTube playlist in MP3 format",
        description="Import a YouTube playlist in MP3 format",
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )
    import_playlist_command.add_argument(
        "playlist", 
        nargs="?" if default_playlist_id else 1,  # optional if default exists
        metavar="playlist", 
        type=str,
        default=default_playlist_id,
        help=f"YouTube playlist ID or URL or INDEX (DEFAULT: \"{default_playlist_id}\")"
    )
    import_playlist_command.add_argument(
        "-f", "--filter", 
        metavar="inputs", 
        dest="keywords",
        type=str,
        default="",
        help="Filter songs to import using keywords"
    )
    import_playlist_command.add_argument(
        "-m", "--match", 
        metavar="level", 
        type=int,
        default=45,
        help="Filter match threshold (0-100, DEFAULT: 45)"
    )
    import_playlist_command.add_argument(
        "-t", "--thresh", 
        metavar="level", 
        type=int,
        default=50,
        help="Shazam match threshold (0-100, DEFAULT: 50)"
    )
    import_playlist_command.add_argument(
        "-p", "--prompt", 
        action="store_true",
        default=False,
        help="Prompt before importing each new song"
    )

    import_playlist_command.set_defaults(
        func=lambda args: asyncio.run(_run_import_playlist(args))
    )


    # CLI parser for command "playlists"
    list_playlists_command = subparsers.add_parser(
        'playlists', 
        parents=[shared_options_parser],
        help='List created MP3 playlists',
        description='List created MP3 playlists',
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )

    list_playlists_command.set_defaults(func=_run_list_playlists)


    # CLI parser for command "songs"
    list_songs_command = subparsers.add_parser(
        "songs", 
        parents=[shared_options_parser],
        help="List songs in MP3 playlists",
        description="List songs in MP3 playlists",
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )
    list_songs_command.add_argument(
        "-l", "--list", 
        metavar="playlist", 
        dest="playlist",
        type=str,
        default=None,
        help="Specify a particular playlist by its ID or URL or INDEX"
    )
    list_songs_command.add_argument(
        "-f", "--filter", 
        metavar="inputs", 
        dest="keywords",
        type=str,
        default="",
        help="Filter songs using keywords and sort by relevance"
    )
    list_songs_command.add_argument(
        "-m", "--match", 
        metavar="level", 
        type=int,
        default=45,
        help="Filter match threshold (0-100, DEFAULT: 45)"
    )
    list_songs_command.add_argument(
        "-v", "--verbose", 
        action="store_true",
        default=False,
        help="Enable verbose output"
    )

    list_songs_command.set_defaults(func=_run_list_songs)


    # CLI parser for command "junks"
    list_junk_ongs_command = subparsers.add_parser(
        "junks", 
        parents=[shared_options_parser],
        help="List junk songs in MP3 playlists",
        description="List junk songs in MP3 playlists",
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )
    list_junk_ongs_command.add_argument(
        "-l", "--list", 
        metavar="playlist", 
        dest="playlist",
        type=str,
        default=None,
        help="Specify a particular playlist by its ID or URL or INDEX"
    )
    list_junk_ongs_command.add_argument(
        "-f", "--filter", 
        metavar="inputs", 
        dest="keywords",
        type=str,
        default="",
        help="Filter songs using keywords and sort by relevance"
    )
    list_junk_ongs_command.add_argument(
        "-m", "--match", 
        metavar="level", 
        type=int,
        default=45,
        help="Filter match threshold (0-100, DEFAULT: 45)"
    )
    list_junk_ongs_command.add_argument(
        "-v", "--verbose", 
        action="store_true",
        default=False,
        help="Enable verbose output"
    )

    list_junk_ongs_command.set_defaults(func=_run_list_junk_songs)


    # CLI parser for command "tag"
    tag_unk_songs_command = subparsers.add_parser(
        "tag", 
        parents=[shared_options_parser],
        help="Tag junk songs of MP3 playlists",
        description="Add ID3 tags and cover art then rename junk songs",
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )
    tag_unk_songs_command.add_argument(
        "-l", "--list", 
        metavar="playlist", 
        dest="playlist",
        type=str,
        default=None,
        help="Specify a particular playlist by its ID or URL or INDEX"
    )
    tag_unk_songs_command.add_argument(
        "-t", "--thresh", 
        metavar="level", 
        type=int,
        default=50,
        help="Shazam match threshold (0-100, DEFAULT: 50)"
    )
    tag_unk_songs_command.add_argument(
        "-f", "--filter", 
        metavar="inputs", 
        dest="keywords",
        type=str,
        default="",
        help="Filter songs using keywords and sort by relevance"
    )
    tag_unk_songs_command.add_argument(
        "-m", "--match", 
        metavar="level", 
        type=int,
        default=45,
        help="Filter match threshold (0-100, DEFAULT: 45)"
    )
    tag_unk_songs_command.add_argument(
        "-p", "--prompt", 
        action="store_true",
        default=False,
        help="Prompt to tag each junk songs"
    )

    tag_unk_songs_command.set_defaults(
        func=lambda args: asyncio.run(_run_tag_junk_songs(args))
    )


    # CLI parser for command "untag"
    untag_songs_command = subparsers.add_parser(
        "untag", 
        parents=[shared_options_parser],
        help="Untag playlist MP3 files",
        description="Remove ID3 tags and cover art then rename songs as junk",
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )
    untag_songs_command.add_argument(
        "-l", "--list", 
        metavar="playlist", 
        dest="playlist",
        type=str,
        default=None,
        help="Specify a particular playlist by its ID or URL or INDEX"
    )
    untag_songs_command.add_argument(
        "-f", "--filter", 
        metavar="inputs", 
        dest="keywords",
        type=str,
        default="",
        help="Filter songs using keywords and sort by relevance"
    )
    untag_songs_command.add_argument(
        "-m", "--match", 
        metavar="level", 
        type=int,
        default=45,
        help="Filter match threshold (0-100, DEFAULT: 45)"
    )
    untag_songs_command.add_argument(
        "-p", "--prompt", 
        action="store_true",
        default=False,
        help="Prompt to untag each songs"
    )

    untag_songs_command.set_defaults(func=_run_untag_songs)


    # CLI parser for command "videos"
    browse_videos_command = subparsers.add_parser(
        "videos", 
        parents=[shared_options_parser],
        help="Open song videos on YouTube",
        description="Open song videos on YouTube",
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )
    browse_videos_command.add_argument(
        "-l", "--list", 
        metavar="playlist", 
        dest="playlist",
        type=str,
        default=None,
        help="Specify a particular playlist by its ID or URL or INDEX"
    )
    browse_videos_command.add_argument(
        "-f", "--filter", 
        metavar="inputs", 
        dest="keywords",
        type=str,
        default="",
        help="Filter songs using keywords and sort by relevance"
    )
    browse_videos_command.add_argument(
        "-m", "--match", 
        metavar="level", 
        type=int,
        default=45,
        help="Filter match threshold (0-100, DEFAULT: 45)"
    )
    browse_videos_command.add_argument(
        "-v", "--verbose", 
        action="store_true",
        default=False,
        help="Enable verbose output"
    )

    browse_videos_command.set_defaults(func=_run_browse_videos)


    # CLI parser for command "play"
    play_songs_command = subparsers.add_parser(
        "play", 
        parents=[shared_options_parser],
        help="Play MP3 files from imported playlists",
        description="Play MP3 files from imported playlists",
        epilog=epilog_md, 
        formatter_class=cliParser.formatter_class
    )
    play_songs_command.add_argument(
        "keywords", 
        nargs="?",
        metavar="filter", 
        type=str,
        default="",
        help="Filter songs using keywords and sort by relevance"
    )
    play_songs_command.add_argument(
        "-m", "--match", 
        metavar="level", 
        type=int,
        default=45,
        help="Filter match threshold (0-100, DEFAULT: 45)"
    )
    play_songs_command.add_argument(
        "index", 
        nargs="?",
        metavar="index", 
        type=int,
        default=None,
        help="INDEX of song to play among selected songs (0: random song)"
    )
    play_songs_command.add_argument(
        "-l", "--list", 
        metavar="playlist", 
        dest="playlist",
        type=str,
        default=None,
        help="Specify a particular playlist by its ID or URL or INDEX"
    )
    play_songs_command.add_argument(
        "-s", "--shuffle", 
        dest="shuffle",
        action="store_true",
        default=False,
        help="Play songs in random order"
    )
    play_songs_command.add_argument(
        "-v", "--verbose", 
        action="store_true",
        default=False,
        help="Enable verbose output"
    )

    play_songs_command.set_defaults(
        func=lambda args: asyncio.run(_run_play_songs(args))
    )


    # Parse CLI
    print()
    args = cliParser.parse_args(args=None if sys.argv[1:] else ["--help"])

    # Automatically reset sequences to turn off color changes at the end of every print
    init(autoreset = True)

    # Log start of program execution
    print(f"{Fore.LIGHTGREEN_EX}PYPL2MP3 STARTED AT " 
        + f"{(datetime.datetime.now()).time().strftime('%H:%M:%S')}{Fore.RESET}\n")
    
    print(f"{Fore.WHITE + Style.DIM} ⇨ Playlists repository:  {Style.RESET_ALL}"
        + f"{Fore.LIGHTBLUE_EX}{defaul_rRepository_path}{Fore.RESET}")
    
    print(f"{Fore.WHITE + Style.DIM} ⇨ Favorite playlist ID:  {Style.RESET_ALL}"
        + f"{Fore.LIGHTBLUE_EX}{default_playlist_id}{Fore.RESET}")

    # Check binaries for relevant commands
    if args.command in {"import", "tag", "untag"}:
        _check_required_binaries(["ffmpeg", "ffprobe", "node"])

    # Execute appropriate command runner
    try:
        args.func(args)
    except SongError as error:
        # Catch any Song error, print it and exit
        print(f"\n{Fore.RED}FATAL ERROR!", error, f"{Fore.RESET}")
        # raise
    except Exception as error:
        # Catch any unhandled error, print it and raise it
        print(f"\n{Fore.RED}FATAL ERROR!", type(error).__name__, "-", error, f"{Fore.RESET}")
        raise

    # Log end of program execution
    print(f"\n{Fore.LIGHTGREEN_EX}PYPL2MP3 FINISHED AT " 
        + f"{(datetime.datetime.now()).time().strftime('%H:%M:%S')}{Fore.RESET}\n\n")


# Main entry point
# This allows the module to be run as a script or imported
# without executing the main function, to be used in other modules
if __name__ == "__main__":
    main()
