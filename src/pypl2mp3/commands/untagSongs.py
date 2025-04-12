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

# Third party packages
from colorama import Fore, Style

# pypl2mp3 libs
from pypl2mp3.libs.repository import getSongFiles
from pypl2mp3.libs.song import Song
from pypl2mp3.libs.utils import CounterMaker, formatSongLabel


def untagSongs(args):
    """
    Remove ID3 tags from songs
    """
    
    repositoryPath = Path(args.repo)
    promptToConfirm = False
    promptToConfirm = args.prompt
    keywords = args.keywords
    songFiles = getSongFiles(
        repositoryPath,
        keywords = keywords,
        filterMatchThreshold = args.match,
        playlistIdentifier = args.playlist,
        displaySummary = True)
    songCount = len(songFiles)
    counterMaker = CounterMaker(songCount)
    if not promptToConfirm and input(
        f'\n{Style.BRIGHT}{Fore.LIGHTBLUE_EX}This will untag all songs found. Continue {Style.RESET_ALL} '
        + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') != 'yes':
            return
    songIndex = 0
    for songPathname in songFiles:
        songIndex += 1
        counter = counterMaker.format(songIndex)
        song = Song(songPathname)
        print(f'\n{formatSongLabel(counter, song)}  ' 
            + f'{Fore.WHITE + Style.DIM}[https://youtu.be/{song.youtubeId}]')
        if promptToConfirm and input(
            f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to untag this song{Style.RESET_ALL} '
            + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') != 'yes':
                continue
        song.resetState()
        song.fixFilename()
        print(f'Song untagged and renamed to: {Fore.LIGHTCYAN_EX}{song.filename}{Fore.RESET}')