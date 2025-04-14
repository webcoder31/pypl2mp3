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
import re

# Third party packages
from colorama import Fore, Back, Style

# pypl2mp3 libs
from pypl2mp3.libs.utils import ProgressCounter, get_deterministic_sort_key


def listPlaylists(args):
    """
    List playlists
    """
    
    repository_path = Path(args.repo)
    playlistPaths = [Path(path) for path in list(
        filter(re.compile(r'^.*\[(.?[^\]]+)\]$').match, [str(dir) for dir in repository_path.glob(f'*/')]))]
    playlistPaths.sort(key = get_deterministic_sort_key)
    playlistCount = len(playlistPaths)
    if playlistCount == 0:
        raise Exception(f'No playlist found in repository.')
    print(f'\n{Back.GREEN + Style.BRIGHT}Found {len(playlistPaths)} playlists in repository.{Style.RESET_ALL}')
    progress_counter = ProgressCounter(playlistCount)
    playlistIndex = 0
    for playlistPath in playlistPaths:
        playlistIndex += 1
        counter = progress_counter.format(playlistIndex)
        allSongFiles = list(playlistPath.glob('*.mp3'))
        junkSongFiles = list(playlistPath.glob('* (JUNK).mp3'))
        print(f'\n{counter} {Fore.LIGHTYELLOW_EX}{playlistPath.name}{Fore.RESET}')
        print(f' '.ljust(10 + 1, ' ') + f'{Style.BRIGHT}Number of well tagged songs .... ' 
            + f'{len(allSongFiles) - len(junkSongFiles)}{Style.RESET_ALL}')
        print(f' '.ljust(10 + 1, ' ') + f'{Style.BRIGHT}Number of junk songs ........... ' 
            + f'{len(junkSongFiles)}{Style.RESET_ALL}')
        print(f' '.ljust(10 + 1, ' ') + f'{Fore.CYAN}Total .......................... ' 
            + f'{len(allSongFiles)}{Fore.RESET}')