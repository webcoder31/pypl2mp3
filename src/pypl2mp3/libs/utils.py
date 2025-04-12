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
import re

# Third party packages
from colorama import Fore, Style
from slugify import slugify
from thefuzz import fuzz


def extractYoutubeIdFromFilename(filename):
    """
    Extract YouTube ID located between the last brackets of the provided filename
    """

    match = re.match(r'^.*\[(?P<youtubeId>[^\]]+)\][^\]]*$', str(filename))
    if match:
        return match.group('youtubeId')
    return None


def extractYoutubeIdFromUrl(url):
    """
    Extract YouTube ID from the provided YouTube URL (e.g., https://www.youtube.com/watch?v=...)
    The ID is the part after the last '=' character.
    """

    match = re.match(r'^.*=(?P<youtubeId>.+)$', str(url))
    if match:
        return match.group('youtubeId')
    return None


def fuzzyMatchLevel(artist, title, keywords):
    """
    Computes fuzzy match level of song artist name and song title against keywords.
    The higher the score, the better the match.
    """
    
    if not keywords:
        return 100  # Assume perfect match if no filter
    score = 0
    penalty = 0
    songName = f'{artist.lower()} {title.lower()}'.strip()
    keywordList = keywords.lower().split()
    stackedKeywords = ''
    weight = len(keywordList) + 1
    weightSum = 0
    for keyword in keywordList:
        stackedKeywords += f' {keyword}'.strip()
        weight -= 1
        weightSum += weight
        if keyword in songName:
            score += 100 * weight  # Perfect match for exact keyword presence
        else:
            fuzzy_score = sum([  # Fuzzy match score for each stacked keyword combination
                1 * fuzz.WRatio(stackedKeywords, artist.lower()), 
                1 * fuzz.WRatio(stackedKeywords, title.lower()),
                3 * fuzz.WRatio(stackedKeywords, songName),
            ]) / 5
            if fuzzy_score < 100 - 10 * len(keywordList):
                penalty += weight  # Apply penalty for missing important words 
            score += fuzzy_score * weight
    # Decrease match level according to total weight of keywords (less keywords ==> more selective) 
    # and apply possible penalty to reduce rank
    return max((score / weightSum) - (50 * math.exp(-(math.log(2) / 3) * weightSum)) - (penalty * 10), 0)


def deterministicListSorter(string):
    """
    Function used by sort() method of lists to 
    perform deterministic case insensitive sorting
    """
    
    return slugify(str(string)).casefold(), str(string)


def formatSongLabel(counter, song):
    """
    Format a song label
    """
    
    return f'{counter}  ' \
        + f'{Fore.WHITE}{song.duration}  ' \
        + f'{Fore.LIGHTCYAN_EX + Style.BRIGHT}{song.artist}  ' \
        + f'{Fore.LIGHTYELLOW_EX}{song.title}{Fore.MAGENTA}' \
        + f'{("", " (JUNK)")[song.hasJunkFilename]}{Fore.RESET + Style.RESET_ALL}'


# Class that formats labels
class LabelMaker():
    """
    Utility class to format a label 
    """

    def __init__(self, tabSize):
        """
        Returns a LabelMaker instance
        """
        
        self.tabSize = tabSize

    def format(self, label):
        """
        Format a text label
        """
        
        return f'{Fore.WHITE + Style.DIM}{label.ljust(self.tabSize)} {Style.RESET_ALL}'
    

class CounterMaker():
    """
    Utility class to format a counter
    """
    
    def __init__(self, totalCount):
        """
        Returns a CounterMaker instance
        """
        
        self.totalCount = totalCount
        self.numberPadding = max(2, len(str(totalCount)))
        self.padSize = int(self.numberPadding * 2 + 1)
    
    def format(self, index):
        """
        Format a counter
        """
        
        return f'{Fore.LIGHTGREEN_EX}{str(index).rjust(self.numberPadding, "0")}' \
               + f'{Fore.WHITE + Style.DIM}/{Style.RESET_ALL}' \
               + f'{Fore.LIGHTGREEN_EX}{str(self.totalCount).rjust(self.numberPadding, "0")}{Style.RESET_ALL}'
    
    def placeholder(self, text = ''):
        """
        Return blank string (spaces) or the given text, 
        truncated if required, as a placeholder for a counter
        """
        
        return f'{Fore.LIGHTGREEN_EX}{text[:self.padSize].ljust(self.padSize, " ")}{Style.RESET_ALL}'
