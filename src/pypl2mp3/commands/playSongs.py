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
from pypl2mp3.libs.repository import getSongFiles
from pypl2mp3.libs.song import Song
from pypl2mp3.libs.utils import LabelMaker, CounterMaker, formatSongLabel

# Global variables
songFiles = None
songCount = 0
songIndex = 0
songUrl = None
songPlayerThread = None
isSongPlayerRunning = False
isSongPlayerPaused = False
playDirection = 'forward'
counterMaker = None
verbose = False


def runSongPlayer():
    """
    Run song player
    """

    global songIndex
    global songUrl
    global isSongPlayerRunning

    while True:
        pygame.mixer.music.stop() # Stop music in case is playing something
        step = (-1, 1)[playDirection == 'forward']
        songIndex += step
        songIndex = (songIndex + songCount) % (2 * songCount) - songCount
        if songIndex < 0:
            songIndex = songCount + songIndex
        songFile = songFiles[songIndex]
        counter = counterMaker.format(songIndex)
        song = Song(songFile)
        songUrl = f'https://youtu.be/{song.youtubeId}'
        print('\033[2K\033[1G', end = '\r') # Erase and go to beginning of line
        print(formatSongLabel(counter, song))
        if verbose:
            labelMaker = LabelMaker(9)
            print(counterMaker.placeholder() + '  '
                + labelMaker.format('Playlist')
                + f'{Fore.LIGHTBLUE_EX}{song.playlist}{Fore.RESET}')
            print(counterMaker.placeholder() + '  '
                + labelMaker.format('Filename')
                + f'{Fore.LIGHTBLUE_EX}{song.filename}{Fore.RESET}')
            print(counterMaker.placeholder() + '  '
                + labelMaker.format('Link')
                + f'{Fore.LIGHTBLUE_EX}https://youtu.be/{song.youtubeId}{Fore.RESET}')
        nextSongIndex = songIndex + step
        nextSongIndex = (nextSongIndex + songCount) % (2 * songCount) - songCount
        if nextSongIndex < 0:
            nextSongIndex = songCount + nextSongIndex
        nextSongFile = songFiles[nextSongIndex]
        nextCounter = counterMaker.placeholder(('<--', '-->')[playDirection == 'forward'])
        nextSong = Song(nextSongFile)
        print(('', '\n')[verbose] + f'{nextCounter}  '
            + f'{Fore.WHITE + Style.DIM}{nextSong.duration}  {Style.RESET_ALL}'
            + f'{Fore.WHITE + Style.DIM}{nextSong.artist}  {Style.RESET_ALL}'
            + f'{Fore.WHITE + Style.DIM}{nextSong.title}{Style.RESET_ALL}'
            + f'{Fore.WHITE + Style.DIM}{("", " (JUNK)")[nextSong.hasJunkFilename]}  {Style.RESET_ALL}', end = '', flush = True)
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
    global counterMaker
    global songPlayerThread
    
    repositoryPath = Path(args.repo)
    keywords = args.keywords
    verbose = args.verbose
    songFiles = getSongFiles(
        repositoryPath, 
        keywords = keywords, 
        filterMatchThreshold = args.match,
        songIndex = args.index, 
        playlistIdentifier = args.playlist, 
        displaySummary = True)
    print('\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  <--  ]{Style.DIM}  Prev song / Play backward{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  -->  ]{Style.DIM}  Next song / Play forward{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[ SPACE ]{Style.DIM}  Pause song / Play song{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  TAB  ]{Style.DIM}  Open song video in browser{Fore.RESET + Style.RESET_ALL}\n'
        + f'{Fore.LIGHTMAGENTA_EX}[  ESC  ]{Style.DIM}  Quit player{Fore.RESET + Style.RESET_ALL}\n')
    if (args.shuffle):
        random.shuffle(songFiles)
    songCount = len(songFiles)
    counterMaker = CounterMaker(songCount)

    # Run song player in a daemon thread
    songPlayerThread = Thread(target = runSongPlayer)
    songPlayerThread.setDaemon(True)
    songPlayerThread.start()

    # Register function that control song player on key pressed
    listen_keyboard(on_press = controlSongPlayer, sequential=True)
