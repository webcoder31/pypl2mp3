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
from pypl2mp3.libs.repository import getPlaylist
from pypl2mp3.libs.song import Song, SongError
from pypl2mp3.libs.utils import extractYoutubeIdFromFilename, extractYoutubeIdFromUrl, fuzzyMatchLevel, LabelMaker, CounterMaker


async def importPlaylist(args):
    """
    Sync (or create) a loacal playlist from YouTube 
    """
    
    repositoryPath = Path(args.repo)
    selectedPlaylist = getPlaylist(repositoryPath, args.playlist, mustExist = False)
    keywords = args.keywords
    filterMatchThreshold = args.match
    shazamMatchThreshold = args.thresh
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
    playlistPath = repositoryPath / f'{playlistData.owner} - {playlistData.title} [{selectedPlaylist.id}]'
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
    allSongFiles = frozenset(map(extractYoutubeIdFromFilename, list(playlistPath.glob('*.mp3'))))
    junkSongFiles = frozenset(map(extractYoutubeIdFromFilename, list(playlistPath.glob('* (JUNK).mp3'))))
    videoIds = frozenset(map(extractYoutubeIdFromUrl, playlistData.video_urls))
    songCount = len(videoIds) - len(set(allSongFiles) & set(videoIds)) # Number of new songs (not already imported)
    if songCount == 0:
        print(f'\n{Fore.LIGHTYELLOW_EX}No new video to import.{Fore.RESET}')
        return
    print(f'{Fore.LIGHTYELLOW_EX}Number of new videos to import:  {Fore.RESET}'
        + f'{Fore.LIGHTGREEN_EX}{songCount}{Fore.RESET}')
    if keywords:
        print(f'\n{Fore.WHITE + Style.DIM} ⇨ Import filter:  {Style.RESET_ALL}'
            + f'{Fore.LIGHTBLUE_EX}{keywords}  '
            + f'{Style.DIM}(match threshold: {filterMatchThreshold}%){Fore.RESET + Style.RESET_ALL}')
    counterMaker = CounterMaker(songCount)
    labelMaker = LabelMaker(26 + counterMaker.padSize)
    lineBreak = ''
    songIndex = 0
    for videoId in videoIds:
        if videoId in allSongFiles:
            continue
        video = YouTube(f'https://youtube.com/watch?v={videoId}', client='WEB')
        songIndex += 1
        counter = counterMaker.format(songIndex)
        songName = video.author + ' - ' + video.title
        matchLevel = fuzzyMatchLevel(video.author, video.title, keywords)
        if matchLevel < filterMatchThreshold:
            if songIndex == 1:
                print()
            print(f'{lineBreak}{counter}' + Fore.YELLOW + Style.DIM + (f' ⇨ Match too low ({matchLevel:.1f}%)').ljust(labelMaker.tabSize - counterMaker.padSize, ' ')
                + Style.RESET_ALL + f' {Fore.GREEN}{songName}{Fore.RESET} {Fore.BLUE}[{video.video_id}]{Fore.RESET}')
            lineBreak = ''
            continue
        lineBreak = '\n'
        print(f'\n{counter}{Style.BRIGHT}' + ' ⇨ New video to import!'.ljust(labelMaker.tabSize - counterMaker.padSize, ' ') 
            + f' {Fore.LIGHTGREEN_EX}{songName}{Fore.RESET} {Fore.BLUE}[{video.video_id}]{Fore.RESET}{Style.RESET_ALL}')
        if promptToConfirm and input(
                f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to add new song in playlist{Style.RESET_ALL} ' 
                + f'({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? ') != 'yes':
            continue
        try:
            # Progress bar callback
            def progressBarCallback(percentage, label = ''):
                progress_bar = (
                    f'{Fore.LIGHTRED_EX}{("■" * int(percentage / 2))}{Fore.RESET}' \
                    + f'{Fore.LIGHTRED_EX}{("□" * (50 - int(percentage / 2)))}{Fore.RESET}')
                print(('', '\x1b[K')[percentage < 100], end = '\r')
                print(f'{labelMaker.format(label)}{progress_bar} {Style.DIM}{int(percentage)}%'.strip() + f' {Style.RESET_ALL}', 
                    end = ('\n', '')[percentage < 100], 
                    flush = True)

            async def beforeConnectToVideo(youtubeId):
                print(labelMaker.format('Connecting to YouTube API:') 
                    + f'Please, wait... ', end = '', flush = True)

            async def afterConnectToVideo(videoProps):
                print('\x1b[K', end = '\r')
                print(labelMaker.format('Connecting to YouTube API:') 
                    + f'Ready to import video in playlist {Fore.BLUE}{playlistData.title}{Fore.RESET}')

            # async def beforeDonwnloadAudio(videoProps, m4aPath):
            #     pass

            progressLoggerForDownloadAudio = SimpleNamespace(
                label = 'Streaming audio:',
                callback = progressBarCallback)

            # async def afterDownloadAudio(videoProps, m4aPath):
            #     pass

            # async def beforeEncodeToMp3(videoProps, m4aPath, mp3Path):
            #     pass

            progressLoggerForEncodeToMp3 = SimpleNamespace(
                label = 'Encoding audio stream to MP3:',
                callback = progressBarCallback)

            # async def afterEncodeToMp3(videoProps, m4aPath, mp3Path):
            #     pass

            # async def beforeDownloadCoverArt(song):
            #     pass

            progressLoggerForDownloadCoverArt = SimpleNamespace(
                label = 'Downloading cover art:',
                callback = progressBarCallback)

            # async def afterDownloadCoverArt(song):
            #     pass

            # async def onDeleteCoverArt(song):
            #     pass

            async def beforeShazamSong(song):
                print(labelMaker.format('Shazam-ing audio track:') 
                    + f'Please, wait... ', end = '', flush = True)

            async def afterShazamSong(song):
                print('\x1b[K', end = '\r')
                print(labelMaker.format('Shazam match result:') 
                    + f'Artist: {Fore.LIGHTCYAN_EX}{song.shazamArtist}{Fore.RESET}, ' 
                    + f'Title: {Fore.LIGHTCYAN_EX}{song.shazamTitle}{Fore.RESET}, ' 
                    + f'Match: {Fore.LIGHTCYAN_EX}{song.shazamMatchLevel}%{Fore.RESET}')

            song = await Song.createFromYoutube(
                video.video_id, 
                playlistPath, 
                shazamMatchThreshold,
                verbose = True, 
                useDefaultVerbosity = False,
                beforeConnectToVideo = beforeConnectToVideo, 
                afterConnectToVideo = afterConnectToVideo,
                # beforeDonwnloadAudio = beforeDonwnloadAudio, 
                progressLoggerForDownloadAudio = progressLoggerForDownloadAudio, 
                # afterDownloadAudio = afterDownloadAudio,
                # beforeEncodeToMp3 = beforeEncodeToMp3, 
                progressLoggerForEncodeToMp3 = progressLoggerForEncodeToMp3, 
                # afterEncodeToMp3 = afterEncodeToMp3,
                # beforeDownloadCoverArt = beforeDownloadCoverArt, 
                progressLoggerForDownloadCoverArt = progressLoggerForDownloadCoverArt, 
                # afterDownloadCoverArt = afterDownloadCoverArt, 
                # onDeleteCoverArt = onDeleteCoverArt,
                beforeShazamSong = beforeShazamSong, 
                afterShazamSong = afterShazamSong)

            if not song.hasJunkFilename:
                print(labelMaker.format('MP3 file saved successfully:') 
                    + f'{Fore.LIGHTYELLOW_EX + Style.BRIGHT}{song.filename}{Fore.RESET + Style.RESET_ALL}')
                shazamedSongReport.append(SimpleNamespace(
                    youtubeId = video.video_id, 
                    songName = songName, 
                    detail = f'Shazam match level OK ({song.shazamMatchLevel}%)',
                    filename = song.filename))
            else:
                print(labelMaker.format('MP3 file saved as junk song:') 
                    + f'{Fore.MAGENTA}{song.filename}{Fore.RESET}')
                junkSongReport.append(SimpleNamespace(
                    youtubeId = video.video_id, 
                    songName = songName,  
                    reason = f'Shazam match level too low ({song.shazamMatchLevel}%)',
                    filename = song.filename))
        except SongError as error:
            print(f'{Fore.RED}ERROR! An exception occurs while importing song:', 
                type(error).__name__, '-', error, f'{Fore.RESET}')
            importFailureReport.append(SimpleNamespace(
                youtubeId = video.video_id, 
                songName = songName,  
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
            print(f'\n- YouTube ID: {Fore.BLUE}{song.youtubeId}{Fore.RESET}')
            print(f'  Song name:  {Fore.CYAN}{song.songName}{Fore.RESET}')
            print(f'  Detail:     {Fore.LIGHTGREEN_EX}{song.detail}{Fore.RESET}')
            print(f'  Filename:   {Fore.LIGHTYELLOW_EX}{song.filename}{Style.RESET_ALL}')
    if len(junkSongReport) > 0:
        print(f'\n\n{Back.MAGENTA + Fore.WHITE} New junk song summary {Style.RESET_ALL}')
        for song in junkSongReport:
            print(f'\n- YouTube ID: {Fore.BLUE}{song.youtubeId}{Fore.RESET}')
            print(f'  Song name:  {Fore.CYAN}{song.songName}{Fore.RESET}')
            print(f'  Reason:     {Fore.LIGHTGREEN_EX}{song.reason}{Fore.RESET}')
            print(f'  Filename:   {Fore.MAGENTA}{song.filename}{Fore.RESET}')
    if len(importFailureReport) > 0:
        print(f'\n\n{Back.RED + Fore.WHITE} Import failure summary {Style.RESET_ALL}')
        for song in importFailureReport:
            print(f'\n- YouTube ID: {Fore.BLUE}{song.youtubeId}{Fore.RESET}')
            print(f'  Song name:  {Fore.CYAN}{song.songName}{Fore.RESET}')
            print(f'  Issue: {Fore.RED}{song.issue}{Fore.RESET}')