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
from pathlib import Path
import webbrowser

# Third party packages
from colorama import Fore, Style

# pypl2mp3 libs
from pypl2mp3.libs.repository import getSongFiles
from pypl2mp3.libs.song import Song
from pypl2mp3.libs.utils import LabelMaker, CounterMaker, formatSongLabel


def visitSongUrls(args):
    """
    Open the YouTube URL of a song in a browser
    """
    
    repositoryPath = Path(args.repo)
    keywords = args.keywords
    verbose = args.verbose
    songFiles = getSongFiles(
        repositoryPath, 
        keywords = keywords, 
        filterMatchThreshold = args.match,
        playlistIdentifier = args.playlist, 
        displaySummary = True)
    songCount = len(songFiles)
    counterMaker = CounterMaker(songCount)
    songIndex = 0
    for songPathname in songFiles:
        songIndex += 1
        counter = counterMaker.format(songIndex)
        song = Song(songPathname)
        print('\n' + formatSongLabel(counter, song))
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
        if input(
            f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to open video for this song {Style.RESET_ALL} '
            + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') == 'yes':
                songUrl = f'https://youtu.be/{song.youtubeId}'
                webbrowser.open(songUrl, new=0, autoraise=True)
                