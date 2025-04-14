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
from types import SimpleNamespace

# Third party packages
from colorama import Fore, Back, Style
from pytubefix import Playlist, YouTube
from thefuzz import fuzz

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_playlist
from pypl2mp3.libs.song import SongModel, SongError
from pypl2mp3.libs.utils import extract_youtube_id_from_filename, extract_youtube_id_from_url, calculate_fuzzy_match_score, LabelFormatter, ProgressCounter


async def importPlaylist(args):
    """
    Sync (or create) a loacal playlist from YouTube 
    """
    
    repository_path = Path(args.repo)
    selectedPlaylist = get_repository_playlist(repository_path, args.playlist, must_exist = False)
    keywords = args.keywords
    filter_match_threshold = args.match
    shazam_match_threshold = args.thresh
    promptToConfirm = args.prompt

    print(f'\n{Fore.LIGHTGREEN_EX}Retrieving playlist content from {selectedPlaylist.url}. \nPlease, wait...\n{Fore.RESET}')
    try:
        playlistData = Playlist(selectedPlaylist.url, 'WEB')
    except Exception as error:
        print(f'\n{Fore.RED}FATAL ERROR!{Fore.RESET} An exception occurs while downloading playlist content: ', 
            type(error).__name__, '–', error)
        return
    if not playlistData:
        print(f'\n{Fore.RED}FATAL ERROR!{Fore.RESET} ' 
            + f'Cannot find or access playlist located at {Fore.RED}{selectedPlaylist.url}{Fore.RESET}.')
        return
    print(f'{Back.YELLOW + Style.BRIGHT} Found {len(playlistData.videos)} accessible videos over {playlistData.length} ' 
        + f'in playlist "{playlistData.title}" of user "{playlistData.owner}". {Style.RESET_ALL}')
    playlistPath = repository_path / f'{playlistData.owner} - {playlistData.title} [{selectedPlaylist.id}]'
    try:
        if not playlistPath.exists():
            playlistPath.mkdir(parents = True)
    except:
        print(f'\n{Fore.RED}FATAL ERROR!{Fore.RESET} Failed to create playlist folder {Fore.RED}{playlistPath}{Fore.RESET}.')
        return
    print()
    shazamedSongReport = []
    junkSongReport = []
    importFailureReport = []
    allSongFiles = frozenset(map(extract_youtube_id_from_filename, list(playlistPath.glob('*.mp3'))))
    junkSongFiles = frozenset(map(extract_youtube_id_from_filename, list(playlistPath.glob('* (JUNK).mp3'))))
    videoIds = frozenset(map(extract_youtube_id_from_url, playlistData.video_urls))
    songCount = len(videoIds) - len(set(allSongFiles) & set(videoIds)) # Number of new songs (not already imported)
    if songCount == 0:
        print(f'\n{Fore.LIGHTYELLOW_EX}No new video to import.{Fore.RESET}')
        return
    print(f'{Fore.LIGHTYELLOW_EX}Number of new videos to import:  {Fore.RESET}'
        + f'{Fore.LIGHTGREEN_EX}{songCount}{Fore.RESET}')
    if keywords:
        print(f'\n{Fore.WHITE + Style.DIM} ⇨ Import filter:  {Style.RESET_ALL}'
            + f'{Fore.LIGHTBLUE_EX}{keywords}  '
            + f'{Style.DIM}(match threshold: {filter_match_threshold}%){Fore.RESET + Style.RESET_ALL}')
    progress_counter = ProgressCounter(songCount)
    label_formatter = LabelFormatter(26 + progress_counter.pad_size)
    lineBreak = ''
    song_index = 0
    for videoId in videoIds:
        if videoId in allSongFiles:
            continue
        video = YouTube(f'https://youtube.com/watch?v={videoId}', client='WEB')
        song_index += 1
        counter = progress_counter.format(song_index)
        song_name = video.author + ' - ' + video.title
        matchLevel = calculate_fuzzy_match_score(video.author, video.title, keywords)
        if matchLevel < filter_match_threshold:
            if song_index == 1:
                print()
            print(f'{lineBreak}{counter}' + Fore.YELLOW + Style.DIM + (f' ⇨ Match too low ({matchLevel:.1f}%)').ljust(label_formatter.tab_size - progress_counter.pad_size, ' ')
                + Style.RESET_ALL + f' {Fore.GREEN}{song_name}{Fore.RESET} {Fore.BLUE}[{video.video_id}]{Fore.RESET}')
            lineBreak = ''
            continue
        lineBreak = '\n'
        print(f'\n{counter}{Style.BRIGHT}' + ' ⇨ New video to import!'.ljust(label_formatter.tab_size - progress_counter.pad_size, ' ') 
            + f' {Fore.LIGHTGREEN_EX}{song_name}{Fore.RESET} {Fore.BLUE}[{video.video_id}]{Fore.RESET}{Style.RESET_ALL}')
        if promptToConfirm and input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to add new song in playlist{Style.RESET_ALL} ' 
                + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') != 'yes':
            continue
        try:
            # Progress bar callback
            def progress_bar_callback(percentage, label = ''):
                progress_bar = (
                    f'{Fore.LIGHTRED_EX}{("■" * int(percentage / 2))}{Fore.RESET}' \
                    + f'{Fore.LIGHTRED_EX}{("□" * (50 - int(percentage / 2)))}{Fore.RESET}')
                print(('', '\x1b[K')[percentage < 100], end = '\r')
                print(f'{label_formatter.format(label)}{progress_bar} {Style.DIM}{int(percentage)}%'.strip() + f' {Style.RESET_ALL}', 
                    end = ('\n', '')[percentage < 100], 
                    flush = True)

            async def before_connect_to_video(youtube_id):
                print(label_formatter.format('Connecting to YouTube API:') 
                    + f'Please, wait... ', end = '', flush = True)

            async def after_connect_to_video(video_properties):
                print('\x1b[K', end = '\r')
                print(label_formatter.format('Connecting to YouTube API:') 
                    + f'Ready to import video in playlist {Fore.BLUE}{playlistData.title}{Fore.RESET}')

            # async def before_download_audio(video_properties, m4aPath):
            #     pass

            progress_logger_for_download_audio = SimpleNamespace(
                label = 'Streaming audio:',
                callback = progress_bar_callback)

            # async def after_download_audio(video_properties, m4aPath):
            #     pass

            # async def before_encode_to_mp3(video_properties, m4aPath, mp3_path):
            #     pass

            progress_logger_for_encode_to_mp3 = SimpleNamespace(
                label = 'Encoding audio stream to MP3:',
                callback = progress_bar_callback)

            # async def after_encode_to_mp3(video_properties, m4aPath, mp3_path):
            #     pass

            # async def before_download_cover_art(song):
            #     pass

            progress_logger_for_download_cover_art = SimpleNamespace(
                label = 'Downloading cover art:',
                callback = progress_bar_callback)

            # async def after_download_cover_art(song):
            #     pass

            # async def on_delete_cover_art(song):
            #     pass

            async def before_shazam_song(song):
                print(label_formatter.format('Shazam-ing audio track:') 
                    + f'Please, wait... ', end = '', flush = True)

            async def after_shazam_song(song):
                print('\x1b[K', end = '\r')
                print(label_formatter.format('Shazam match result:') 
                    + f'Artist: {Fore.LIGHTCYAN_EX}{song.shazam_artist}{Fore.RESET}, ' 
                    + f'Title: {Fore.LIGHTCYAN_EX}{song.shazam_title}{Fore.RESET}, ' 
                    + f'Match: {Fore.LIGHTCYAN_EX}{song.shazam_match_level}%{Fore.RESET}')

            song = await SongModel.create_from_youtube(
                video.video_id, 
                playlistPath, 
                shazam_match_threshold,
                verbose = True, 
                use_default_verbosity = False,
                before_connect_to_video = before_connect_to_video, 
                after_connect_to_video = after_connect_to_video,
                # before_download_audio = before_download_audio, 
                progress_logger_for_download_audio = progress_logger_for_download_audio, 
                # after_download_audio = after_download_audio,
                # before_encode_to_mp3 = before_encode_to_mp3, 
                progress_logger_for_encode_to_mp3 = progress_logger_for_encode_to_mp3, 
                # after_encode_to_mp3 = after_encode_to_mp3,
                # before_download_cover_art = before_download_cover_art, 
                progress_logger_for_download_cover_art = progress_logger_for_download_cover_art, 
                # after_download_cover_art = after_download_cover_art, 
                # on_delete_cover_art = on_delete_cover_art,
                before_shazam_song = before_shazam_song, 
                after_shazam_song = after_shazam_song)

            if not song.has_junk_filename:
                print(label_formatter.format('MP3 file saved successfully:') 
                    + f'{Fore.LIGHTYELLOW_EX + Style.BRIGHT}{song.filename}{Fore.RESET + Style.RESET_ALL}')
                shazamedSongReport.append(SimpleNamespace(
                    youtube_id = video.video_id, 
                    song_name = song_name, 
                    detail = f'Shazam match level OK ({song.shazam_match_level}%)',
                    filename = song.filename))
            else:
                print(label_formatter.format('MP3 file saved as junk song:') 
                    + f'{Fore.MAGENTA}{song.filename}{Fore.RESET}')
                junkSongReport.append(SimpleNamespace(
                    youtube_id = video.video_id, 
                    song_name = song_name,  
                    reason = f'Shazam match level too low ({song.shazam_match_level}%)',
                    filename = song.filename))
        except SongError as error:
            print(f'{Fore.RED}ERROR! An exception occurs while importing song:', 
                type(error).__name__, '-', error, f'{Fore.RESET}')
            importFailureReport.append(SimpleNamespace(
                youtube_id = video.video_id, 
                song_name = song_name,  
                issue = f'{error}'))
        except:
            raise
        if promptToConfirm and input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Press ENTER to continue ' 
                + f'or type "abort" to stop importing songs:{Style.RESET_ALL} ') == 'abort':
            break

    print(f'\n\n{Back.LIGHTCYAN_EX + Fore.WHITE} Playlist import report {Style.RESET_ALL}')

    print(f'\n{Fore.LIGHTYELLOW_EX}- New Shazam-ed songs added to playlist .... ' 
        + f'{len(shazamedSongReport)}{Fore.RESET}')
    print(f'{Fore.MAGENTA}- New junk songs added to playlist ......... ' 
        + f'{len(junkSongReport)}{Fore.RESET}')
    print(f'{Fore.RED}- Song import failures ..................... ' 
        + f'{len(importFailureReport)}{Fore.RESET}')

    print(f'\n{Style.BRIGHT}- Number of Shazam-ed songs in playlist .... ' 
        + f'{len(allSongFiles) - len(junkSongFiles) + len(shazamedSongReport)}{Style.RESET_ALL}')
    print(f'{Style.BRIGHT}- Number of junk songs in playlist ......... ' 
        + f'{len(junkSongFiles) + len(junkSongReport)}{Style.RESET_ALL}')

    print(f'\n{Fore.CYAN}- Total number of songs in playlist ........ ' 
        + f'{len(allSongFiles) + len(shazamedSongReport) + len(junkSongReport)}{Fore.RESET}')
    if len(shazamedSongReport) > 0:
        print(f'\n\n{Back.YELLOW + Fore.WHITE} New Shazam-ed song summary {Style.RESET_ALL}')
        for song in shazamedSongReport:
            print(f'\n- YouTube ID: {Fore.BLUE}{song.youtube_id}{Fore.RESET}')
            print(f'  Song name:  {Fore.CYAN}{song.song_name}{Fore.RESET}')
            print(f'  Detail:     {Fore.LIGHTGREEN_EX}{song.detail}{Fore.RESET}')
            print(f'  Filename:   {Fore.LIGHTYELLOW_EX}{song.filename}{Style.RESET_ALL}')
    if len(junkSongReport) > 0:
        print(f'\n\n{Back.MAGENTA + Fore.WHITE} New junk song summary {Style.RESET_ALL}')
        for song in junkSongReport:
            print(f'\n- YouTube ID: {Fore.BLUE}{song.youtube_id}{Fore.RESET}')
            print(f'  Song name:  {Fore.CYAN}{song.song_name}{Fore.RESET}')
            print(f'  Reason:     {Fore.LIGHTGREEN_EX}{song.reason}{Fore.RESET}')
            print(f'  Filename:   {Fore.MAGENTA}{song.filename}{Fore.RESET}')
    if len(importFailureReport) > 0:
        print(f'\n\n{Back.RED + Fore.WHITE} Import failure summary {Style.RESET_ALL}')
        for song in importFailureReport:
            print(f'\n- YouTube ID: {Fore.BLUE}{song.youtube_id}{Fore.RESET}')
            print(f'  Song name:  {Fore.CYAN}{song.song_name}{Fore.RESET}')
            print(f'  Issue: {Fore.RED}{song.issue}{Fore.RESET}')