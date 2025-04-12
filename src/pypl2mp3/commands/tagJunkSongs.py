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
from pypl2mp3.libs.repository import getSongFiles
from pypl2mp3.libs.song import Song
from pypl2mp3.libs.utils import LabelMaker, CounterMaker, formatSongLabel


async def tagJunkSongs(args):
    """
    Set ID3 tags to junk songs
    """
    
    repositoryPath = Path(args.repo)
    promptToConfirm = False
    promptToConfirm = args.prompt
    shazamMatchThreshold = args.thresh
    junkSongFiles = getSongFiles(
        repositoryPath,
        keywords = args.keywords,
        filterMatchThreshold = args.match,
        junkOnly = True,
        playlistIdentifier = args.playlist,
        displaySummary = True)
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
    counterMaker = CounterMaker(songCount)
    labelMaker = LabelMaker(25)
    songIndex = 0

    for songPathname in junkSongFiles:
        songIndex += 1
        counter = counterMaker.format(songIndex)
        song = Song(songPathname)
        songName = song.labelFromFilename
        songName = f'{song.artist} - {song.title}'
        print(f'\n{formatSongLabel(counter, song)}  ' 
            + f'{Fore.WHITE + Style.DIM}[https://youtu.be/{song.youtubeId}]')
        if song.shouldBeTagged or not song.hasCoverArt:
            print(f'{Fore.MAGENTA}Song is not tagged or is missing cover art and should be YouTube-ed first before being fixed.{Fore.RESET}')
        elif song.shouldBeShazamed:
            print(f'{Fore.MAGENTA}Song is tagged and has cover art but it should be Shazam-ed to get trusted ones.{Fore.RESET}')
        elif song.shouldBeRenamed:
            print(f'{Fore.MAGENTA}Song is Shazam-ed and tagged but it should be renamed.{Fore.RESET}')
            if promptToConfirm:
                print(labelMaker.format('Current filename:') + f'{Fore.CYAN}{song.filename}{Fore.RESET}')
                print(labelMaker.format('Expected filename:') + f'{Fore.GREEN}{song.expectedFilename}{Fore.RESET}')
        else:
            print(f'{Fore.LIGHTYELLOW_EX}Song is Shazam-ed, tagged and named accordingly but still marked as "JUNK".{Fore.RESET}')
            if not promptToConfirm:
                print(f'{Fore.LIGHTYELLOW_EX}You should fix it using "--prompt" option{Fore.RESET}')
                junkSongReport.append({
                    'songName': songName,
                    'youtubeId': song.youtubeId,
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
                'songName': songName, 
                'youtubeId': song.youtubeId, 
                'filename': song.filename, 
                'reason': f'Song tagging aborted by user'})
        if (((song.shouldBeTagged or not song.hasCoverArt) and not promptToConfirm)
            or ((song.shouldBeTagged or not song.hasCoverArt) and promptToConfirm and input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to load song missing information from YouTube first{Style.RESET_ALL} ' 
                + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') == 'yes')):
            print(f'YouTube-ing junk song: Please, wait... ', end = '', flush = True)
            try:
                youtubeSongInfo = YouTube(f'https://youtube.com/watch?v={song.youtubeId}', client='WEB')
                song.updateState(
                    artist=youtubeSongInfo.author,
                    title = youtubeSongInfo.title,
                    coverArtUrl = youtubeSongInfo.thumbnail_url)
            except:
                print('\x1b[K', end = '\r')
                print(labelMaker.format('YouTube-ing junk song:') 
                    + f'{Fore.MAGENTA}ERROR! Failed to retrieve song information{Fore.RESET} ' 
                    + f'{Fore.BLUE}(IGNORING - Will try with Shazam anyway).{Fore.RESET}')
            print('\x1b[K', end = '\r')
            print(labelMaker.format('YouTube-ing junk song:') 
                + f'Artist: {Fore.LIGHTCYAN_EX}{song.artist}{Fore.RESET}, ' 
                + f'Title: {Fore.LIGHTCYAN_EX}{song.title}{Fore.RESET}, ' 
                + f'Cover art URL: {Fore.LIGHTCYAN_EX}{("None", "Available")[song.coverArtUrl is not None]}{Fore.RESET}')
            if not promptToConfirm:
                if song.hasCoverArt:
                    print(labelMaker.format('Updating MP3 tags:') 
                        + f'YouTube cover art and ID3 tags added to file.')
                else:
                    print(labelMaker.format('Updating MP3 tags:') 
                        + f'{Fore.MAGENTA}WARNING! YouTube ID3 tags added to file but not cover art{Fore.RESET}')
                try:
                    song.fixFilename(markAsJunk = (song.shazamMatchLevel or 0) < shazamMatchThreshold)
                    print(labelMaker.format('Junk song renamed to:') 
                        + f'{Fore.CYAN}{song.filename}{Fore.RESET}')
                except:
                    print(labelMaker.format('Junk song renamed to:') 
                        + f'{Fore.MAGENTA}ERROR! Failed to rename junk song to: {song.expectedJunkFilename}{Fore.RESET} ' 
                        + f'{Fore.BLUE}(IGNORING - Will try with Shazam anyway).{Fore.RESET}')
        print(f'Shazam-ing junk song: Please, wait... ', end = '', flush = True)
        try :
            await song.shazamSong(shazamMatchThreshold = shazamMatchThreshold)
        except Exception as error:
            if promptToConfirm:
                print('\x1b[K', end = '\r')
                print(labelMaker.format('Shazam-ing junk song:') 
                    + f'{Fore.MAGENTA}WARNING! An exception ({type(error).__name__}) ' 
                    + f'occurs while Shazam-ing song.{Fore.RESET}')
            else:
                print(f'\n{Fore.RED}ERROR! An exception occurs while Shazam-ing song:', 
                    type(error).__name__, '-', error, f'{Fore.RESET}')
                junkSongReport.append({
                    'songName': songName,
                    'youtubeId': song.youtubeId,
                    'filename': song.filename,
                    'reason': f'Failed to shazam song: {type(error).__name__} - {error}'})
                continue
        if not song.shouldBeShazamed:
            print('\x1b[K', end = '\r')
            print(labelMaker.format('Shazam-ing junk song:') 
                + f'Artist: {Fore.LIGHTCYAN_EX}{song.shazamArtist}{Fore.RESET}, ' 
                + f'Title: {Fore.LIGHTCYAN_EX}{song.shazamTitle}{Fore.RESET}, ' 
                + f'Match: {Fore.LIGHTCYAN_EX}{song.shazamMatchLevel}%{Fore.RESET}')
            if shazamMatchThreshold > 0 and song.shazamMatchLevel > shazamMatchThreshold:
                if promptToConfirm:
                    print(labelMaker.format('Shazam match result:') 
                        + f'{Fore.CYAN}Match level is over threshold ({song.shazamMatchLevel}% > {shazamMatchThreshold}%). ' 
                        + f'You can trust default values that will be purposed bellow.{Fore.RESET}')
                else:
                    if song.hasCoverArt:
                        print(labelMaker.format('Updating MP3 tags:') 
                            + f'Shazam cover art and ID3 tags added to file.')
                    else:
                        print(labelMaker.format('Updating MP3 tags:') 
                            + f'{Fore.MAGENTA}WARNING! Shazam ID3 tags added to file but not cover art{Fore.RESET}')
                    try:
                        song.fixFilename(markAsJunk = (song.shazamMatchLevel or 0) < shazamMatchThreshold)
                        print(labelMaker.format('Song successfully tagged and renamed to:') + f'{Fore.LIGHTYELLOW_EX}{song.filename}{Fore.RESET}')
                        unjunkSongReport.append({
                            'songName': songName, 
                            'youtubeId': song.youtubeId, 
                            'filename': song.filename, 
                            'detail': f'Shazam match level OK ({song.shazamMatchLevel}%)'})
                    except:
                        print(f'{Fore.RED}ERROR! Failed to rename junk song to: {song.expectedFilename}{Fore.RESET}')
                        junkSongReport.append({
                            'songName': songName, 
                            'youtubeId': song.youtubeId, 
                            'filename': song.filename, 
                            'reason': f'Failed to rename junk song to "{song.expectedFilename}"'})
                        continue
            elif shazamMatchThreshold > 0 and song.shazamMatchLevel < shazamMatchThreshold:
                if promptToConfirm:
                    print(labelMaker.format('Shazam match result:') 
                        + f'{Fore.MAGENTA}WARNING! Low match level ({song.shazamMatchLevel}% < {shazamMatchThreshold}%).{Fore.RESET}')
                else:
                    print(f'{Fore.MAGENTA}WARNING! Match level ({song.shazamMatchLevel}%) is too low to fix junk song.{Fore.RESET}')
                    junkSongReport.append({
                        'songName': songName, 
                        'youtubeId': song.youtubeId, 
                        'filename': song.filename, 
                        'reason': f'Match level ({song.shazamMatchLevel}%) is too low to fix junk song'})
            else:
                print('\x1b[K', end = '\r')
                print(labelMaker.format('Shazam-ing junk song:') 
                    + f'{Fore.MAGENTA}No match found{Fore.RESET} {Fore.BLUE}(this may occur with long track).{Fore.RESET}')
                if not promptToConfirm:
                    print(f'{Fore.MAGENTA}WARNING! Shazam did not find any match to fix this song. ' 
                        + f'Fix it using "--prompt" option.{Fore.RESET}')
                    junkSongReport.append({
                        'songName': songName, 
                        'youtubeId': song.youtubeId, 
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
                    print(labelMaker.format('   ⇨ Artist:') + f'{Fore.LIGHTYELLOW_EX}{artistInput}{Fore.RESET}')
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
                    print(labelMaker.format('   ⇨ Title:') + f'{Fore.LIGHTYELLOW_EX}{titleInput}{Fore.RESET}')
                    break
            while True:
                tip = (
                    'None - Type ENTER to leave blank cover art or an URL to set one', 
                    'Available - Type ENTER to keep existing cover art or an URL to chnge it')[song.coverArtUrl is not None]
                coverArtUrlInput = (
                    input(f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}   ⇨ Cover URL [default: {Fore.CYAN}%s{Style.RESET_ALL}]: ' % (tip)) 
                    or (song.coverArtUrl or 'None')).strip()
                if coverArtUrlInput == '':
                    print('\033[1A\x1b[K', end = '\r')
                    continue
                else:
                    choice = (None, 'Keep existing cover art')[coverArtUrlInput == song.coverArtUrl] or coverArtUrlInput
                    print('\033[1A\x1b[K', end = '\r')
                    print(labelMaker.format('   ⇨ Cover URL:') 
                        + f'{Fore.LIGHTYELLOW_EX}{choice}{Fore.RESET}')
                    song.coverArtUrl = (
                        (None, coverArtUrlInput)[coverArtUrlInput == song.coverArtUrl] 
                        or (None, coverArtUrlInput)[coverArtUrlInput != 'None'])
                    break
            saveTagsInput = input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to save ID3 tags and cover art{Style.RESET_ALL} ' 
                + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}/{Fore.CYAN}retry{Fore.RESET}) ? ')
            if saveTagsInput == 'yes':
                try:
                    song.updateState(
                        artist = artistInput,
                        title = titleInput,
                        coverArtUrl = coverArtUrlInput
                    )
                    if song.hasCoverArt:
                        print(labelMaker.format('Updating MP3 tags:') 
                            + f'Cover art and ID3 tags added to file.')
                    else:
                        print(labelMaker.format('Updating MP3 tags') 
                            + f'{Fore.MAGENTA}WARNING! ID3 tags added to file but not cover art{Fore.RESET}')
                except:
                    print(f'{Fore.RED}ERROR! Failed to save ID3 tags and cover art.{Fore.RESET}')
                    continue
                songName = f'{song.artist} - {song.title} [{song.youtubeId}]'
                print(labelMaker.format('New song name from tags:') 
                    + f'{Fore.CYAN + Style.BRIGHT}{songName}{Fore.RESET + Style.RESET_ALL}')
                if input(
                    f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to fix junk song filename{Style.RESET_ALL} ' 
                    + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') == 'yes':
                    try:
                        song.fixFilename(markAsJunk = False)
                        print(f'{Fore.LIGHTYELLOW_EX}Junk song successfully renamed to: {song.filename}{Fore.RESET}')
                        unjunkSongReport.append({
                            'youtubeId': song.youtubeId, 
                            'songName': songName, 
                            'detail': f'Shazam match level OK ({song.shazamMatchLevel}%)',
                            'filename': song.filename})
                    except:
                        print(f'{Fore.RED}ERROR! Failed to rename junk song to: {song.expectedFilename}{Fore.RESET}')
                        junkSongReport.append({
                            'songName': songName, 
                            'youtubeId': song.youtubeId, 
                            'filename': song.filename, 
                            'reason': f'Failed to rename junk song to "{song.expectedFilename}"'})
                        continue
                break
            elif saveTagsInput == 'retry':
                continue
            else:
                junkSongReport.append({
                    'songName': songName, 
                    'youtubeId': song.youtubeId, 
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
            print(f'\n{Fore.WHITE + Style.DIM}- YouTube ID: {Style.RESET_ALL}{Fore.WHITE}{reportItem["youtubeId"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Song name:  {Style.RESET_ALL}{Fore.CYAN}{reportItem["songName"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Filename:   {Style.RESET_ALL}{Fore.CYAN}{reportItem["filename"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Detail:     {Style.RESET_ALL}{Fore.LIGHTYELLOW_EX}{reportItem["detail"]}{Fore.RESET}')

    if len(junkSongReport) > 0:
        print(f'\n\n{Back.MAGENTA + Fore.WHITE} Unfixed junk songs summary {Style.RESET_ALL}')
        for reportItem in junkSongReport:
            print(f'\n{Fore.WHITE + Style.DIM}- YouTube ID: {Style.RESET_ALL}{Fore.WHITE}{reportItem["youtubeId"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Song name:  {Style.RESET_ALL}{Fore.CYAN}{reportItem["songName"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Filename:   {Style.RESET_ALL}{Fore.CYAN}{reportItem["filename"]}{Fore.RESET}')
            print(f'{Fore.WHITE + Style.DIM}  Reason:     {Style.RESET_ALL}{Fore.MAGENTA}{reportItem["reason"]}{Fore.RESET}')