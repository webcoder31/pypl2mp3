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
from colorama import Fore, Back, Style
from pytubefix import YouTube

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import LabelFormatter, ProgressCounter, format_song_display


async def tagJunkSongs(args):
    """
    Set ID3 tags to junk songs
    """
    
    repository_path = Path(args.repo)
    promptToConfirm = False
    promptToConfirm = args.prompt
    shazam_match_threshold = args.thresh
    junkSongFiles = get_repository_song_files(
        repository_path,
        keywords = args.keywords,
        filter_match_threshold = args.match,
        junk_only = True,
        playlist_identifier = args.playlist,
        display_summary = True)
    if len(junkSongFiles) == 0:
        print(f'\n{Fore.LIGHTYELLOW_EX}No junk song found.{Fore.RESET}')
        return
    print(f'\n{Fore.MAGENTA}NOTE: Type CTRL+C twice to exit.{Fore.RESET}')
    songCount = len(junkSongFiles)
    if not promptToConfirm and input(
        f'\n{Style.BRIGHT}{Fore.LIGHTBLUE_EX}This will try to Shazam and tag all junk songs found. Continue {Style.RESET_ALL}'
        + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') != 'yes':
            return
    unjunkSongReport = []
    junkSongReport = []
    progress_counter = ProgressCounter(songCount)
    label_formatter = LabelFormatter(25)
    song_index = 0

    for songPathname in junkSongFiles:
        song_index += 1
        counter = progress_counter.format(song_index)
        song = SongModel(songPathname)
        song_name = song.label_from_filename
        song_name = f'{song.artist} - {song.title}'
        print(f'\n{format_song_display(counter, song)}  ' 
            + f'{Fore.WHITE + Style.DIM}[https://youtu.be/{song.youtube_id}]')
        if song.should_be_tagged or not song.has_cover_art:
            print(f'{Fore.MAGENTA}Song is not tagged or is missing cover art and should be YouTube-ed first before being fixed.{Fore.RESET}')
        elif song.should_be_shazamed:
            print(f'{Fore.MAGENTA}Song is tagged and has cover art but it should be Shazam-ed to get trusted ones.{Fore.RESET}')
        elif song.should_be_renamed:
            print(f'{Fore.MAGENTA}Song is Shazam-ed and tagged but it should be renamed.{Fore.RESET}')
            if promptToConfirm:
                print(label_formatter.format('Current filename:') + f'{Fore.CYAN}{song.filename}{Fore.RESET}')
                print(label_formatter.format('Expected filename:') + f'{Fore.GREEN}{song.expected_filename}{Fore.RESET}')
        else:
            print(f'{Fore.LIGHTYELLOW_EX}Song is Shazam-ed, tagged and named accordingly but still marked as "JUNK".{Fore.RESET}')
            if not promptToConfirm:
                print(f'{Fore.LIGHTYELLOW_EX}You should fix it using "--prompt" option{Fore.RESET}')
                junkSongReport.append({
                    'song_name': song_name,
                    'youtube_id': song.youtube_id,
                    'filename': song.filename,
                    'reason': f'Ignored - Should be unjunked using "--prompt" option'})
                continue
        if promptToConfirm: 
            response = input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to fix this junk song{Style.RESET_ALL} '
                + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}/{Fore.CYAN}abort{Fore.RESET}) ? ')
            if response == 'abort':
                break
            elif response != 'yes':
                continue
            junkSongReport.append({
                'song_name': song_name, 
                'youtube_id': song.youtube_id, 
                'filename': song.filename, 
                'reason': f'Song tagging aborted by user'})
        if (((song.should_be_tagged or not song.has_cover_art) and not promptToConfirm)
            or ((song.should_be_tagged or not song.has_cover_art) and promptToConfirm and input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to load song missing information from YouTube first{Style.RESET_ALL} ' 
                + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') == 'yes')):
            print(f'YouTube-ing junk song: Please, wait... ', end = '', flush = True)
            try:
                youtubeSongInfo = YouTube(f'https://youtube.com/watch?v={song.youtube_id}', client='WEB')
                song.update_state(
                    artist=youtubeSongInfo.author,
                    title = youtubeSongInfo.title,
                    cover_art_url = youtubeSongInfo.thumbnail_url)
            except:
                print('\x1b[K', end = '\r')
                print(label_formatter.format('YouTube-ing junk song:') 
                    + f'{Fore.MAGENTA}ERROR! Failed to retrieve song information{Fore.RESET} ' 
                    + f'{Fore.BLUE}(IGNORING - Will try with Shazam anyway).{Fore.RESET}')
            print('\x1b[K', end = '\r')
            print(label_formatter.format('YouTube-ing junk song:') 
                + f'Artist: {Fore.LIGHTCYAN_EX}{song.artist}{Fore.RESET}, ' 
                + f'Title: {Fore.LIGHTCYAN_EX}{song.title}{Fore.RESET}, ' 
                + f'Cover art URL: {Fore.LIGHTCYAN_EX}{("None", "Available")[song.cover_art_url is not None]}{Fore.RESET}')
            if not promptToConfirm:
                if song.has_cover_art:
                    print(label_formatter.format('Updating MP3 tags:') 
                        + f'YouTube cover art and ID3 tags added to file.')
                else:
                    print(label_formatter.format('Updating MP3 tags:') 
                        + f'{Fore.MAGENTA}WARNING! YouTube ID3 tags added to file but not cover art{Fore.RESET}')
                try:
                    song.fix_filename(mark_as_junk = (song.shazam_match_level or 0) < shazam_match_threshold)
                    print(label_formatter.format('Junk song renamed to:') 
                        + f'{Fore.CYAN}{song.filename}{Fore.RESET}')
                except:
                    print(label_formatter.format('Junk song renamed to:') 
                        + f'{Fore.MAGENTA}ERROR! Failed to rename junk song to: {song.expected_junk_filename}{Fore.RESET} ' 
                        + f'{Fore.BLUE}(IGNORING - Will try with Shazam anyway).{Fore.RESET}')
        print(f'Shazam-ing junk song: Please, wait... ', end = '', flush = True)
        try :
            await song.shazam_song(shazam_match_threshold = shazam_match_threshold)
        except Exception as error:
            if promptToConfirm:
                print('\x1b[K', end = '\r')
                print(label_formatter.format('Shazam-ing junk song:') 
                    + f'{Fore.MAGENTA}WARNING! An exception ({type(error).__name__}) ' 
                    + f'occurs while Shazam-ing song.{Fore.RESET}')
            else:
                print(f'\n{Fore.RED}ERROR! An exception occurs while Shazam-ing song:', 
                    type(error).__name__, '-', error, f'{Fore.RESET}')
                junkSongReport.append({
                    'song_name': song_name,
                    'youtube_id': song.youtube_id,
                    'filename': song.filename,
                    'reason': f'Failed to shazam song: {type(error).__name__} - {error}'})
                continue
        if not song.should_be_shazamed:
            print('\x1b[K', end = '\r')
            print(label_formatter.format('Shazam-ing junk song:') 
                + f'Artist: {Fore.LIGHTCYAN_EX}{song.shazam_artist}{Fore.RESET}, ' 
                + f'Title: {Fore.LIGHTCYAN_EX}{song.shazam_title}{Fore.RESET}, ' 
                + f'Match: {Fore.LIGHTCYAN_EX}{song.shazam_match_level}%{Fore.RESET}')
            if shazam_match_threshold > 0 and song.shazam_match_level > shazam_match_threshold:
                if promptToConfirm:
                    print(label_formatter.format('Shazam match result:') 
                        + f'{Fore.CYAN}Match level is over threshold ({song.shazam_match_level}% > {shazam_match_threshold}%). ' 
                        + f'You can trust default values that will be purposed bellow.{Fore.RESET}')
                else:
                    if song.has_cover_art:
                        print(label_formatter.format('Updating MP3 tags:') 
                            + f'Shazam cover art and ID3 tags added to file.')
                    else:
                        print(label_formatter.format('Updating MP3 tags:') 
                            + f'{Fore.MAGENTA}WARNING! Shazam ID3 tags added to file but not cover art{Fore.RESET}')
                    try:
                        song.fix_filename(mark_as_junk = (song.shazam_match_level or 0) < shazam_match_threshold)
                        print(label_formatter.format('Song successfully tagged and renamed to:') + f'{Fore.LIGHTYELLOW_EX}{song.filename}{Fore.RESET}')
                        unjunkSongReport.append({
                            'song_name': song_name, 
                            'youtube_id': song.youtube_id, 
                            'filename': song.filename, 
                            'detail': f'Shazam match level OK ({song.shazam_match_level}%)'})
                    except:
                        print(f'{Fore.RED}ERROR! Failed to rename junk song to: {song.expected_filename}{Fore.RESET}')
                        junkSongReport.append({
                            'song_name': song_name, 
                            'youtube_id': song.youtube_id, 
                            'filename': song.filename, 
                            'reason': f'Failed to rename junk song to "{song.expected_filename}"'})
                        continue
            elif shazam_match_threshold > 0 and song.shazam_match_level < shazam_match_threshold:
                if promptToConfirm:
                    print(label_formatter.format('Shazam match result:') 
                        + f'{Fore.MAGENTA}WARNING! Low match level ({song.shazam_match_level}% < {shazam_match_threshold}%).{Fore.RESET}')
                else:
                    print(f'{Fore.MAGENTA}WARNING! Match level ({song.shazam_match_level}%) is too low to fix junk song.{Fore.RESET}')
                    junkSongReport.append({
                        'song_name': song_name, 
                        'youtube_id': song.youtube_id, 
                        'filename': song.filename, 
                        'reason': f'Match level ({song.shazam_match_level}%) is too low to fix junk song'})
            else:
                print('\x1b[K', end = '\r')
                print(label_formatter.format('Shazam-ing junk song:') 
                    + f'{Fore.MAGENTA}No match found{Fore.RESET} {Fore.BLUE}(this may occur with long track).{Fore.RESET}')
                if not promptToConfirm:
                    print(f'{Fore.MAGENTA}WARNING! Shazam did not find any match to fix this song. ' 
                        + f'Fix it using "--prompt" option.{Fore.RESET}')
                    junkSongReport.append({
                        'song_name': song_name, 
                        'youtube_id': song.youtube_id, 
                        'filename': song.filename, 
                        'reason': 'Shazam did not find any match for song'})
        if not promptToConfirm:
            continue
        while True:
            print(f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Please, input new ID3 tags or hit ENTER to accept purposed default values.{Style.RESET_ALL}')
            while True:
                artistInput = (
                    input(f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}   ⇨ Artist [default: {Fore.CYAN}%s{Style.RESET_ALL}]: ' % song.artist) 
                    or song.artist).strip()
                if artistInput == '':
                    print('\033[1A\x1b[K', end = '\r')
                    continue
                else:
                    print('\033[1A\x1b[K', end = '\r')
                    print(label_formatter.format('   ⇨ Artist:') + f'{Fore.LIGHTYELLOW_EX}{artistInput}{Fore.RESET}')
                    break
            while True:
                titleInput = (
                    input(f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}   ⇨ Title [default: {Fore.CYAN}%s{Style.RESET_ALL}]: ' % song.title) 
                    or song.title).strip()
                if titleInput == '':
                    print('\033[1A\x1b[K', end = '\r')
                    continue
                else:
                    print('\033[1A\x1b[K', end = '\r')
                    print(label_formatter.format('   ⇨ Title:') + f'{Fore.LIGHTYELLOW_EX}{titleInput}{Fore.RESET}')
                    break
            while True:
                tip = (
                    'None - Type ENTER to leave blank cover art or an URL to set one', 
                    'Available - Type ENTER to keep existing cover art or an URL to chnge it')[song.cover_art_url is not None]
                cover_art_urlInput = (
                    input(f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}   ⇨ Cover URL [default: {Fore.CYAN}%s{Style.RESET_ALL}]: ' % (tip)) 
                    or (song.cover_art_url or 'None')).strip()
                if cover_art_urlInput == '':
                    print('\033[1A\x1b[K', end = '\r')
                    continue
                else:
                    choice = (None, 'Keep existing cover art')[cover_art_urlInput == song.cover_art_url] or cover_art_urlInput
                    print('\033[1A\x1b[K', end = '\r')
                    print(label_formatter.format('   ⇨ Cover URL:') 
                        + f'{Fore.LIGHTYELLOW_EX}{choice}{Fore.RESET}')
                    song.cover_art_url = (
                        (None, cover_art_urlInput)[cover_art_urlInput == song.cover_art_url] 
                        or (None, cover_art_urlInput)[cover_art_urlInput != 'None'])
                    break
            saveTagsInput = input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to save ID3 tags and cover art{Style.RESET_ALL} ' 
                + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}/{Fore.CYAN}retry{Fore.RESET}) ? ')
            if saveTagsInput == 'yes':
                try:
                    song.update_state(
                        artist = artistInput,
                        title = titleInput,
                        cover_art_url = cover_art_urlInput
                    )
                    if song.has_cover_art:
                        print(label_formatter.format('Updating MP3 tags:') 
                            + f'Cover art and ID3 tags added to file.')
                    else:
                        print(label_formatter.format('Updating MP3 tags') 
                            + f'{Fore.MAGENTA}WARNING! ID3 tags added to file but not cover art{Fore.RESET}')
                except:
                    print(f'{Fore.RED}ERROR! Failed to save ID3 tags and cover art.{Fore.RESET}')
                    continue
                song_name = f'{song.artist} - {song.title} [{song.youtube_id}]'
                print(label_formatter.format('New song name from tags:') 
                    + f'{Fore.CYAN + Style.BRIGHT}{song_name}{Fore.RESET + Style.RESET_ALL}')
                if input(
                    f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to fix junk song filename{Style.RESET_ALL} ' 
                    + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') == 'yes':
                    try:
                        song.fix_filename(mark_as_junk = False)
                        print(f'{Fore.LIGHTYELLOW_EX}Junk song successfully renamed to: {song.filename}{Fore.RESET}')
                        unjunkSongReport.append({
                            'youtube_id': song.youtube_id, 
                            'song_name': song_name, 
                            'detail': f'Shazam match level OK ({song.shazam_match_level}%)',
                            'filename': song.filename})
                    except:
                        print(f'{Fore.RED}ERROR! Failed to rename junk song to: {song.expected_filename}{Fore.RESET}')
                        junkSongReport.append({
                            'song_name': song_name, 
                            'youtube_id': song.youtube_id, 
                            'filename': song.filename, 
                            'reason': f'Failed to rename junk song to "{song.expected_filename}"'})
                        continue
                break
            elif saveTagsInput == 'retry':
                continue
            else:
                junkSongReport.append({
                    'song_name': song_name, 
                    'youtube_id': song.youtube_id, 
                    'filename': song.filename, 
                    'reason': f'Song tagging aborted by user'})
                break

    print(f'\n\n{Back.BLUE + Fore.WHITE} Results {Style.RESET_ALL}')

    print(f'\n{Fore.LIGHTYELLOW_EX}- Successfully fixed junk songs ........... ' 
        + f'{len(unjunkSongReport)}{Fore.RESET}')
    print(f'{Fore.MAGENTA}- Unfixed junk songs ...................... ' 
        + f'{len(junkSongReport)}{Fore.RESET}')
    print(f'\n{Fore.CYAN}- Total number of processed songs ......... ' 
        + f'{len(unjunkSongReport) + len(junkSongReport)}{Fore.RESET}')
    
    if len(unjunkSongReport) > 0:
        print(f'\n\n{Back.YELLOW + Fore.WHITE} Fixed junk song summary {Style.RESET_ALL}')
        for reportItem in unjunkSongReport:
            print(f'\n{Fore.WHITE + Style.DIM}- YouTube ID: {Style.RESET_ALL}{Fore.WHITE}{reportItem["youtube_id"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Song name:  {Style.RESET_ALL}{Fore.CYAN}{reportItem["song_name"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Filename:   {Style.RESET_ALL}{Fore.CYAN}{reportItem["filename"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Detail:     {Style.RESET_ALL}{Fore.LIGHTYELLOW_EX}{reportItem["detail"]}{Fore.RESET}')

    if len(junkSongReport) > 0:
        print(f'\n\n{Back.MAGENTA + Fore.WHITE} Unfixed junk songs summary {Style.RESET_ALL}')
        for reportItem in junkSongReport:
            print(f'\n{Fore.WHITE + Style.DIM}- YouTube ID: {Style.RESET_ALL}{Fore.WHITE}{reportItem["youtube_id"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Song name:  {Style.RESET_ALL}{Fore.CYAN}{reportItem["song_name"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Filename:   {Style.RESET_ALL}{Fore.CYAN}{reportItem["filename"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Reason:     {Style.RESET_ALL}{Fore.MAGENTA}{reportItem["reason"]}{Fore.RESET}')