#!/usr/bin/env python3

"""
This file is part of PYPL2MP3 software, 
a YouTube playlist MP3 converter that can also shazam, tag and play songs.

@author    Thierry Thiers <webcoder31@gmail.com>
@copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
@license   http://www.cecill.info  CeCILL-C License
@link      https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
import os
from pathlib import Path
import random
from threading import Thread
import webbrowser

# Hide pygame support prompt (should be done before loading pygame module)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Third party packages
from colorama import Fore, Style
import pygame
from sshkeyboard import listen_keyboard, stop_listening

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import LabelFormatter, ProgressCounter, format_song_display

# Global variables
songFiles = None
songCount = 0
song_index = 0
songUrl = None
songPlayerThread = None
isSongPlayerRunning = False
isSongPlayerPaused = False
playDirection = 'forward'
progress_counter = None
verbose = False


def runSongPlayer():
    """
    Run song player
    """

    global song_index
    global songUrl
    global isSongPlayerRunning

    while True:
        pygame.mixer.music.stop() # Stop music in case is playing something
        step = (-1, 1)[playDirection == 'forward']
        song_index += step
        song_index = (song_index + songCount) % (2 * songCount) - songCount
        if song_index < 0:
            song_index = songCount + song_index
        songFile = songFiles[song_index]
        counter = progress_counter.format(song_index)
        song = SongModel(songFile)
        songUrl = f'https://youtu.be/{song.youtube_id}'
        print('\033[2K\033[1G', end = '\r') # Erase and go to beginning of line
        print(format_song_display(counter, song))
        if verbose:
            label_formatter = LabelFormatter(9)
            print(progress_counter.placeholder() + '  '
                + label_formatter.format('Playlist')
                + f'{Fore.LIGHTBLUE_EX}{song.playlist}{Fore.RESET}')
            print(progress_counter.placeholder() + '  '
                + label_formatter.format('Filename')
                + f'{Fore.LIGHTBLUE_EX}{song.filename}{Fore.RESET}')
            print(progress_counter.placeholder() + '  '
                + label_formatter.format('Link')
                + f'{Fore.LIGHTBLUE_EX}https://youtu.be/{song.youtube_id}{Fore.RESET}')
        nextSongIndex = song_index + step
        nextSongIndex = (nextSongIndex + songCount) % (2 * songCount) - songCount
        if nextSongIndex < 0:
            nextSongIndex = songCount + nextSongIndex
        nextSongFile = songFiles[nextSongIndex]
        nextCounter = progress_counter.placeholder(('<--', '-->')[playDirection == 'forward'])
        nextSong = SongModel(nextSongFile)
        print(('', '\n')[verbose] + f'{nextCounter}  '
            + f'{Fore.WHITE + Style.DIM}{nextSong.duration}  {Style.RESET_ALL}'
            + f'{Fore.WHITE + Style.DIM}{nextSong.artist}  {Style.RESET_ALL}'
            + f'{Fore.WHITE + Style.DIM}{nextSong.title}{Style.RESET_ALL}'
            + f'{Fore.WHITE + Style.DIM}{("", " (JUNK)")[nextSong.has_junk_filename]}  {Style.RESET_ALL}', end = '', flush = True)
        try:
            pygame.mixer.music.load(songFile)
            pygame.mixer.music.play()
            clock = pygame.time.Clock()
            isSongPlayerRunning = True
            while isSongPlayerRunning and (pygame.mixer.music.get_busy() or isSongPlayerPaused):
                clock.tick(1)
        except pygame.error:
            print(f'\n{Fore.RED}Error playing song: {songFile}{Fore.RESET}')
            pygame.mixer.music.stop()
            stop_listening()
            pygame.quit()
            return


async def controlSongPlayer(key):
    """
    Control song player on key pressed
    """

    global songPlayerThread
    global isSongPlayerRunning
    global isSongPlayerPaused
    global playDirection

    # Run song player forward by jumping to next song
    if key == 'right':
        playDirection = 'forward'
        isSongPlayerRunning = False

    # Run song player backward by jumping to previous song
    if key == 'left':
        playDirection = 'backward'
        isSongPlayerRunning = False

    # Pause / unpause song player
    if key == 'space':
        isSongPlayerPaused = not isSongPlayerPaused
        if isSongPlayerPaused:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()

    # Open current song related video in web browser
    if key == 'tab':
        webbrowser.open(songUrl, new=0, autoraise=True)

    # Exit song player
    if key == 'esc':
        pygame.mixer.music.stop()
        stop_listening()
        pygame.quit()
        songPlayerThread.join()
        

def playSongs(args):
    """
    Play songs
    """

    global verbose
    global songFiles
    global songCount
    global progress_counter
    global songPlayerThread
    
    repository_path = Path(args.repo)
    keywords = args.keywords
    verbose = args.verbose
    songFiles = get_repository_song_files(
        repository_path, 
        keywords = keywords, 
        filter_match_threshold = args.match,
        song_index = args.index, 
        playlist_identifier = args.playlist, 
        display_summary = True)
    print('\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  <--  ]{Style.DIM}  Prev song / Play backward{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  -->  ]{Style.DIM}  Next song / Play forward{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[ SPACE ]{Style.DIM}  Pause song / Play song{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  TAB  ]{Style.DIM}  Open song video in browser{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  ESC  ]{Style.DIM}  Quit player{Fore.RESET + Style.RESET_ALL}\n')
    if (args.shuffle):
        random.shuffle(songFiles)
    songCount = len(songFiles)
    progress_counter = ProgressCounter(songCount)

    # Run song player in a daemon thread
    songPlayerThread = Thread(target = runSongPlayer)
    songPlayerThread.setDaemon(True)
    songPlayerThread.start()

    # Register function that control song player on key pressed
    listen_keyboard(on_press = controlSongPlayer, sequential=True)
