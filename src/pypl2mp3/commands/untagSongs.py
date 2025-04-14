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
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import ProgressCounter, format_song_display


def untagSongs(args):
    """
    Remove ID3 tags from songs
    """
    
    repository_path = Path(args.repo)
    promptToConfirm = False
    promptToConfirm = args.prompt
    keywords = args.keywords
    songFiles = get_repository_song_files(
        repository_path,
        keywords = keywords,
        filter_match_threshold = args.match,
        playlist_identifier = args.playlist,
        display_summary = True)
    songCount = len(songFiles)
    progress_counter = ProgressCounter(songCount)
    if not promptToConfirm and input(
        f'\n{Style.BRIGHT}{Fore.LIGHTBLUE_EX}This will untag all songs found. Continue {Style.RESET_ALL} '
        + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') != 'yes':
            return
    song_index = 0
    for songPathname in songFiles:
        song_index += 1
        counter = progress_counter.format(song_index)
        song = SongModel(songPathname)
        print(f'\n{format_song_display(counter, song)}  ' 
            + f'{Fore.WHITE + Style.DIM}[https://youtu.be/{song.youtube_id}]')
        if promptToConfirm and input(
            f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to untag this song{Style.RESET_ALL} '
            + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') != 'yes':
                continue
        song.reset_state()
        song.fix_filename()
        print(f'Song untagged and renamed to: {Fore.LIGHTCYAN_EX}{song.filename}{Fore.RESET}')