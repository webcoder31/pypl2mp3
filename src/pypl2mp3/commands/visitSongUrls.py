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
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import LabelFormatter, ProgressCounter, format_song_display


def visitSongUrls(args):
    """
    Open the YouTube URL of a song in a browser
    """
    
    repository_path = Path(args.repo)
    keywords = args.keywords
    verbose = args.verbose
    songFiles = get_repository_song_files(
        repository_path, 
        keywords = keywords, 
        filter_match_threshold = args.match,
        playlist_identifier = args.playlist, 
        display_summary = True)
    songCount = len(songFiles)
    progress_counter = ProgressCounter(songCount)
    song_index = 0
    for songPathname in songFiles:
        song_index += 1
        counter = progress_counter.format(song_index)
        song = SongModel(songPathname)
        print('\n' + format_song_display(counter, song))
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
        if input(
            f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to open video for this song {Style.RESET_ALL} '
            + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') == 'yes':
                songUrl = f'https://youtu.be/{song.youtube_id}'
                webbrowser.open(songUrl, new=0, autoraise=True)
                