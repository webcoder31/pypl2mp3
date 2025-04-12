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
import math
import random
import re
from types import SimpleNamespace

# Third party packages
from colorama import Fore, Back, Style

# pypl2mp3 libs
from pypl2mp3.libs.song import Song, SongError
from pypl2mp3.libs.utils import extractYoutubeIdFromFilename, deterministicListSorter, fuzzyMatchLevel


def getPlaylist(repositoryPath, playlistIdentifier, mustExist = True):
    """
    Get playlist information from any playlist identifier (an ID or an URL or an instant index)
    """
    
    playlistIdentifier = playlistIdentifier
    playlistFolders = [
        folder.name 
        for folder in list(repositoryPath.glob('*')) 
        if re.match(r'^.*\[[^\]]+\][^\]]*$', folder.name)
    ]
    playlistFolders.sort(key = deterministicListSorter)
    if str(playlistIdentifier).isnumeric():
        if 0 <= int(playlistIdentifier) - 1 < len(playlistFolders):
            id = extractYoutubeIdFromFilename(playlistFolders[int(playlistIdentifier) - 1])
            url = 'https://www.youtube.com/playlist?list=' + id
            exists = True
            folder = playlistFolders[int(playlistIdentifier) - 1]
            path = repositoryPath / folder
            name = folder[:(-1 * len(id) - 3)]
        else:
            raise SongError('Playlist index is out of range.')
    else:
        id = str(playlistIdentifier)
        match = re.match(r'[&?]list=(?P<id>[^&]+)', str(id), re.IGNORECASE)
        if match:
            id = match.group('id')
        url = 'https://www.youtube.com/playlist?list=' + id
        matchingFolders = [folder for folder in playlistFolders if id in folder]
        matchingFolders.sort(key = deterministicListSorter)
        if len(matchingFolders) > 1:
            raise SongError(f'More than one playlists match YouTube ID in repository.')
        if len(matchingFolders) > 0:
            exists = True
            folder = matchingFolders[0]
            path = repositoryPath / folder
            name = folder[:(-1 * len(id) - 3)]
        else:
            if mustExist:
                raise SongError(f'Playlist does not exist in repository.')
            exists = False
            folder = None
            path = None
            name = None
    return SimpleNamespace(
        id = id,
        url = url,
        exists = exists,
        folder = folder,
        path = path,
        name = name)


def getMatchingSongs(searchPath, keywords='', threshold=45, junkOnly=False):
    """
    Finds and returns a list of song paths sorted by weighted match level,
    ensuring scores are more evenly distributed but still preserve ranking differences.
    """

    filePattern = '*.mp3' if not junkOnly else '*(JUNK).mp3'

    # Get valid songs with YouTube IDs
    songFiles = [
        songPath for songPath in searchPath.rglob(filePattern)
        if extractYoutubeIdFromFilename(songPath.name) is not None
    ]

    # If no keywords are provided, return song files sorted by song name
    if keywords == '':
        songFiles = [
            {'path': songPath, 'name': f'{song.artist} - {song.title}'}
            for songPath in songFiles if (song := Song(songPath))  # Create and assign `song` once
        ]
        songFiles.sort(key = lambda song: (deterministicListSorter(song['name']), song['path'].parent.name))
        return [song['path'] for song in songFiles]
    
    # Compute raw match levels
    matchedSongs = [
        {'path': songPath, 'matchLevel': fuzzyMatchLevel(song.artist, song.title, keywords)}
        for songPath in songFiles if (song := Song(songPath))  # Create and assign `song` once
    ]

    # Exclude songs with zero match level
    matchedSongs = [song for song in matchedSongs if song['matchLevel'] > 0]

    if not matchedSongs:
        return []  # No valid matches

    # Sort songs by match level (descending)
    matchedSongs.sort(key=lambda song: song['matchLevel'], reverse=True)

    # Apply square root normalization
    min_score = min(song['matchLevel'] for song in matchedSongs)
    max_score = max(song['matchLevel'] for song in matchedSongs)
    score_range = max_score - min_score
    for song in matchedSongs:
        raw_score = song['matchLevel'] - (min_score if score_range > 0 else 0)
        normalized_score = (math.sqrt(raw_score) / math.sqrt(score_range or 1)) * 100
        song['matchLevel'] = normalized_score

    # Filter using the threshold
    return [song['path'] for song in matchedSongs if song['matchLevel'] >= threshold]


def getSongFiles(
        repositoryPath, 
        junkOnly = False, 
        keywords = '', 
        filterMatchThreshold = 45,
        songIndex = None, 
        playlistIdentifier = None, 
        displaySummary = False):
    """
    Retrieve song files, from a particular repository or playlist, that match 
    an optional filter operating on song file names and/or, optionally, match
    a song located at a given index within the selected songs.
    If requested, display a short summary about song selection criteria.
    """
    
    searchPath = repositoryPath
    selectedPlaylist = None
    if playlistIdentifier:
        selectedPlaylist = getPlaylist(repositoryPath, playlistIdentifier, mustExist = True)
        searchPath = selectedPlaylist.path
    songFiles = getMatchingSongs(searchPath, keywords, filterMatchThreshold, junkOnly)
    songCount = len(songFiles)
    if songCount == 0:
        raise SongError(f'No song found.')
    if songIndex is not None:
        if abs(songIndex) > songCount:
            raise SongError(f'Song index is out of range.')
        songFiles = [songFiles[(songIndex - 1, random.randint(0, songCount - 1))[songIndex == 0]]]
    if displaySummary:
        print(f'\n{Back.YELLOW + Style.BRIGHT} Found {len(songFiles)} songs matching criteria {Style.RESET_ALL}\n')
        if selectedPlaylist:
            print(f'{Fore.WHITE + Style.DIM} ⇨ Playlist:   {Style.RESET_ALL}'
                + f'{Fore.LIGHTBLUE_EX}{selectedPlaylist.name}{Fore.RESET}')
        else:
            print(f'{Fore.WHITE + Style.DIM} ⇨ Playlists:  {Style.RESET_ALL}'
                + f'{Fore.LIGHTBLUE_EX}ALL{Fore.RESET}')
        if keywords:
            print(f'{Fore.WHITE + Style.DIM} ⇨ Filter:     {Style.RESET_ALL}'
                + f'{Fore.LIGHTBLUE_EX}{keywords}  '
                + f'{Style.DIM}(match threshold: {filterMatchThreshold}%){Fore.RESET + Style.RESET_ALL}')
        else:
            print(f'{Fore.WHITE + Style.DIM} ⇨ Filter:     {Style.RESET_ALL}'
                + f'{Fore.LIGHTBLUE_EX}NONE{Fore.RESET}')
    return songFiles