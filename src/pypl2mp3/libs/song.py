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
import datetime
from pathlib import Path
import re
import tempfile
import time
from types import SimpleNamespace
import urllib.request

# Third party packages
from colorama import Fore, Style
from moviepy.editor import AudioFileClip
from mutagen.id3 import TIT2, TPE1, TXXX, APIC
import mutagen.mp3
from proglog import ProgressBarLogger
from pytubefix import YouTube, request
from shazamio import Shazam
from slugify import slugify
from thefuzz import fuzz

# pypl2mp3 libs
from pypl2mp3.libs.utils import LabelMaker


class SongError(Exception):
    """
    Song error class
    """
    
    def __init__(self, message, errors = None):
        """
        Construct a SongError
        """
                  
        super().__init__(message)
        if errors:
            print(errors)


class Song:
    """
    Song class
    NOTE: MP3 files are saved in ID3v2.3 only, without ID3v1 (default is ID3v2.4)
    """


    class TerminalProgressBar():
        """
        Inner base class providing a method in charge of printing progress bar in terminal
        """

        def __init__(self, progressCallback = None, label = ''):
            """
            Construct a TerminalProgressBar
            """
            
            self.labelMaker = LabelMaker(max(33, len(label)))
            self.label = label
            self.baseLabel = label.strip()
            self.baseLabelSuffix = ''
            if self.baseLabel[-1] == ':':
                self.baseLabel = self.baseLabel[:-1]
                self.baseLabelSuffix = ':'
            self.previousPercentage = 0
            self.progressCallback = self.defaultProgressCallback
            if progressCallback:
                self.progressCallback = progressCallback

        def defaultProgressCallback(self, percentage, label = ''):
            """
            Default progress callback
            """
            progress_bar = (
                f'{Fore.BLUE}{("■" * int(percentage / 2))}{Fore.RESET}' \
                + f'{Fore.BLUE}{("□" * (50 - int(percentage / 2)))}{Fore.RESET}')
            print(('', '\x1b[K')[percentage < 100], end = '\r')
            print(f'{self.labelMaker.format(label)}{progress_bar} {Style.DIM}{int(percentage)}%'.strip() + f' {Style.RESET_ALL}',
                end = ('\n', '')[percentage < 100],
                flush = True)

        def updateProgressBar(self, percentage):
            """
            Update progress bar
            """
            
            percentage = int(percentage)
            if percentage != self.previousPercentage:
                if int(percentage)-int(self.previousPercentage) > 10:
                    for x in range(int(percentage)-int(self.previousPercentage)):
                        curPercentage = max(0, min(100, self.previousPercentage + x + 1))
                        self.progressCallback(curPercentage, label = self.label)
                        time.sleep(0.01)
                else:
                    self.progressCallback(percentage, label = self.label)
            self.previousPercentage = percentage


    class AudioStreamDownloadProgressBar(TerminalProgressBar):
        """
        Inner class to display audio stream download progress bar (extends TerminalProgressBar)
        """

        def update(self, stream, chunk, bytes_remaining):
            """
            Update progress bar
            """
            
            self.label = f'{self.baseLabel} ({stream.filesize_mb} Mb){self.baseLabelSuffix}'
            percentage = ((stream.filesize - bytes_remaining) / stream.filesize) * 100
            self.updateProgressBar(percentage)


    class CoverArtDownloadProgressBar(TerminalProgressBar):
        """
        Inner class to display cover art download progress bar (extends TerminalProgressBar)
        """
        
        def update(self, count, blockSize, totalSize):
            """
            Update progress bar
            """
            
            self.label = f'{self.baseLabel} ({int(totalSize / 1024)} Kb){self.baseLabelSuffix}'
            percentage = min([int(count * blockSize * 100 / totalSize), 100])
            self.updateProgressBar(percentage)


    class Mp3EncodingProgressBar(ProgressBarLogger):
        """
        Inner class extending ProgressBarLogger of "proglog" module which is expected
        by an AudioFileClip stream instance to log MP3 encoding progress
        """

        def __init__(self, progressCallback = None, label = '', **kwargs):
            """
            Construct a Mp3EncodingProgressBar
            """
            
            super().__init__(kwargs)
            self.progressBar = Song.TerminalProgressBar(progressCallback = progressCallback, label = label)

        def bars_callback(self, bar, attr, value, previousValue = None):
            """
            Implementation of ProgressBarLogger class abstract method
            """
            
            if previousValue is not None:
                percentage = int((value / self.bars[bar]['total']) * 100)
                self.progressBar.updateProgressBar(percentage)


    @staticmethod
    def sanitizeString(string): 
        """
        Sanitize a string (static method)
        """

        return re.sub(r'\s+', ' ', slugify(string or '',
        replacements = [['-', '(((DASH)))'], ['\'', '(((APOS)))']],
        regex_pattern = r'[\\<>*/":+`|=]+',
        lowercase = False,
        allow_unicode = True,
        separator = ' ').replace('(((DASH)))', '-').replace('(((APOS)))', '\'').strip())


    # Shazam API client (class property)
    shazamClient = Shazam()

    # Date of last request to Shazam API (class property)
    lastShazamRequestAt = 0


    @staticmethod
    async def createFromYoutube(
            youtubeId,
            destFolderPath, 
            shazamMatchThreshold = 50, 
            verbose = True, 
            useDefaultVerbosity = True,
            beforeConnectToVideo = None, 
            afterConnectToVideo = None,
            beforeDonwnloadAudio = None, 
            progressLoggerForDownloadAudio = None, 
            afterDownloadAudio = None,
            beforeEncodeToMp3 = None, 
            progressLoggerForEncodeToMp3 = None, 
            afterEncodeToMp3 = None,
            beforeDownloadCoverArt = None, 
            progressLoggerForDownloadCoverArt = None, 
            afterDownloadCoverArt = None, 
            onDeleteCoverArt = None,
            beforeShazamSong = None, 
            afterShazamSong = None):
        """
        Create a Song instance from YouTube (static method)
        """
        
        # Disable verbosity logging
        if verbose != True:
            beforeConnectToVideo = None 
            afterConnectToVideo = None
            beforeDonwnloadAudio = None 
            progressLoggerForDownloadAudio = None 
            afterDownloadAudio = None
            beforeEncodeToMp3 = None 
            progressLoggerForEncodeToMp3 = None 
            afterEncodeToMp3 = None
            beforeDownloadCoverArt = None 
            progressLoggerForDownloadCoverArt = None 
            afterDownloadCoverArt = None 
            onDeleteCoverArt = None
            beforeShazamSong = None 
            afterShazamSong = None

        # Activate default verbosity logging
        if verbose and useDefaultVerbosity:

            labelMaker = LabelMaker(33)
            
            async def beforeConnectToVideo(youtubeId):
                print(labelMaker.format('Connecting to YouTube API:') + f'Please, wait... ', end = '', flush = True)

            async def afterConnectToVideo(videoProps):
                print('\x1b[K', end = '\r')
                print(labelMaker.format('Connecting to YouTube API:') + f'Ready to import video "{videoProps.youtubeId}"')

            async def beforeDonwnloadAudio(videoProps, m4aPath):
                pass
    
            progressLoggerForDownloadAudio = SimpleNamespace(
                label = 'Streaming audio: ',
                callback = None)
    
            async def afterDownloadAudio(videoProps, m4aPath):
                pass
    
            async def beforeEncodeToMp3(videoProps, m4aPath, mp3Path):
                pass
    
            progressLoggerForEncodeToMp3 = SimpleNamespace(
                label = 'Encoding audio stream to MP3: ',
                callback = None)
    
            async def afterEncodeToMp3(videoProps, m4aPath, mp3Path):
                pass
    
            async def beforeDownloadCoverArt(song):
                pass
    
            progressLoggerForDownloadCoverArt = SimpleNamespace(
                label = 'Downloading cover art: ',
                callback = None)
    
            async def afterDownloadCoverArt(song):
                pass
    
            async def onDeleteCoverArt(song):
                pass
    
            async def beforeShazamSong(song):
                print(labelMaker.format('Shazaming audio track:') + f'Please, wait... ', end = '', flush = True)
    
            async def afterShazamSong(song):
                print('\x1b[K', end = '\r')
                print(labelMaker.format('Shazam match result:') 
                    + f'Artist: {Fore.LIGHTCYAN_EX}{song.shazamArtist}{Fore.RESET}, ' 
                    + f'Title: {Fore.LIGHTCYAN_EX}{song.shazamTitle}{Fore.RESET}, ' 
                    + f'Match: {Fore.LIGHTCYAN_EX}{song.shazamMatchLevel}%{Fore.RESET}')
 
        # Connect to YouTube video to get song information
        try:
            if beforeConnectToVideo is not None:
                await beforeConnectToVideo(youtubeId)
            # video = YouTube(f'https://youtube.com/watch?v={youtubeId}', use_oauth=True, allow_oauth_cache=True)
            video = YouTube(f'https://youtube.com/watch?v={youtubeId}', client='WEB')
            videoProps = SimpleNamespace(
                youtubeId = video.video_id,
                artist = video.author,
                title = video.title,
                coverArtUrl = video.thumbnail_url)
            if afterConnectToVideo is not None:
                await afterConnectToVideo(videoProps)
        except Exception as error:
            raise SongError(f'Failed to connect to YouTube video "{youtubeId}"', error)
        
        # Download YouTube video audio stream
        with tempfile.TemporaryDirectory() as tempDir:
            tempM4aPath = Path(tempDir) / 'temp.m4a'
            tempMp3Path = Path(destFolderPath) / 'temp (JUNK).mp3'
            try:
                if progressLoggerForDownloadAudio is not None:
                    logger = Song.AudioStreamDownloadProgressBar(
                        progressCallback = progressLoggerForDownloadAudio.callback, 
                        label = progressLoggerForDownloadAudio.label)
                    video.register_on_progress_callback(logger.update)
                if beforeDonwnloadAudio is not None:
                    await beforeDonwnloadAudio(videoProps, tempM4aPath)
                request.default_range_size = 1179648 # 1.12 MB chunk size (default is 9 MB)
                m4aStream = video.streams.get_audio_only()
                if m4aStream is None:
                    raise SongError('Cannot get audio stream from YouTube video')
                m4aStream.download(output_path = Path(tempDir), filename = 'temp.m4a')
                if afterDownloadAudio is not None:
                    await afterDownloadAudio(videoProps, tempM4aPath)
            except Exception as error:
                raise SongError('Failed to stream audio track from YouTube video', error)
            
            # Encode audio stream to MP3 file
            try:
                logger = None
                if progressLoggerForEncodeToMp3 is not None:
                    logger = Song.Mp3EncodingProgressBar(
                        progressCallback = progressLoggerForEncodeToMp3.callback, 
                        label = progressLoggerForEncodeToMp3.label)
                if beforeEncodeToMp3 is not None:
                    await beforeEncodeToMp3(videoProps, tempM4aPath, tempMp3Path)
                mp3Stream = AudioFileClip(str(tempM4aPath))
                mp3Stream.write_audiofile(
                    str(tempMp3Path), 
                    logger = logger)
                mp3Stream.close()
                if afterEncodeToMp3 is not None:
                    await afterEncodeToMp3(videoProps, tempM4aPath, tempMp3Path)
            except Exception as error:
                raise SongError('Failed to encode YouTube video audio stream to MP3', error)
            
            # Create song object from MP3 file and YouTube song information 
            song = Song(
                tempMp3Path,
                youtubeId = video.video_id,
                artist = video.author,
                title = video.title,
                coverArtUrl = video.thumbnail_url)
            
            # Get YouTube song cover art and save it in MP3 file
            await song.updateCoverArt(
                beforeDownloadCoverArt = beforeDownloadCoverArt, 
                progressLoggerForDownloadCoverArt = progressLoggerForDownloadCoverArt, 
                afterDownloadCoverArt = afterDownloadCoverArt, 
                onDeleteCoverArt = onDeleteCoverArt)
            
            # Submit song to Shazam API for recognition and update song state accordingly
            await song.shazamSong(
                shazamMatchThreshold = shazamMatchThreshold, 
                beforeShazamSong = beforeShazamSong, 
                afterShazamSong = afterShazamSong)
            
            # Get Shazam song covert art and save it in MP3 file
            await song.updateCoverArt(
                beforeDownloadCoverArt = beforeDownloadCoverArt, 
                progressLoggerForDownloadCoverArt = progressLoggerForDownloadCoverArt, 
                afterDownloadCoverArt = afterDownloadCoverArt, 
                onDeleteCoverArt = onDeleteCoverArt)
            
            # Rename MP3 file according to gathered song informaton
            # If Shazam recogntion failed or is too bad, mark song as junk
            song.fixFilename(markAsJunk = (song.shazamMatchLevel or 0) < shazamMatchThreshold)

            # Return created song object
            return song
    

    def __init__(self, mp3Path, youtubeId = None, artist = None, title = None, coverArtUrl = None, shazamMatchLevel = None):
        """
        Construct a Song instance from a MP3 file
        """
        
        # Check if song object is already initialized
        self.isAlreadyInitialized = getattr(self, 'isAlreadyInitialized', False)
        
        # Set song object attributes that depends on MP3 file only 
        self.path = Path(mp3Path)
        self.mp3 = mutagen.mp3.MP3(self.path)
        self.audioLength = self.mp3.info.length
        self.duration = '{:0>8}'.format(str(datetime.timedelta(seconds=round(self.audioLength))))
        self.filename = self.path.name
        self.hasJunkFilename = re.match(r'^.*\s\(JUNK\)\.mp3$', str(self.filename)) is not None
        self.labelFromFilename = self.path.name[:(-4, -11)[self.hasJunkFilename]]
        self.playlist = self.path.parent.name

        # Initialize song object attributes that will be computed later
        self.hasCoverArt = None
        self.shouldBeTagged = False
        self.shouldBeRenamed = False
        self.shouldBeShazamed = False

        # YouTube ID is required. Raise en error if it is missing.
        # Try to get it from constructor parameters first, then from current state, 
        # then from ID3 tags, then from MP3 filename.
        try:
            youtubeIdTag = self.mp3.tags['TXXX:YouTube ID'].text[0]
        except:
            youtubeIdTag = None
        self.youtubeId = youtubeId or getattr(self, 'youtubeId', None) or youtubeIdTag
        if not self.youtubeId:
            match = re.match(r'^.*\[(?P<youtubeId>[^\]]+)\]$', str(self.labelFromFilename))
            if match:
                self.youtubeId = match.group('youtubeId')
            else:
                raise SongError('YouTube ID is missing in MP3 file: ' + str(self.path))

        # Extract song name from filename
        self.songNameFromFileName = self.labelFromFilename
        match = (re.match(r'^(?P<songName>.*)\[(?P<youtubeId>[^\]]+)\]$', str(self.labelFromFilename)))
        if match and match.group('songName') and match.group('youtubeId') == self.youtubeId:
            self.songNameFromFileName = (match.group('songName')).strip()

        # Set song artist and title.
        # Try to get them from constructor parameters first or from current state.
        # At initialization time, also try to get them from ID3 tags, then from MP3 filename.
        self.artist = artist or getattr(self, 'artist', None)
        self.title = title or getattr(self, 'title', None)
        if not self.isAlreadyInitialized and (not self.artist or not self.title):
            try:
                self.artist = self.artist or self.mp3.tags['TPE1'].text[0]
            except:
                pass
            try:
                self.title = self.title or self.mp3.tags['TIT2'].text[0]
            except:
                pass
            match = re.match(r'^(?P<artist>.*)\s-\s(?P<title>.*)\s\[[^\]]+\]$', str(self.labelFromFilename))
            if match:
                self.artist = self.artist or match.group('artist')
                self.title = self.title or match.group('title')
            else:
                match = re.match(r'^(?P<title>.*)\s\[[^\]]+\]$', str(self.labelFromFilename))
                if match:
                    self.title = self.title or match.group('title')
        if self.artist:
            self.artist = re.sub(r'\s+', ' ', self.artist.strip())
        if self.title:
            self.title = re.sub(r'\s+', ' ', self.title.strip())

        # Set covert art URL. 
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.coverArtUrl = coverArtUrl or getattr(self, 'coverArtUrl', None)
        if not self.isAlreadyInitialized and not self.coverArtUrl:
            try:
                self.coverArtUrl = self.mp3.tags['TXXX:Cover art URL'].text[0]
            except:
                pass
            
        # Set Shazam artist.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazamArtist = getattr(self, 'shazamArtist', None)
        if not self.isAlreadyInitialized and not self.shazamArtist:
            try:
                self.shazamArtist = self.mp3.tags['TXXX:Shazam artist'].text[0]
            except:
                pass
            
        # Set Shazam title.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazamTitle = getattr(self, 'shazamTitle', None)
        if not self.isAlreadyInitialized and not self.shazamTitle:
            try:
                self.shazamTitle = self.mp3.tags['TXXX:Shazam title'].text[0]
            except:
                pass
            
        # Set Shazam cover art URL.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazamCoverArtUrl = getattr(self, 'shazamCoverArtUrl', None)
        if not self.isAlreadyInitialized and not self.shazamCoverArtUrl:
            try:
                self.shazamCoverArtUrl = self.mp3.tags['TXXX:Shazam cover art URL'].text[0]
            except:
                pass

        # Set Shazam match level.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        if shazamMatchLevel == 0:
            self.shazamMatchLevel = 0
        else:
            self.shazamMatchLevel = getattr(self, 'shazamMatchLevel', None)
            if not self.isAlreadyInitialized and self.shazamMatchLevel is None:
                try:
                    self.shazamMatchLevel = int(self.mp3.tags['TXXX:Shazam match level'].text[0])
                except:
                    pass
            
        # Update MP3 file ID3 tags if required
        # e.g. if song state is modified after initialization (deliberate recall of constructor)
        # or if song MP3 file was just created and not yet tagged
        if self.isAlreadyInitialized or youtubeIdTag is None:
            self.updateId3Tags()

        # Compute expected filenames
        artistLabel = Song.sanitizeString(self.artist).upper()
        titleLabel = Song.sanitizeString(self.title)
        titleLabel = titleLabel[:1].upper() + titleLabel[1:]
        self.expectedFilename = artistLabel + ('', ' - ')[bool(self.artist and self.title)] \
            + titleLabel + ('', ' ')[bool(self.artist or self.title)] + '[' + self.youtubeId + '].mp3'
        self.expectedJunkFilename = artistLabel + ('', ' - ')[bool(self.artist and self.title)] \
            + titleLabel + ('', ' ')[bool(self.artist or self.title)] + '[' + self.youtubeId + '] (JUNK).mp3'

        # Check if MP3 file should be tagged
        if not self.artist or not self.title:
            self.shouldBeTagged = True

        # Check if MP3 file should be shazamed
        if self.shazamMatchLevel is None:
            self.shouldBeShazamed = True

        # Check if MP3 file should be renamed
        if ((not self.hasJunkFilename and self.filename != self.expectedFilename) 
            or (self.hasJunkFilename and self.filename != self.expectedJunkFilename)):
            self.shouldBeRenamed = True

        # Check if MP3 file has a cover art
        try:
            self.hasCoverArt = self.mp3.tags['APIC:Cover art'].type == 3
        except:
            self.hasCoverArt = False

        # Mark song object as initialized
        self.isAlreadyInitialized = True


    def updateId3Tags(self):
        """
        Update ID3 tags of the Song MP3 file
        """
        
        # Create ID3 tag receptacle in MP3 file if none already exists
        if self.mp3.tags is None:
            self.mp3.tags = mutagen.id3.ID3()

        # Update or remove tag artist
        if self.artist:
            self.mp3.tags.add(TPE1(encoding = 3, text = u'' + self.artist))
        else:
            self.mp3.tags.delall('TPE1')

        # Update or remove tag title
        if self.title:
            self.mp3.tags.add(TIT2(encoding = 3, text = u'' + self.title))
        else:
            self.mp3.tags.delall('TPE1')

        # Delete all custom tags
        self.mp3.tags.delall('TXXX')

        # Set custom tag for YouTube ID
        self.mp3.tags.add(TXXX(encoding = 3,
            desc = u'YouTube ID',
            text = u'' + self.youtubeId))

        # Set custom tag for cover art URL if required
        if self.coverArtUrl:
            self.mp3.tags.add(TXXX(encoding = 3,
                desc = u'Cover art URL',
                text = u'' + self.coverArtUrl))

        # Set custom tag for Shazam match level if required
        if self.shazamMatchLevel is not None:
            self.mp3.tags.add(TXXX(encoding = 3,
                desc = u'Shazam match level',
                text = u'' + str(self.shazamMatchLevel)))

        # Set custom tag for Shazam artist if required
        if self.shazamArtist:
            self.mp3.tags.add(TXXX(encoding = 3,
                desc = u'Shazam artist',
                text = u'' + str(self.shazamArtist)))

        # Set custom tag for Shazam title if required
        if self.shazamTitle:
            self.mp3.tags.add(TXXX(encoding = 3,
                desc = u'Shazam title',
                text = u'' + str(self.shazamTitle)))

        # Set custom tag for Shazam cover art URL if required
        if self.shazamCoverArtUrl:
            self.mp3.tags.add(TXXX(encoding = 3,
                desc = u'Shazam cover art URL',
                text = u'' + str(self.shazamCoverArtUrl)))

        # Save tags
        self.mp3.save(v1 = 0, v2_version = 3)


    async def updateCoverArt(
            self,
            beforeDownloadCoverArt = None,
            progressLoggerForDownloadCoverArt = None,
            afterDownloadCoverArt = None,
            onDeleteCoverArt = None):
        """
        Update or delete covert art of the Song MP3 file
        Raise an error if covert art download fails
        """

        # Check if cover art must be updated or deleted
        try:
            self.hasCoverArt = self.mp3.tags['APIC:Cover art'].type == 3
            if not self.coverArtUrl:
                self.mp3.tags.delall('APIC')
                self.mp3.tags.delall('TXXX:Cover art URL')
                self.mp3.save(v1 = 0, v2_version = 3)
                self.hasCoverArt = False
                if onDeleteCoverArt is not None:
                    await onDeleteCoverArt(self)
                return
        except:
            self.hasCoverArt = False
        shouldCoverArtBeUpdated = False
        if self.coverArtUrl:
            shouldCoverArtBeUpdated = True
            if self.hasCoverArt:
                try:
                    if self.coverArtUrl == self.mp3.tags['TXXX:Stored cover art URL'].text[0]:
                        shouldCoverArtBeUpdated = False
                except:
                    shouldCoverArtBeUpdated = True

        # Update or remove cover art
        if shouldCoverArtBeUpdated :
            if beforeDownloadCoverArt is not None:
                await beforeDownloadCoverArt(self)
            with tempfile.TemporaryDirectory() as temporaryDirectoryPathname:
                temporaryFilePathname = Path(temporaryDirectoryPathname) / 'temp.jpg'
                progressBarCallback = None
                if progressLoggerForDownloadCoverArt is not None:
                    progressBarLogger = Song.CoverArtDownloadProgressBar(
                        progressCallback = progressLoggerForDownloadCoverArt.callback, 
                        label = progressLoggerForDownloadCoverArt.label)
                    progressBarCallback = progressBarLogger.update
                try:
                    urllib.request.urlretrieve(
                        self.coverArtUrl, 
                        temporaryFilePathname, 
                        progressBarCallback)
                except Exception as error:
                    raise SongError(f'Failed to download cover art') from error
                try:
                    with open(temporaryFilePathname, 'rb') as f:
                        self.mp3.tags.delall('APIC')
                        self.mp3.tags.add(APIC(
                            encoding = 3, # 3 is for utf-8
                            desc = u'Cover art',
                            mime = 'image/jpg', # image/jpeg or image/png
                            type = 3, # 3 is for the cover image
                            data = f.read()))
                        self.mp3.tags.add(TXXX(encoding = 3,
                            desc = u'Cover art URL',
                            text = u'' + self.coverArtUrl))
                        self.mp3.tags.add(TXXX(encoding = 3,
                            desc = u'Stored cover art URL',
                            text = u'' + self.coverArtUrl))
                except Exception as error:
                    raise SongError(f'Failed to add cover art to MP3 file') from error
                self.mp3.save(v1 = 0, v2_version = 3)
            self.hasCoverArt = True
            if afterDownloadCoverArt is not None:
                await afterDownloadCoverArt(self)


    async def shazamSong(
            self,
            shazamMatchThreshold = 50,
            beforeShazamSong = None,
            afterShazamSong = None):
        """
        Retrieve Song artist, title and cover art url from Shazam then compute matching rate
        """
        
        # Ask Shazam to recognize song
        # Wait for 15s min since last request to Shazam API.
        # If request fails, wait for 35s before retry.
        if beforeShazamSong is not None:
            await beforeShazamSong(self)
        try:
            diffTime = time.time() - Song.lastShazamRequestAt
            if (diffTime < 15):
                time.sleep(15 - diffTime)
            result = await self.shazamClient.recognize_song(str(self.path))
            Song.lastShazamRequestAt = time.time()
        except:
            diffTime = time.time() - Song.lastShazamRequestAt
            if (diffTime < 35):
                time.sleep(35 - diffTime)
            try:
                result = await self.shazamClient.recognize_song(str(self.path))
                Song.lastShazamRequestAt = time.time()
            except Exception as error:
                raise SongError('Shazam API seems out of service', error)
            
        # Update song state and related MP3 file according to Shazam result and compare returned artist and title
        # with current artist and title to compute matching rate using "fuzzy" string matching based on
        # levenshtein distance algorithm.
        if 'track' in result:
            try:
                title = result['track']['title'][:1].upper() + result['track']['title'][1:]
                artist = result['track']['subtitle'][:1].upper() + result['track']['subtitle'][1:]
                artistMatchingRate = fuzz.partial_token_sort_ratio(self.artist, artist, True)
                titleMatchingRate = fuzz.partial_token_sort_ratio(self.title, title, True)
                matchingRate = int((titleMatchingRate * 2 + artistMatchingRate) / 3)
                if matchingRate >= shazamMatchThreshold:
                    try:
                        coverArtUrl = result['track']['images']['coverart']
                        self.updateState(
                            artist = artist,
                            title = title,
                            coverArtUrl = coverArtUrl,
                            shazamArtist = artist,
                            shazamTitle = title,
                            shazamCoverArtUrl = coverArtUrl,
                            shazamMatchLevel = matchingRate)
                    except:
                        self.updateState(
                            artist = artist,
                            title = title,
                            shazamArtist = artist,
                            shazamTitle = title,
                            shazamMatchLevel = matchingRate)
                else:
                    self.updateState(
                        shazamArtist = artist,
                        shazamTitle = title,
                        shazamMatchLevel = matchingRate)
            except Exception as error:
                raise SongError('Unexpected Shazam result', error)
        else:
            self.updateState(shazamMatchLevel = 0)
        if afterShazamSong is not None:
            await afterShazamSong(self)


    def fixFilename(self, markAsJunk = None):
        """
        Fix Song MP3 filename (rename the MP3 file)
        """
        
        if not markAsJunk == True and not markAsJunk == False:
            markAsJunk = self.hasJunkFilename
        if self.shouldBeTagged:
            appropriateFilename = f'{self.songNameFromFileName} [{self.youtubeId}] (JUNK).mp3'
        else:
            appropriateFilename = (self.expectedFilename, self.expectedJunkFilename)[markAsJunk]
        try:
            self.path = self.path.rename(self.path.parent / appropriateFilename)
        except:
            raise SongError('Failed to rename song MP3 file')
        self.updateState()


    def updateState(
            self,
            artist = False,
            title = False,
            coverArtUrl = False,
            shazamArtist = False,
            shazamTitle = False,
            shazamCoverArtUrl = False,
            shazamMatchLevel = -1):
        """
        Update song state and related MP3 file ID3 tags
        """
        
        self.artist = (self.artist, artist)[artist != False]
        self.title = (self.title, title)[title != False]
        self.coverArtUrl = (self.coverArtUrl, coverArtUrl)[coverArtUrl != False]
        self.shazamArtist = (self.shazamArtist, shazamArtist)[shazamArtist != False]
        self.shazamTitle = (self.shazamTitle, shazamTitle)[shazamTitle != False]
        self.shazamCoverArtUrl = (self.shazamCoverArtUrl, shazamCoverArtUrl)[shazamCoverArtUrl != False]
        self.shazamMatchLevel = (self.shazamMatchLevel, shazamMatchLevel)[shazamMatchLevel != -1]
        self.__init__(self.path, self.youtubeId)


    def resetState(self):
        """
        Reset Song state and remove covert art and ID3 tags 
        from related MP3 file (excepted tag holding YouTube ID)
        """
        
        self.artist = None 
        self.title = None 
        self.coverArtUrl = None  
        self.shazamArtist = None
        self.shazamTitle = None
        self.shazamCoverArtUrl = None
        self.shazamMatchLevel = None
        self.__init__(self.path, self.youtubeId)