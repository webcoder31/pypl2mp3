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
from pypl2mp3.libs.utils import LabelFormatter


class SongError(Exception):
    """
    Song error class
    """
    
    def __init__(self, message, errors=None):
        """
        Construct a SongError
        """
                  
        super().__init__(message)
        if errors:
            print(errors)


class SongModel:
    """
    Song class
    NOTE: MP3 files are saved in ID3v2.3 only, without ID3v1 (default is ID3v2.4)
    """


    class TerminalProgressBar():
        """
        Inner base class providing a method in charge of printing progress bar in terminal
        """

        def __init__(self, progress_callback=None, label=""):
            """
            Construct a TerminalProgressBar
            """
            
            self.label_formatter = LabelFormatter(max(33, len(label)))
            self.label = label
            self.base_label = label.strip()
            self.base_label_suffix = ""
            if self.base_label[-1] == ":":
                self.base_label = self.base_label[:-1]
                self.base_label_suffix = ":"
            self.previous_percentage = 0
            self.progress_callback = self.default_progress_callback
            if progress_callback:
                self.progress_callback = progress_callback

        def default_progress_callback(self, percentage, label=""):
            """
            Default progress callback
            """
            progress_bar = (
                f"{Fore.BLUE}{('■' * int(percentage / 2))}{Fore.RESET}" \
                + f"{Fore.BLUE}{('□' * (50 - int(percentage / 2)))}{Fore.RESET}"
            )
            print(("", "\x1b[K")[percentage < 100], end="\r")
            print(f"{self.label_formatter.format(label)}{progress_bar}" 
                  + " {Style.DIM}{int(percentage)}%".strip() 
                  + f" {Style.RESET_ALL}",
                end=("\n", "")[percentage < 100],
                flush=True
            )

        def update_progress_bar(self, percentage):
            """
            Update progress bar
            """
            
            percentage = int(percentage)
            if percentage != self.previous_percentage:
                if int(percentage)-int(self.previous_percentage) > 10:
                    for x in range(int(percentage)-int(self.previous_percentage)):
                        cur_percentage = max(0, min(100, self.previous_percentage + x + 1))
                        self.progress_callback(cur_percentage, label=self.label)
                        time.sleep(0.01)
                else:
                    self.progress_callback(percentage, label=self.label)
            self.previous_percentage = percentage


    class AudioStreamDownloadProgressBar(TerminalProgressBar):
        """
        Inner class to display audio stream download progress bar (extends TerminalProgressBar)
        """

        def update(self, stream, chunk, bytes_remaining):
            """
            Update progress bar
            """
            
            self.label = f"{self.base_label} ({stream.filesize_mb} Mb){self.base_label_suffix}"
            percentage = ((stream.filesize - bytes_remaining) / stream.filesize) * 100
            self.update_progress_bar(percentage)


    class CoverArtDownloadProgressBar(TerminalProgressBar):
        """
        Inner class to display cover art download progress bar (extends TerminalProgressBar)
        """
        
        def update(self, count, block_size, total_size):
            """
            Update progress bar
            """
            
            self.label = f"{self.base_label} ({int(total_size / 1024)} Kb){self.base_label_suffix}"
            percentage = min([int(count * block_size * 100 / total_size), 100])
            self.update_progress_bar(percentage)


    class Mp3EncodingProgressBar(ProgressBarLogger):
        """
        Inner class extending ProgressBarLogger of "proglog" module which is expected
        by an AudioFileClip stream instance to log MP3 encoding progress
        """

        def __init__(self, progress_callback=None, label="", **kwargs):
            """
            Construct a Mp3EncodingProgressBar
            """
            
            super().__init__(kwargs)
            self.progress_bar = SongModel.TerminalProgressBar(
                progress_callback=progress_callback, 
                label=label
            )

        def bars_callback(self, bar, attr, value, previous_value=None):
            """
            Implementation of ProgressBarLogger class abstract method
            """
            
            if previous_value is not None:
                percentage = int((value / self.bars[bar]["total"]) * 100)
                self.progress_bar.update_progress_bar(percentage)


    @staticmethod
    def sanitize_string(string): 
        """
        Sanitize a string (static method)
        """
        string = slugify(string or "",
            replacements=[["-", "(((DASH)))"], ["\'", "(((APOS)))"]],
            regex_pattern=r"[\\<>*/\":+`|=]+",
            lowercase=False,
            allow_unicode=True,
            separator=" "
        ).replace("(((DASH)))", "-").replace("(((APOS)))", "\'").strip()

        return re.sub(r"\s+", " ", string)


    # Shazam API client (class property)
    shazam_client = Shazam()

    # Date of last request to Shazam API (class property)
    last_shazam_request_time = 0


    @staticmethod
    async def create_from_youtube(
            youtube_id,
            dest_folder_path, 
            shazam_match_threshold=50, 
            verbose=True, 
            use_default_verbosity=True,
            before_connect_to_video=None, 
            after_connect_to_video=None,
            before_download_audio=None, 
            progress_logger_for_download_audio=None, 
            after_download_audio=None,
            before_encode_to_mp3=None, 
            progress_logger_for_encode_to_mp3=None, 
            after_encode_to_mp3=None,
            before_download_cover_art=None, 
            progress_logger_for_download_cover_art=None, 
            after_download_cover_art=None, 
            on_delete_cover_art=None,
            before_shazam_song=None, 
            after_shazam_song=None
        ):
        """
        Create a Song instance from YouTube (static method)
        """
        
        # Disable verbosity logging
        if verbose != True:
            before_connect_to_video = None 
            after_connect_to_video = None
            before_download_audio = None 
            progress_logger_for_download_audio = None 
            after_download_audio = None
            before_encode_to_mp3 = None 
            progress_logger_for_encode_to_mp3 = None 
            after_encode_to_mp3 = None
            before_download_cover_art = None 
            progress_logger_for_download_cover_art = None 
            after_download_cover_art = None 
            on_delete_cover_art = None
            before_shazam_song = None 
            after_shazam_song = None

        # Activate default verbosity logging
        if verbose and use_default_verbosity:

            label_formatter = LabelFormatter(33)
            
            async def before_connect_to_video(youtube_id):
                print(
                    label_formatter.format("Connecting to YouTube API:") 
                    + f"Please, wait... ", end="", flush=True
                )

            async def after_connect_to_video(video_properties):
                print("\x1b[K", end="\r")
                print(
                    label_formatter.format("Connecting to YouTube API:") 
                    + f"Ready to import video \"{video_properties.youtube_id}\""
                )

            async def before_download_audio(video_properties, m4aPath):
                pass
    
            progress_logger_for_download_audio = SimpleNamespace(
                label="Streaming audio: ",
                callback=None
            )
    
            async def after_download_audio(video_properties, m4aPath):
                pass
    
            async def before_encode_to_mp3(video_properties, m4aPath, mp3_path):
                pass
    
            progress_logger_for_encode_to_mp3 = SimpleNamespace(
                label="Encoding audio stream to MP3: ",
                callback=None
            )
    
            async def after_encode_to_mp3(video_properties, m4aPath, mp3_path):
                pass
    
            async def before_download_cover_art(song):
                pass
    
            progress_logger_for_download_cover_art = SimpleNamespace(
                label="Downloading cover art: ",
                callback=None
            )
    
            async def after_download_cover_art(song):
                pass
    
            async def on_delete_cover_art(song):
                pass
    
            async def before_shazam_song(song):
                print(
                    label_formatter.format("Shazaming audio track:") 
                    + f"Please, wait... ", end="", flush=True
                )
    
            async def after_shazam_song(song):
                print("\x1b[K", end="\r")
                print(label_formatter.format("Shazam match result:") 
                    + f"Artist: {Fore.LIGHTCYAN_EX}{song.shazam_artist}{Fore.RESET}, " 
                    + f"Title: {Fore.LIGHTCYAN_EX}{song.shazam_title}{Fore.RESET}, " 
                    + f"Match: {Fore.LIGHTCYAN_EX}{song.shazam_match_score}%{Fore.RESET}"
                )
 
        # Connect to YouTube video to get song information
        try:
            if before_connect_to_video is not None:
                await before_connect_to_video(youtube_id)
            video = YouTube(f"https://youtube.com/watch?v={youtube_id}", client="WEB")
            video_properties = SimpleNamespace(
                youtube_id=video.video_id,
                artist=video.author,
                title=video.title,
                cover_art_url=video.thumbnail_url
            )
            if after_connect_to_video is not None:
                await after_connect_to_video(video_properties)
        except Exception as error:
            raise SongError(f"Failed to connect to YouTube video \"{youtube_id}\"", error)
        
        # Download YouTube video audio stream
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_m4a_path = Path(temp_dir) / "temp.m4a"
            temp_mp3_path = Path(dest_folder_path) / "temp (JUNK).mp3"
            try:
                if progress_logger_for_download_audio is not None:
                    logger = SongModel.AudioStreamDownloadProgressBar(
                        progress_callback=progress_logger_for_download_audio.callback, 
                        label=progress_logger_for_download_audio.label
                    )
                    video.register_on_progress_callback(logger.update)
                if before_download_audio is not None:
                    await before_download_audio(video_properties, temp_m4a_path)
                request.default_range_size = 1179648 # 1.12 MB chunk size (default is 9 MB)
                m4a_stream = video.streams.get_audio_only()
                if m4a_stream is None:
                    raise SongError("Cannot get audio stream from YouTube video")
                m4a_stream.download(output_path=Path(temp_dir), filename="temp.m4a")
                if after_download_audio is not None:
                    await after_download_audio(video_properties, temp_m4a_path)
            except Exception as error:
                raise SongError("Failed to stream audio track from YouTube video", error)
            
            # Encode audio stream to MP3 file
            try:
                logger = None
                if progress_logger_for_encode_to_mp3 is not None:
                    logger = SongModel.Mp3EncodingProgressBar(
                        progress_callback=progress_logger_for_encode_to_mp3.callback, 
                        label=progress_logger_for_encode_to_mp3.label
                    )
                if before_encode_to_mp3 is not None:
                    await before_encode_to_mp3(video_properties, temp_m4a_path, temp_mp3_path)
                mp3_stream = AudioFileClip(str(temp_m4a_path))
                mp3_stream.write_audiofile(str(temp_mp3_path), logger=logger)
                mp3_stream.close()
                if after_encode_to_mp3 is not None:
                    await after_encode_to_mp3(video_properties, temp_m4a_path, temp_mp3_path)
            except Exception as error:
                raise SongError("Failed to encode YouTube video audio stream to MP3", error)
            
            # Create song object from MP3 file and YouTube song information 
            song = SongModel(
                temp_mp3_path,
                youtube_id=video.video_id,
                artist=video.author,
                title=video.title,
                cover_art_url=video.thumbnail_url
            )
            
            # Get YouTube song cover art and save it in MP3 file
            await song.update_cover_art(
                before_download_cover_art=before_download_cover_art, 
                progress_logger_for_download_cover_art=progress_logger_for_download_cover_art, 
                after_download_cover_art=after_download_cover_art, 
                on_delete_cover_art=on_delete_cover_art
            )
            
            # Submit song to Shazam API for recognition and update song state accordingly
            await song.shazam_song(
                shazam_match_threshold=shazam_match_threshold, 
                before_shazam_song=before_shazam_song, 
                after_shazam_song=after_shazam_song
            )
            
            # Get Shazam song covert art and save it in MP3 file
            await song.update_cover_art(
                before_download_cover_art=before_download_cover_art, 
                progress_logger_for_download_cover_art=progress_logger_for_download_cover_art, 
                after_download_cover_art=after_download_cover_art, 
                on_delete_cover_art=on_delete_cover_art
            )
            
            # Rename MP3 file according to gathered song informaton
            # If Shazam recogntion failed or is too bad, mark song as junk
            song.fix_filename(mark_as_junk=(song.shazam_match_score or 0) < shazam_match_threshold)

            # Return created song object
            return song
    

    def __init__(
            self, 
            mp3_path, 
            youtube_id=None, 
            artist=None, 
            title=None, 
            cover_art_url=None, 
            shazam_match_score=None
        ):
        """
        Construct a Song instance from a MP3 file
        """
        
        # Check if song object is already initialized
        self.is_already_initialized = getattr(self, "is_already_initialized", False)
        
        # Set song object attributes that depends on MP3 file only 
        self.path = Path(mp3_path)
        self.mp3 = mutagen.mp3.MP3(self.path)
        self.audio_length = self.mp3.info.length
        self.duration = "{:0>8}".format(str(datetime.timedelta(seconds=round(self.audio_length))))
        self.filename = self.path.name
        self.has_junk_filename = re.match(r"^.*\s\(JUNK\)\.mp3$", str(self.filename)) is not None
        self.label_from_filename = self.path.name[:(-4, -11)[self.has_junk_filename]]
        self.playlist = self.path.parent.name

        # Initialize song object attributes that will be computed later
        self.has_cover_art = None
        self.should_be_tagged = False
        self.should_be_renamed = False
        self.should_be_shazamed = False

        # YouTube ID is required. Raise en error if it is missing.
        # Try to get it from constructor parameters first, then from current state, 
        # then from ID3 tags, then from MP3 filename.
        try:
            youtube_id_tag = self.mp3.tags["TXXX:YouTube ID"].text[0]
        except:
            youtube_id_tag = None
        self.youtube_id = youtube_id or getattr(self, "youtube_id", None) or youtube_id_tag
        if not self.youtube_id:
            match = re.match(r"^.*\[(?P<youtube_id>[^\]]+)\]$", str(self.label_from_filename))
            if match:
                self.youtube_id = match.group("youtube_id")
            else:
                raise SongError("YouTube ID is missing in MP3 file: " + str(self.path))

        # Extract song name from filename
        self.song_name_from_filename = self.label_from_filename
        match = (re.match(r"^(?P<song_name>.*)\[(?P<youtube_id>[^\]]+)\]$", str(self.label_from_filename)))
        if match and match.group("song_name") and match.group("youtube_id") == self.youtube_id:
            self.song_name_from_filename = (match.group("song_name")).strip()

        # Set song artist and title.
        # Try to get them from constructor parameters first or from current state.
        # At initialization time, also try to get them from ID3 tags, then from MP3 filename.
        self.artist = artist or getattr(self, "artist", None)
        self.title = title or getattr(self, "title", None)
        if not self.is_already_initialized and (not self.artist or not self.title):
            try:
                self.artist = self.artist or self.mp3.tags["TPE1"].text[0]
            except:
                pass
            try:
                self.title = self.title or self.mp3.tags["TIT2"].text[0]
            except:
                pass
            match = re.match(r"^(?P<artist>.*)\s-\s(?P<title>.*)\s\[[^\]]+\]$", str(self.label_from_filename))
            if match:
                self.artist = self.artist or match.group("artist")
                self.title = self.title or match.group("title")
            else:
                match = re.match(r"^(?P<title>.*)\s\[[^\]]+\]$", str(self.label_from_filename))
                if match:
                    self.title = self.title or match.group("title")
        if self.artist:
            self.artist = re.sub(r"\s+", " ", self.artist.strip())
        if self.title:
            self.title = re.sub(r"\s+", " ", self.title.strip())

        # Set covert art URL. 
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.cover_art_url = cover_art_url or getattr(self, "cover_art_url", None)
        if not self.is_already_initialized and not self.cover_art_url:
            try:
                self.cover_art_url = self.mp3.tags["TXXX:Cover art URL"].text[0]
            except:
                pass
            
        # Set Shazam artist.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazam_artist = getattr(self, "shazam_artist", None)
        if not self.is_already_initialized and not self.shazam_artist:
            try:
                self.shazam_artist = self.mp3.tags["TXXX:Shazam artist"].text[0]
            except:
                pass
            
        # Set Shazam title.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazam_title = getattr(self, "shazam_title", None)
        if not self.is_already_initialized and not self.shazam_title:
            try:
                self.shazam_title = self.mp3.tags["TXXX:Shazam title"].text[0]
            except:
                pass
            
        # Set Shazam cover art URL.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazam_cover_art_url = getattr(self, "shazam_cover_art_url", None)
        if not self.is_already_initialized and not self.shazam_cover_art_url:
            try:
                self.shazam_cover_art_url = self.mp3.tags["TXXX:Shazam cover art URL"].text[0]
            except:
                pass

        # Set Shazam match level.
        # Try to get it from constructor parameters first or from current state.
        # At initialization time, also try to get it from ID3 tags.
        if shazam_match_score == 0:
            self.shazam_match_score = 0
        else:
            self.shazam_match_score = getattr(self, "shazam_match_score", None)
            if not self.is_already_initialized and self.shazam_match_score is None:
                try:
                    self.shazam_match_score = int(self.mp3.tags["TXXX:Shazam match level"].text[0])
                except:
                    pass
            
        # Update MP3 file ID3 tags if required
        # e.g. if song state is modified after initialization (deliberate recall of constructor)
        # or if song MP3 file was just created and not yet tagged
        if self.is_already_initialized or youtube_id_tag is None:
            self.update_id3_tags()

        # Compute expected filenames
        artist_label = SongModel.sanitize_string(self.artist).upper()
        title_label = SongModel.sanitize_string(self.title)
        title_label = title_label[:1].upper() + title_label[1:]
        self.expected_filename = artist_label + ("", " - ")[bool(self.artist and self.title)] \
            + title_label + ("", " ")[bool(self.artist or self.title)] + "[" + self.youtube_id + "].mp3"
        self.expected_junk_filename = artist_label + ("", " - ")[bool(self.artist and self.title)] \
            + title_label + ("", " ")[bool(self.artist or self.title)] + "[" + self.youtube_id + "] (JUNK).mp3"

        # Check if MP3 file should be tagged
        if not self.artist or not self.title:
            self.should_be_tagged = True

        # Check if MP3 file should be shazamed
        if self.shazam_match_score is None:
            self.should_be_shazamed = True

        # Check if MP3 file should be renamed
        if ((not self.has_junk_filename and self.filename != self.expected_filename) 
            or (self.has_junk_filename and self.filename != self.expected_junk_filename)
        ):
            self.should_be_renamed = True

        # Check if MP3 file has a cover art
        try:
            self.has_cover_art = self.mp3.tags["APIC:Cover art"].type == 3
        except:
            self.has_cover_art = False

        # Mark song object as initialized
        self.is_already_initialized = True


    def update_id3_tags(self):
        """
        Update ID3 tags of the Song MP3 file
        """
        
        # Create ID3 tag receptacle in MP3 file if none already exists
        if self.mp3.tags is None:
            self.mp3.tags = mutagen.id3.ID3()

        # Update or remove tag artist
        if self.artist:
            self.mp3.tags.add(TPE1(
                encoding=3, text=u"" + self.artist
            ))
        else:
            self.mp3.tags.delall("TPE1")

        # Update or remove tag title
        if self.title:
            self.mp3.tags.add(TIT2(
                encoding=3, 
                text=u"" + self.title
            ))
        else:
            self.mp3.tags.delall("TPE1")

        # Delete all custom tags
        self.mp3.tags.delall("TXXX")

        # Set custom tag for YouTube ID
        self.mp3.tags.add(TXXX(
            encoding=3,
            desc=u"YouTube ID",
            text=u"" + self.youtube_id
        ))

        # Set custom tag for cover art URL if required
        if self.cover_art_url:
            self.mp3.tags.add(TXXX(
                encoding=3,
                desc=u"Cover art URL",
                text=u"" + self.cover_art_url
            ))

        # Set custom tag for Shazam match level if required
        if self.shazam_match_score is not None:
            self.mp3.tags.add(TXXX(
                encoding=3,
                desc=u"Shazam match level",
                text=u"" + str(self.shazam_match_score)
            ))

        # Set custom tag for Shazam artist if required
        if self.shazam_artist:
            self.mp3.tags.add(TXXX(
                encoding=3,
                desc=u"Shazam artist",
                text=u"" + str(self.shazam_artist)
            ))

        # Set custom tag for Shazam title if required
        if self.shazam_title:
            self.mp3.tags.add(TXXX(
                encoding=3,
                desc=u"Shazam title",
                text=u"" + str(self.shazam_title)
            ))

        # Set custom tag for Shazam cover art URL if required
        if self.shazam_cover_art_url:
            self.mp3.tags.add(TXXX(
                encoding=3,
                desc=u"Shazam cover art URL",
                text=u"" + str(self.shazam_cover_art_url)
            ))

        # Save tags
        self.mp3.save(v1=0, v2_version=3)


    async def update_cover_art(
            self,
            before_download_cover_art=None,
            progress_logger_for_download_cover_art=None,
            after_download_cover_art=None,
            on_delete_cover_art=None
        ):
        """
        Update or delete covert art of the Song MP3 file
        Raise an error if covert art download fails
        """

        # Check if cover art must be updated or deleted
        try:
            self.has_cover_art = self.mp3.tags["APIC:Cover art"].type == 3
            if not self.cover_art_url:
                self.mp3.tags.delall("APIC")
                self.mp3.tags.delall("TXXX:Cover art URL")
                self.mp3.save(v1=0, v2_version=3)
                self.has_cover_art = False
                if on_delete_cover_art is not None:
                    await on_delete_cover_art(self)
                return
        except:
            self.has_cover_art = False
        should_cover_art_be_updated = False
        if self.cover_art_url:
            should_cover_art_be_updated = True
            if self.has_cover_art:
                try:
                    if self.cover_art_url == self.mp3.tags["TXXX:Stored cover art URL"].text[0]:
                        should_cover_art_be_updated = False
                except:
                    should_cover_art_be_updated = True

        # Update or remove cover art
        if should_cover_art_be_updated :
            if before_download_cover_art is not None:
                await before_download_cover_art(self)
            with tempfile.TemporaryDirectory() as temporary_directory_pathname:
                temporary_file_pathname = Path(temporary_directory_pathname) / "temp.jpg"
                progress_bar_callback = None
                if progress_logger_for_download_cover_art is not None:
                    progress_bar_logger = SongModel.CoverArtDownloadProgressBar(
                        progress_callback=progress_logger_for_download_cover_art.callback, 
                        label=progress_logger_for_download_cover_art.label
                    )
                    progress_bar_callback = progress_bar_logger.update
                try:
                    urllib.request.urlretrieve(
                        self.cover_art_url, 
                        temporary_file_pathname, 
                        progress_bar_callback
                    )
                except Exception as error:
                    raise SongError(f"Failed to download cover art") from error
                try:
                    with open(temporary_file_pathname, "rb") as f:
                        self.mp3.tags.delall("APIC")
                        self.mp3.tags.add(APIC(
                            encoding=3, # 3 is for utf-8
                            desc=u"Cover art",
                            mime="image/jpg", # image/jpeg or image/png
                            type=3, # 3 is for the cover image
                            data=f.read())
                        )
                        self.mp3.tags.add(TXXX(
                            encoding=3,
                            desc=u"Cover art URL",
                            text=u"" + self.cover_art_url
                        ))
                        self.mp3.tags.add(TXXX(
                            encoding=3,
                            desc=u"Stored cover art URL",
                            text=u"" + self.cover_art_url
                        ))
                except Exception as error:
                    raise SongError(f"Failed to add cover art to MP3 file") from error
                self.mp3.save(v1=0, v2_version=3)
            self.has_cover_art = True
            if after_download_cover_art is not None:
                await after_download_cover_art(self)


    async def shazam_song(
            self,
            shazam_match_threshold=50,
            before_shazam_song=None,
            after_shazam_song=None
        ):
        """
        Retrieve Song artist, title and cover art url from Shazam then compute matching rate
        """
        
        # Ask Shazam to recognize song.
        # Wait for 15s min since last request to Shazam API.
        # If request fails, wait for 35s before retry.
        if before_shazam_song is not None:
            await before_shazam_song(self)
        try:
            diff_time = time.time() - SongModel.last_shazam_request_time
            if diff_time < 15:
                time.sleep(15 - diff_time)
            result = await self.shazam_client.recognize_song(str(self.path))
            SongModel.last_shazam_request_time = time.time()
        except:
            diff_time = time.time() - SongModel.last_shazam_request_time
            if diff_time < 35:
                time.sleep(35 - diff_time)
            try:
                result = await self.shazam_client.recognize_song(str(self.path))
                SongModel.last_shazam_request_time = time.time()
            except Exception as error:
                raise SongError("Shazam API seems out of service", error)
            
        # Update song state and related MP3 file according to Shazam result and 
        # compare returned artist and title with current artist and title to compute 
        # matching rate using "fuzzy" string matching based on levenshtein distance algorithm.
        if "track" in result:
            try:
                title = result["track"]["title"][:1].upper() + result["track"]["title"][1:]
                artist = result["track"]["subtitle"][:1].upper() + result["track"]["subtitle"][1:]
                artist_match_score = fuzz.partial_token_sort_ratio(self.artist, artist, True)
                title_match_score = fuzz.partial_token_sort_ratio(self.title, title, True)
                match_score = int((title_match_score * 2 + artist_match_score) / 3)
                if match_score >= shazam_match_threshold:
                    try:
                        cover_art_url = result["track"]["images"]["coverart"]
                        self.update_state(
                            artist=artist,
                            title=title,
                            cover_art_url=cover_art_url,
                            shazam_artist=artist,
                            shazam_title=title,
                            shazam_cover_art_url=cover_art_url,
                            shazam_match_score=match_score
                        )
                    except:
                        self.update_state(
                            artist=artist,
                            title=title,
                            shazam_artist=artist,
                            shazam_title=title,
                            shazam_match_score=match_score
                        )
                else:
                    self.update_state(
                        shazam_artist=artist,
                        shazam_title=title,
                        shazam_match_score=match_score
                    )
            except Exception as error:
                raise SongError("Unexpected Shazam result", error)
        else:
            self.update_state(shazam_match_score=0)
        if after_shazam_song is not None:
            await after_shazam_song(self)


    def fix_filename(self, mark_as_junk=None):
        """
        Fix Song MP3 filename (rename the MP3 file)
        """
        if not mark_as_junk == True and not mark_as_junk == False:
            mark_as_junk = self.has_junk_filename
        if self.should_be_tagged:
            appropriate_filename = f"{self.song_name_from_filename} [{self.youtube_id}] (JUNK).mp3"
        else:
            appropriate_filename = (self.expected_filename, self.expected_junk_filename)[mark_as_junk]
        try:
            self.path = self.path.rename(self.path.parent / appropriate_filename)
        except:
            raise SongError("Failed to rename song MP3 file")
        self.update_state()


    def update_state(
            self,
            artist=False,
            title=False,
            cover_art_url=False,
            shazam_artist=False,
            shazam_title=False,
            shazam_cover_art_url=False,
            shazam_match_score=-1
        ):
        """
        Update song state and related MP3 file ID3 tags
        """
        self.artist = (self.artist, artist)[artist != False]
        self.title = (self.title, title)[title != False]
        self.cover_art_url = (self.cover_art_url, cover_art_url)[cover_art_url != False]
        self.shazam_artist = (self.shazam_artist, shazam_artist)[shazam_artist != False]
        self.shazam_title = (self.shazam_title, shazam_title)[shazam_title != False]
        self.shazam_cover_art_url = (self.shazam_cover_art_url, shazam_cover_art_url)[shazam_cover_art_url != False]
        self.shazam_match_score = (self.shazam_match_score, shazam_match_score)[shazam_match_score != -1]
        self.__init__(self.path, self.youtube_id)


    def reset_state(self):
        """
        Reset Song state and remove covert art and ID3 tags 
        from related MP3 file (excepted tag holding YouTube ID)
        """
        self.artist = None 
        self.title = None 
        self.cover_art_url = None  
        self.shazam_artist = None
        self.shazam_title = None
        self.shazam_cover_art_url = None
        self.shazam_match_score = None
        self.__init__(self.path, self.youtube_id)