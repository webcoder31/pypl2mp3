#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides song model class for importing and converting
YouTube video to MP3, Shazam recognition and handling song metadata.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""


# Python core modules
from dataclasses import dataclass
import datetime
from pathlib import Path
import re
import tempfile
import time
from types import SimpleNamespace
from typing import Callable
import urllib.request

# Third party packages
from colorama import Fore, Style, init
from moviepy.editor import AudioFileClip
from mutagen.id3 import TIT2, TPE1, TXXX, APIC
import mutagen.mp3
from proglog import ProgressBarLogger
from pytubefix import YouTube, request
from shazamio import Shazam
from slugify import slugify
from thefuzz import fuzz

# pypl2mp3 libs
from pypl2mp3.libs.exceptions import AppBaseException
from pypl2mp3.libs.utils import LabelFormatter

# Automatically clear style on each print
init(autoreset=True)


class SongModelException(AppBaseException):
    """
    Custom exception for song model errors.
    """
    pass


@dataclass
class ProgressBarInterface:
    """
    Interface to be used to provide custom progress bar leveraged during 
    song import (see SongModel.create_from_youtube() method)
    """

    label: str = ""
    callback: Callable | None = None


class SongModel:
    """
    Song model class representing a song object
    
    Note: MP3 files are saved with ID3v2.3 tags only
    """


    class TerminalProgressBar():
        """
        Inner base class providing a method in charge 
        of printing a progress bar in the terminal
        """


        def __init__(self, 
                progress_callback: Callable = None, 
                label: str = ""
            ):
            """
            Construct a TerminalProgressBar

            Args:
                progress_callback: Callback function in charge of displaying 
                    the progress bar. On progress changes, it will be called 
                    with two arguments:
                        - The cnew completion percentage
                        - The label provided here (see bellow)
                    See display_progress_bar() function as an example.
                label: Label that prepend the progress bar
            """

            self.label_formatter = LabelFormatter(min(33, len(label)))
            self.label = label
            self.label_base = label.strip()
            self.label_suffix = ""

            if self.label_base[-1] == ":":
                self.label_base = self.label_base[:-1]
                self.label_suffix = ":"

            self.progress_value = 0

            # Set the callback in charge of displaying the progress bar
            # If none provided use the default one
            if progress_callback:
                self.progress_callback = progress_callback
            else:
                self.progress_callback = self.display_progress_bar


        def display_progress_bar(self, 
                progress_value: int, 
                label: str = ""
            ) -> None:
            """
            Default callback in charge of displaying the progress bar

            Args:
                progress_value: Percentage of completion
                label: Label to display on the progress bar
            """

            progress_bar = (f"{Fore.LIGHTRED_EX}"
                + f"{('■' * int(progress_value / 2))}"
                + f"{('□' * (50 - int(progress_value / 2)))}"
                + f"{Fore.RESET}"
            )

            print(("", "\x1b[K")[progress_value < 100], end="\r")
            print((f"{self.label_formatter.format(label)}" 
                + f"{progress_bar}"
                + f" {Style.DIM}{int(progress_value)}%").strip()
                + f" {Style.RESET_ALL}",
                end=("\n", "")[progress_value < 100],
                flush=True
            )


        def update_progress_bar(self, new_value: float) -> None:
            """
            Update progress bar current value and invoke the callback defined
            to update the display

            Note: This method should be used by TerminalProgressBar subclasses
            to update the progress bar. It must not be overriden by subclasses.

            Args:
                progress_value: Percentage of completion
            """

            new_value = int(new_value)

            if new_value != self.progress_value:

                if new_value - self.progress_value > 10:
                    # If progress_value is too high, update progress bar 
                    # by small steps to avoid flickering
                    for value in range(self.progress_value, new_value + 1):
                        # Update the display of the progress bar
                        self.progress_callback(
                            max(0, min(100, value)), 
                            label=self.label
                        )
                        time.sleep(0.01)
                else:
                    self.progress_callback(new_value, label=self.label)

            self.progress_value = new_value


        def update(self, new_value: float) -> None:
            """
            Update progress bar

            Note: This method should be used by TerminalProgressBar class 
            direct instances to update the progress bar.

            It may be overriden by TerminalProgressBar subclasses to
            provide their own implementation who finally have to call
            the update_progress_bar() method to actually update the 
            progress bar.

            Args:
                new_value: New percentage of completion
            """
            self.update_progress_bar(new_value)


    class AudioDownloadProgressBar(TerminalProgressBar):
        """
        Inner class to display audio stream download progress bar
        """


        def update(self, 
                stream: any, 
                chunk: bytes, 
                bytes_remaining: int
            ) -> None:
            """
            Update progress bar

            Args:
                stream: Stream object
                chunk: Chunk size
                bytes_remaining: Remaining bytes to download
            """

            self.label = \
                f"{self.label_base} ({stream.filesize_mb} Mb)" \
                + f"{self.label_suffix}"
            
            bytes_remaining = \
                max(0, bytes_remaining)  # avoid negative values
            
            new_value = \
                ((stream.filesize - bytes_remaining) / stream.filesize) * 100

            self.update_progress_bar(new_value)


    class CoverArtDownloadProgressBar(TerminalProgressBar):
        """
        Inner class to display cover art download progress bar
        """
        

        def update(self, 
                block_number: int, 
                block_size: int, 
                total_size: int
            ) -> None:
            """
            Update progress bar

            Args:
                count: Number of blocks downloaded
                block_size: Size of each block
                total_size: Total size of the file
            """

            self.label = \
                f"{self.label_base} ({int(total_size / 1024)} Kb)" \
                    + f"{self.label_suffix}"
            
            new_value = \
                min([int(block_number * block_size * 100 / total_size), 100])

            self.update_progress_bar(new_value)


    class Mp3EncodingProgressBar(ProgressBarLogger):
        """
        Inner class extending ProgressBarLogger of "proglog" module 
        which is expected by an AudioFileClip stream instance to log 
        MP3 encoding progress
        """


        def __init__(self, 
                progress_callback: Callable | None = None, 
                label: str = "", 
                **kwargs
            ):
            """
            Construct a Mp3EncodingProgressBar

            Args:
                progress_callback: Callback function to update progress bar
                label: Label to display on the progress bar
                kwargs: Additional arguments for ProgressBarLogger
            """

            super().__init__(kwargs)

            self.progress_bar = SongModel.TerminalProgressBar(
                progress_callback=progress_callback, 
                label=label
            )


        def bars_callback(self, 
                bar: str, 
                attr: str, 
                new_progress_value: float, 
                old_progress_value: float | None = None
            ) -> None:
            """
            Implementation of ProgressBarLogger class abstract method
            to update progress bar

            Args:
                bar: Bar name
                attr: Attribute name
                new_progress_value: Current value
                old_progress_value: Previous value
            """

            if old_progress_value is not None:
                new_value = \
                    int((new_progress_value / self.bars[bar]["total"]) * 100)
                self.progress_bar.update_progress_bar(new_value)


    @staticmethod
    def sanitize_string(string: str) -> str: 
        """
        Sanitize a string (static method)

        Args:
            string: String to sanitize

        Returns:
            Sanitized string
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
            youtube_id: str,
            dest_folder_path: str, 
            shazam_match_threshold: int = 50, 
            verbose: bool = True, 
            use_default_verbosity: bool = True,
            pre_fetch_video_info: Callable | None = None, 
            post_fetch_video_info: Callable | None = None,
            pre_download_audio: Callable | None = None,
            on_download_audio: ProgressBarInterface | None = None,
            post_download_audio: Callable | None = None,
            pre_mp3_encode: Callable | None = None,
            on_mp3_encode: ProgressBarInterface | None = None,
            post_mp3_encode: Callable | None = None,
            pre_download_cover_art: Callable | None = None,
            on_download_cover_art: ProgressBarInterface | None = None,
            post_download_cover_art: Callable | None = None,
            pre_delete_cover_art: Callable | None = None,
            post_delete_cover_art: Callable | None = None,
            pre_shazam_song: Callable | None = None,
            post_shazam_song: Callable | None = None
        ) -> "SongModel":
        """
        Create a Song instance from YouTube (static method)

        Args:
            youtube_id: YouTube video ID
            dest_folder_path: Destination folder path for MP3 file
            shazam_match_threshold: Shazam match threshold (default: 50)
            verbose: Verbosity level (default: True)
            use_default_verbosity: Use default verbosity logging (default: True)
            pre_fetch_video_info: Callback before fetching video information
            post_fetch_video_info: Callback after fetching video information
            pre_download_audio: Callback before downloading audio
            on_download_audio: Progress logger to track audio download
            post_download_audio: Callback after downloading audio
            pre_mp3_encode: Callback before encoding to MP3
            on_mp3_encode: Progress logger to track MP3 encoding
            post_mp3_encode: Callback after encoding to MP3
            pre_download_cover_art: Callback before downloading cover art
            on_download_cover_art: Progress logger to track cover art download
            post_download_cover_art: Callback after downloading cover art
            pre_delete_cover_art: Callback before deleting cover art
            post_delete_cover_art: Callback after deleting cover art
            pre_shazam_song: Callback before shazaming song
            post_shazam_song: Callback after shazaming song

        Returns:
            Song instance

        Raises:
            SongModelError: If any error occurs during the creation process
        """
        
        # Disable verbosity logging
        if verbose != True:
            pre_fetch_video_info = None 
            post_fetch_video_info = None
            pre_download_audio = None 
            on_download_audio = None 
            post_download_audio = None
            pre_mp3_encode = None 
            on_mp3_encode = None 
            post_mp3_encode = None
            pre_download_cover_art = None 
            on_download_cover_art = None 
            post_download_cover_art = None 
            pre_delete_cover_art = None
            post_delete_cover_art = None
            pre_shazam_song = None 
            post_shazam_song = None

        # Activate default verbosity logging
        if verbose and use_default_verbosity:

            label_formatter = LabelFormatter(33)
            
            async def pre_fetch_video_info(youtube_id: str) -> None:
                print(
                    label_formatter.format("Fetching video information:") 
                    + f"Please, wait... ", 
                    end="", 
                    flush=True
                )

            async def post_fetch_video_info(
                    video_info: SimpleNamespace
                ) -> None:
                print("\x1b[K", end="\r")
                print(
                    label_formatter.format("Fetching video information:") 
                    + f"Ready to import video \"{video_info.youtube_id}\""
                )

            async def pre_download_audio(
                    video_info: SimpleNamespace, 
                    m4aPath: str
                ) -> None:
                pass
    
            on_download_audio = ProgressBarInterface(
                label="Streaming audio: ",
                callback=None
            )
    
            async def post_download_audio(
                    video_info: SimpleNamespace, 
                    m4aPath: str
                ) -> None:
                pass
    
            async def pre_mp3_encode(
                    video_info: SimpleNamespace, 
                    m4aPath: str, 
                    mp3_path: str
                ) -> None:
                pass
    
            on_mp3_encode = ProgressBarInterface(
                label="Encoding audio stream to MP3: ",
                callback=None
            )
    
            async def post_mp3_encode(
                    video_info: SimpleNamespace, 
                    m4aPath: str, 
                    mp3_path: str
                ) -> None:
                pass
    
            async def pre_download_cover_art(song):
                pass
    
            on_download_cover_art = ProgressBarInterface(
                label="Downloading cover art: ",
                callback=None
            )
    
            async def post_download_cover_art(song):
                pass

            async def pre_delete_cover_art(song):
                pass
    
            async def post_delete_cover_art(song):
                pass
    
            async def pre_shazam_song(song):
                print(label_formatter.format("Shazaming audio track:") 
                    + f"Please, wait... ", 
                    end="", 
                    flush=True
                )
    
            async def post_shazam_song(song):
                print("\x1b[K", end="\r")
                print(
                    label_formatter.format("Song recognition result:") 
                    + f"Artist: {Fore.LIGHTCYAN_EX}" 
                    + f"{song.shazam_artist}{Fore.RESET}, " 
                    + f"Title: {Fore.LIGHTCYAN_EX}" 
                    + f"{song.shazam_title}{Fore.RESET}, " 
                    + f"Match: {Fore.LIGHTCYAN_EX}" 
                    + f"{song.shazam_match_score}%{Fore.RESET}"
                )
 
        # Connect to YouTube video to get song information
        try:
            if pre_fetch_video_info is not None:
                await pre_fetch_video_info(youtube_id)

            video_url = f"https://youtube.com/watch?v={youtube_id}"
            video = YouTube(video_url, client="WEB")
            video_props = SimpleNamespace(
                youtube_id=video.video_id,
                artist=video.author,
                title=video.title,
                cover_art_url=video.thumbnail_url
            )

            if post_fetch_video_info is not None:
                await post_fetch_video_info(video_props)
        except Exception as exc:
            raise SongModelException(
                f"Failed to fetch information "
                f"for YouTube video \"{youtube_id}\""
            ) from exc
        
        # Download YouTube video audio stream
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_m4a_path = Path(temp_dir) / "temp.m4a"
            temp_mp3_path = Path(dest_folder_path) / "temp (JUNK).mp3"

            # Set up progress bar for audio download
            if on_download_audio is not None:
                audio_download_logger = SongModel.AudioDownloadProgressBar(
                    progress_callback=on_download_audio.callback, 
                    label=on_download_audio.label
                )
                video.register_on_progress_callback(
                    audio_download_logger.update
                )

            # Call pre_download_audio hook if provided
            if pre_download_audio is not None:
                try:
                    await pre_download_audio(video_props, temp_m4a_path)
                except Exception as exc:
                    raise SongModelException(
                        f"Hook \"pre_download_audio\" failed "
                        f"for YouTube video \"{youtube_id}\""
                    ) from exc

            # Download audio stream
            try:
                m4a_stream = video.streams.get_audio_only()

                if m4a_stream is None:
                    raise SongModelException(
                        f"Cannot get audio stream "
                        f"for YouTube video \"{youtube_id}\""
                    )
                
                # Use 1.12 MB chunk chunk for download (default: 9 MB)
                request.default_range_size = 1179648
                m4a_stream.download(
                    output_path=Path(temp_dir), 
                    filename="temp.m4a"
                )
            except Exception as exc:
                raise SongModelException(
                    f"Failed to stream audio track "
                    f"for YouTube video \"{youtube_id}\""
                ) from exc
            
            # Call post_download_audio hook if provided
            if post_download_audio is not None:
                try:
                    await post_download_audio(video_props, temp_m4a_path)
                except Exception as exc:
                    raise SongModelException(
                        f"Hook \"post_download_audio\" failed "
                        f"for YouTube video \"{youtube_id}\""
                    ) from exc
            
            # Set up progress bar for MP3 encoding
            mp3_encode_logger = None
            if on_mp3_encode is not None:
                mp3_encode_logger = SongModel.Mp3EncodingProgressBar(
                    progress_callback=on_mp3_encode.callback, 
                    label=on_mp3_encode.label
                )

            # Call pre_mp3_encode hook if provided
            if pre_mp3_encode is not None:
                try:
                    await pre_mp3_encode(
                        video_props, 
                        temp_m4a_path, 
                        temp_mp3_path
                    )
                except Exception as exc:
                    raise SongModelException(
                        f"Hook \"pre_mp3_encode\" failed "
                        f"for YouTube video \"{youtube_id}\""
                    ) from exc
                
            # Encode audio stream to MP3 file
            try:
                mp3_stream = AudioFileClip(str(temp_m4a_path))
                mp3_stream.write_audiofile(
                    str(temp_mp3_path), 
                    logger=mp3_encode_logger
                )
                mp3_stream.close()
            except Exception as exc:
                raise SongModelException(
                    f"Failed to encode audio stream to MP3 "
                    f"for YouTube video \"{youtube_id}\""
                ) from exc
            
            # Call post_mp3_encode hook if provided
            if post_mp3_encode is not None:
                try:
                    await post_mp3_encode(
                        video_props, 
                        temp_m4a_path, 
                        temp_mp3_path
                    )
                except Exception as exc:
                    raise SongModelException(
                        f"Hook \"post_mp3_encode\" failed "
                        f"for YouTube video \"{youtube_id}\""
                    ) from exc
            
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
                pre_download_cover_art=pre_download_cover_art, 
                on_download_cover_art=on_download_cover_art, 
                post_download_cover_art=post_download_cover_art, 
                pre_delete_cover_art=pre_delete_cover_art,
                post_delete_cover_art=post_delete_cover_art
            )
            
            # Submit song to Shazam API for recognition 
            # and update song state accordingly
            await song.shazam_song(
                shazam_match_threshold=shazam_match_threshold, 
                pre_shazam_song=pre_shazam_song, 
                post_shazam_song=post_shazam_song
            )
            
            # Get Shazam song covert art and save it in MP3 file
            await song.update_cover_art(
                pre_download_cover_art=pre_download_cover_art, 
                on_download_cover_art=on_download_cover_art, 
                post_download_cover_art=post_download_cover_art, 
                pre_delete_cover_art=pre_delete_cover_art,
                post_delete_cover_art=post_delete_cover_art
            )
            
            # Rename MP3 file according to gathered song informaton
            # If Shazam recogntion failed or is too bad, mark song as junk
            song.fix_filename(
                mark_as_junk= \
                    (song.shazam_match_score or 0) < shazam_match_threshold
            )

            # Return created song object
            return song
    

    def __init__(self, 
            mp3_path: str, 
            youtube_id: str | None = None, 
            artist: str | None = None, 
            title: str | None = None, 
            cover_art_url: str | None = None, 
            shazam_match_score: float | None = None
        ) -> None:
        """
        Construct a song model instance from a MP3 file

        Args:
            mp3_path: Path to the MP3 file
            youtube_id: YouTube video ID
            artist: Artist name
            title: Song title
            cover_art_url: Cover art URL
            shazam_match_score: Shazam match score

        Raises:
            SongModelError: If YouTube ID is missing in MP3 file
        """
        
        # Check if song object is already initialized
        self.is_already_initialized = getattr(
            self, 
            "is_already_initialized", 
            False
        )
        
        # Set song object attributes that depends on MP3 file only 
        self.path = Path(mp3_path)
        self.mp3 = mutagen.mp3.MP3(self.path)
        self.audio_length = self.mp3.info.length
        self.duration = "{:0>8}".format(
            str(datetime.timedelta(seconds=round(self.audio_length)))
        )
        self.filename = self.path.name
        self.has_junk_filename = re.match(
            r"^.*\s\(JUNK\)\.mp3$", 
            str(self.filename)
        ) is not None
        self.label_from_filename = \
            self.path.name[:(-4, -11)[self.has_junk_filename]]
        self.playlist = self.path.parent.name

        # Initialize song object attributes that will be computed later
        self.has_cover_art = None
        self.should_be_tagged = False
        self.should_be_renamed = False
        self.should_be_shazamed = False

        # YouTube ID is required.
        # Try to get it from constructor parameters first, 
        # then from song state, 
        # then from ID3 tags, 
        # then from MP3 filename.
        # If not found, raise an error.
        try:
            youtube_id_tag = \
                self.mp3.tags["TXXX:YouTube ID"].text[0]
        except:
            youtube_id_tag = None

        self.youtube_id = youtube_id \
            or getattr(self, "youtube_id", None) \
            or youtube_id_tag

        if not self.youtube_id:
            match = re.match(
                r"^.*\[(?P<youtube_id>[^\]]+)\]$", 
                str(self.label_from_filename)
            )

            if match:
                self.youtube_id = match.group("youtube_id")
            else:
                raise SongModelException(
                    f"Missing YouTube ID in MP3 filename \"{str(self.path)}\""
                )

        # Extract song name from filename
        self.song_name_from_filename = self.label_from_filename
        match = re.match(
            r"^(?P<song_name>.*)\[(?P<youtube_id>[^\]]+)\]$", 
            str(self.label_from_filename)
        )

        if match and match.group("song_name") \
            and match.group("youtube_id") == self.youtube_id:

            self.song_name_from_filename = (match.group("song_name")).strip()

        # Retrieve and set song artist and title.
        # Try to get them from constructor parameters first or from song state.
        # At initialization time, also try to get them from ID3 tags, 
        # then from MP3 filename.
        self.artist = artist or getattr(self, "artist", None)
        self.title = title or getattr(self, "title", None)

        if not self.is_already_initialized \
            and (not self.artist or not self.title):

            try:
                self.artist = self.artist or self.mp3.tags["TPE1"].text[0]
            except:
                pass

            try:
                self.title = self.title or self.mp3.tags["TIT2"].text[0]
            except:
                pass

            match = re.match(
                r"^(?P<artist>.*)\s-\s(?P<title>.*)\s\[[^\]]+\]$", 
                str(self.label_from_filename)
            )

            if match:
                self.artist = self.artist or match.group("artist")
                self.title = self.title or match.group("title")
            else:
                match = re.match(
                    r"^(?P<title>.*)\s\[[^\]]+\]$", 
                    str(self.label_from_filename)
                )

                if match:
                    self.title = self.title or match.group("title")

        if self.artist:
            self.artist = re.sub(r"\s+", " ", self.artist.strip())

        if self.title:
            self.title = re.sub(r"\s+", " ", self.title.strip())

        # Retrieve and set covert art URL. 
        # Try to get it from constructor parameters first or from song state.
        # At initialization time, also try to get it from ID3 tags.
        self.cover_art_url = \
            cover_art_url or getattr(self, "cover_art_url", None)

        if not self.is_already_initialized and not self.cover_art_url:
            try:
                self.cover_art_url = \
                    self.mp3.tags["TXXX:Cover art URL"].text[0]
            except:
                pass
            
        # Retrieve and set Shazam artist.
        # Try to get it from constructor parameters first or from song state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazam_artist = getattr(self, "shazam_artist", None)

        if not self.is_already_initialized and not self.shazam_artist:
            try:
                self.shazam_artist = \
                    self.mp3.tags["TXXX:Shazam artist"].text[0]
            except:
                pass
            
        # Retrieve and set Shazam title.
        # Try to get it from constructor parameters first or from song state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazam_title = getattr(self, "shazam_title", None)

        if not self.is_already_initialized and not self.shazam_title:
            try:
                self.shazam_title = \
                    self.mp3.tags["TXXX:Shazam title"].text[0]
            except:
                pass
            
        # Retrieve and set Shazam cover art URL.
        # Try to get it from constructor parameters first or from song state.
        # At initialization time, also try to get it from ID3 tags.
        self.shazam_cover_art_url = getattr(self, "shazam_cover_art_url", None)

        if not self.is_already_initialized and not self.shazam_cover_art_url:
            try:
                self.shazam_cover_art_url = \
                    self.mp3.tags["TXXX:Shazam cover art URL"].text[0]
            except:
                pass

        # Set Shazam match level.
        # Try to get it from constructor parameters first or from song state.
        # At initialization time, also try to get it from ID3 tags.
        if shazam_match_score == 0:
            self.shazam_match_score = 0
        else:
            self.shazam_match_score = getattr(self, "shazam_match_score", None)

            if not self.is_already_initialized \
                and self.shazam_match_score is None:

                try:
                    self.shazam_match_score = \
                        int(self.mp3.tags["TXXX:Shazam match level"].text[0])
                except:
                    pass
            
        # Update MP3 file ID3 tags if required
        # e.g. if song state is modified after initialization (deliberate 
        # recall of constructor) or if song MP3 file was just created and 
        # not yet tagged
        if self.is_already_initialized or youtube_id_tag is None:
            self.update_id3_tags()

        # Compute expected filenames
        artist_label = SongModel.sanitize_string(self.artist).upper()
        title_label = SongModel.sanitize_string(self.title)
        title_label = title_label[:1].upper() + title_label[1:]

        self.expected_filename = \
            artist_label + ("", " - ")[bool(self.artist and self.title)] \
            + title_label + ("", " ")[bool(self.artist or self.title)] \
            + "[" + self.youtube_id + "].mp3"
        
        self.expected_junk_filename = \
            artist_label + ("", " - ")[bool(self.artist and self.title)] \
            + title_label + ("", " ")[bool(self.artist or self.title)] \
            + "[" + self.youtube_id + "] (JUNK).mp3"

        # Check if MP3 file should be tagged
        if not self.artist or not self.title:
            self.should_be_tagged = True

        # Check if MP3 file should be shazamed
        if self.shazam_match_score is None:
            self.should_be_shazamed = True

        # Check if MP3 file should be renamed
        if (not self.has_junk_filename \
                and self.filename != self.expected_filename) \
            or (self.has_junk_filename \
                and self.filename != self.expected_junk_filename):

            self.should_be_renamed = True

        # Check if MP3 file has a cover art
        try:
            self.has_cover_art = \
                self.mp3.tags["APIC:Cover art"].type == 3
        except:
            self.has_cover_art = False

        # Mark song object as initialized
        self.is_already_initialized = True


    def update_id3_tags(self) -> None:
        """
        Update ID3 tags of the Song MP3 file

        NOTE: MP3 are saved with ID3v2.3 tags only, without ID3v1
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


    async def update_cover_art(self,
            pre_download_cover_art: Callable | None = None,
            on_download_cover_art: ProgressBarInterface | None = None,
            post_download_cover_art: Callable | None = None,
            pre_delete_cover_art: Callable | None = None,
            post_delete_cover_art: Callable | None = None
        ) -> None:
        """
        Update or delete covert art of the Song MP3 file
        Raise an error if covert art download fails

        Args:
            pre_download_cover_art: Callback before downloading cover art
            on_download_cover_art: Progress bar for cover art download
            post_download_cover_art: Callback after downloading cover art
            pre_delete_cover_art: Callback before deleting cover art
            post_delete_cover_art: Callback after deleting cover art

        Raises:
            SongModelError: If cover art download fails
        """

        # Check if cover art must be updated or deleted
        try:
            self.has_cover_art = \
                self.mp3.tags["APIC:Cover art"].type == 3

            if not self.cover_art_url:

                if pre_delete_cover_art is not None:
                    await pre_delete_cover_art(self)
            
                self.mp3.tags.delall("APIC")
                self.mp3.tags.delall("TXXX:Cover art URL")
                self.mp3.save(v1=0, v2_version=3)
                self.has_cover_art = False

                if post_delete_cover_art is not None:
                    await post_delete_cover_art(self)

                return
        except:
            self.has_cover_art = False

        should_cover_art_be_updated = False

        if self.cover_art_url:
            should_cover_art_be_updated = True

            if self.has_cover_art:
                try:
                    stored_cover_art_url = \
                        self.mp3.tags["TXXX:Cover art URL"].text[0]

                    if self.cover_art_url == stored_cover_art_url:
                        should_cover_art_be_updated = False
                except:
                    should_cover_art_be_updated = True

        # Update or remove cover art
        if should_cover_art_be_updated :

            # Set up progress bar for cover art download
            progress_bar_callback = None
            if on_download_cover_art is not None:
                progress_bar_logger = SongModel.CoverArtDownloadProgressBar(
                    progress_callback=on_download_cover_art.callback, 
                    label=on_download_cover_art.label
                )
                progress_bar_callback = progress_bar_logger.update

            # Call pre_download_cover_art hook if provided
            if pre_download_cover_art is not None:
                try:
                    await pre_download_cover_art(self)
                except Exception as exc:
                    raise SongModelException(
                        f"Hook \"pre_download_cover_art\" failed"
                    ) from exc
            
            # Download cover art
            with tempfile.TemporaryDirectory() as temporary_directory_pathname:
                temp_file = Path(temporary_directory_pathname) / "temp.jpg"

                try:
                    urllib.request.urlretrieve(
                        self.cover_art_url, 
                        temp_file, 
                        progress_bar_callback
                    )
                except Exception as exc:
                    raise SongModelException(
                        f"Failed to download cover art"
                    ) from exc
                
                try:
                    with open(temp_file, "rb") as f:
                        self.mp3.tags.delall("APIC")
                        self.mp3.tags.add(APIC(
                            encoding=3,  # 3 is for utf-8
                            desc=u"Cover art",
                            mime="image/jpg",  # image/jpeg or image/png
                            type=3,  # 3 is for the cover image
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
                except Exception as exc:
                    raise SongModelException(
                        f"Failed to add cover art to MP3 file"
                    ) from exc
                
                self.mp3.save(v1=0, v2_version=3)

            # Update covert art presence flag
            self.has_cover_art = True

            # Call post_download_cover_art hook if provided
            if post_download_cover_art is not None:
                try:
                    await post_download_cover_art(self)
                except Exception as exc:
                    raise SongModelException(
                        f"Hook \"post_download_cover_art\" failed"
                    ) from exc
                await post_download_cover_art(self)


    async def shazam_song(self,
            shazam_match_threshold: int = 50,
            pre_shazam_song: Callable | None = None,
            post_shazam_song: Callable | None = None
        ) -> None:
        """
        Retrieve Song artist, title and cover art url 
        from Shazam then compute matching rate

        Args:
            shazam_match_threshold: Shazam match threshold (default: 50)
            pre_shazam_song: Callback before shazaming song
            post_shazam_song: Callback after shazaming song

        Raises:
            SongModelError: If Shazam API call fails
        """
        
        # Call pre_shazam_song hook if provided
        if pre_shazam_song is not None:
            try:
                await pre_shazam_song(self)
            except Exception as exc:
                raise SongModelException(
                    f"Hook \"pre_shazam_song\" failed"
                ) from exc

        # Submit song to Shazam API for recognition.
        try:
            # Wait for 15s min since last request to Shazam API.
            diff_time = time.time() - SongModel.last_shazam_request_time
            if diff_time < 15:
                time.sleep(15 - diff_time)

            # Call Shazam API to recognize song and get metadata
            shazam_metadata = \
                await self.shazam_client.recognize_song(str(self.path))
            SongModel.last_shazam_request_time = time.time()
        except:
            # If Shazam API call fails, wait for 35s before retry
            diff_time = time.time() - SongModel.last_shazam_request_time
            if diff_time < 35:
                time.sleep(35 - diff_time)

            # Retry Shazam API call
            # If it fails again, raise an error
            try:
                shazam_metadata = \
                    await self.shazam_client.recognize_song(str(self.path))
                SongModel.last_shazam_request_time = time.time()
            except Exception as exc:
                raise SongModelException(
                    f"Shazam API seems out of service"
                ) from exc
            
        # Update song state and related MP3 file according to Shazam metadata 
        # and compare returned artist and title with current artist and title 
        # to compute matching rate using "fuzzy" string matching based on 
        # levenshtein distance algorithm.
        if "track" in shazam_metadata:
            try:
                title = \
                    shazam_metadata["track"]["title"][:1].upper() \
                    + shazam_metadata["track"]["title"][1:]
                
                artist = \
                    shazam_metadata["track"]["subtitle"][:1].upper() \
                    + shazam_metadata["track"]["subtitle"][1:]
                
                artist_match_score = \
                    fuzz.partial_token_sort_ratio(self.artist, artist, True)

                title_match_score = \
                    fuzz.partial_token_sort_ratio(self.title, title, True)

                # If artist match score is too low, this probably means that 
                # the song's title grabbed from YouTube video contains the 
                # artist name. In this case, we need to check if the title
                # match score is good enough to consider the song as  
                # recognized by Shazam.
                if artist_match_score < 2 * shazam_match_threshold / 3 \
                        and title_match_score >= shazam_match_threshold:
                    
                    match_score = \
                        fuzz.partial_token_sort_ratio(
                            title, 
                            f"{artist} - {title}", 
                            True
                        )
                else:
                    match_score = \
                        int((artist_match_score + title_match_score * 2) / 3)

                # If match score is good enough, update and save all 
                # related MP3 file metadata with artist, title and 
                # cover art URL from Shazam metadata.
                # Otherwise, only save Shazam-specific metadata.
                if match_score >= shazam_match_threshold:
                    try:
                        cover_art_url = \
                            shazam_metadata["track"]["images"]["coverart"]
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
                        # If cover art URL is not available, 
                        # don't change cover art settings.
                        self.update_state(
                            artist=artist,
                            title=title,
                            shazam_artist=artist,
                            shazam_title=title,
                            shazam_match_score=match_score
                        )
                else:
                    # If match score is not good enough, only save 
                    # Shazam-specific metadata excepted cover art URL.
                    self.update_state(
                        shazam_artist=artist,
                        shazam_title=title,
                        shazam_match_score=match_score
                    )
            except Exception as exc:
                raise SongModelException(
                    f"Failed to update song from Shazam metadata"
                ) from exc
        else:
            self.update_state(shazam_match_score=0)

        # Call post_shazam_song hook if provided
        if post_shazam_song is not None:
            try:
                await post_shazam_song(self)
            except Exception as exc:
                raise SongModelException(
                    f"Hook \"post_shazam_song\" failed"
                ) from exc


    def fix_filename(self, mark_as_junk: bool | None = None) -> None:
        """
        Fix song MP3 filename (rename the MP3 file)

        Args:
            mark_as_junk: Boolean indicating if the file should be marked 
                as junk (default: None, which means use the current state)
        """

        if not mark_as_junk == True and not mark_as_junk == False:
            mark_as_junk = self.has_junk_filename

        if self.should_be_tagged:
            appropriate_filename = \
                f"{self.song_name_from_filename} [{self.youtube_id}] (JUNK).mp3"
        else:
            appropriate_filename = \
                self.expected_junk_filename if mark_as_junk \
                else self.expected_filename

        try:
            self.path = \
                self.path.rename(self.path.parent / appropriate_filename)
        except Exception as exc:
            raise SongModelException(
                f"Failed to rename song MP3 file"
            ) from exc
        
        self.update_state()


    def update_state(self,
            artist: str | None | bool = False,
            title: str | None | bool = False,
            cover_art_url: str | None | bool = False,
            shazam_artist: str | None | bool = False,
            shazam_title: str | None | bool = False,
            shazam_cover_art_url: str | None | bool = False,
            shazam_match_score: float | None | int = -1
        ) -> None:
        """
        Update song state and related MP3 file ID3 tags

        If a parameter is False or -1, keep its current state

        Args:
            artist: Artist name (default: False)
            title: Song title (default: False)
            cover_art_url: Cover art URL (default: False)
            shazam_artist: Shazam artist name (default: False)
            shazam_title: Shazam title (default: False)
            shazam_cover_art_url: Shazam cover art URL (default: False)
            shazam_match_score: Shazam match score (default: -1)
        """

        # Update song state according to provided parameters
        # If parameter is False or -1, keep current state
        self.artist = (self.artist, artist)[artist != False]

        self.title = (self.title, title)[title != False]

        self.cover_art_url = \
            (self.cover_art_url, cover_art_url)[
                cover_art_url != False
            ]
        
        self.shazam_artist = \
            (self.shazam_artist, shazam_artist)[
                shazam_artist != False
            ]
        
        self.shazam_title = \
            (self.shazam_title, shazam_title)[
                shazam_title != False
            ]
        
        self.shazam_cover_art_url = \
            (self.shazam_cover_art_url, shazam_cover_art_url)[
                shazam_cover_art_url != False
            ]
        
        self.shazam_match_score = \
            (self.shazam_match_score, shazam_match_score)[
                shazam_match_score != -1
            ]

        # Reinitialize song object according to new state
        self.__init__(self.path, self.youtube_id)


    def reset_state(self) -> None:
        """
        Reset Song state and remove covert art and ID3 tags 
        from related MP3 file (excepted tag holding YouTube ID)
        """

        # Clear song state
        self.artist = None 
        self.title = None 
        self.cover_art_url = None  
        self.shazam_artist = None
        self.shazam_title = None
        self.shazam_cover_art_url = None
        self.shazam_match_score = None

        # Reinitialize song object according to cleared state
        self.__init__(self.path, self.youtube_id)
        