#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides functionality to download YouTube playlist videos 
as MP3 files, reaname them and update their metadata using Shazam, or 
mark them as "junk" if no match found.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional, Callable

# Third party packages
from colorama import Fore, Back, Style, init
from pytubefix import Playlist, YouTube

# pypl2mp3 libs
from pypl2mp3.libs.exceptions import AppBaseException
from pypl2mp3.libs.logger import logger
from pypl2mp3.libs.repository import get_repository_playlist
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import (
    extract_youtube_id_from_filename,
    extract_youtube_id_from_url,
    calculate_fuzzy_match_score,
    LabelFormatter,
    ProgressCounter
)

# Automatically clear style on each print
init(autoreset=True)

class ImportPlaylistException(AppBaseException):
    """
    Custom exception for playlist import errors.
    """
    pass


@dataclass
class SongReport:
    """
    Data structure for song processing report.
    """

    song_name: str
    youtube_id: str
    filename: Optional[str] = None
    detail: Optional[str] = None
    reason: Optional[str] = None
    issue: Optional[str] = None

    def __getitem__(self, item):
        """
        Implement dictionary-like access to report attributes.
        By the way, this make it subscriptable to be used as a list item.

        Args:
            item: Key to access in the report

        Returns:
            The value associated with the key
        """

        return getattr(self, item)


class ImportReport:
    """Container for playlist import statistics and results."""
    
    def __init__(self):
        """
        Initialize the import report with empty lists for each category.
        """

        self.shazamed_songs: List[SongReport] = []
        self.junk_songs: List[SongReport] = []
        self.skipped_songs: List[SongReport] = []
        self.failed_imports: List[SongReport] = []


    def print_import_report(self, total_songs: int, junk_songs: int) -> None:
        """
        Print detailed import statistics and results.
        
        Args:
            report: Import statistics and results
            total_songs: Total number of songs in playlist
            junk_songs: Number of existing junk songs
        """

        print(f"\n\n{Back.LIGHTCYAN_EX}{Fore.WHITE} Playlist import summary ")

        print(f"\n{Fore.LIGHTYELLOW_EX}"
            + f"⇨ New Shazam-ed songs added to playlist .... " 
            + f"{len(self.shazamed_songs)}")
        
        print(f"{Fore.MAGENTA}"
            + f"⇨ New junk songs added to playlist ......... " 
            + f"{len(self.junk_songs)}")
        
        if len(self.skipped_songs):
            print(f"{Fore.LIGHTYELLOW_EX}"
                + f"⇨ Songs skipped ............................ " 
                + f"{len(self.skipped_songs)}")
            
        print(f"{Fore.RED}"
            + f"⇨ Song import failures ..................... " 
            + f"{len(self.failed_imports)}")

        shazamed_total = \
            total_songs - junk_songs + len(self.shazamed_songs)
        
        junk_total = \
            junk_songs + len(self.junk_songs)
        
        playlist_total = \
            total_songs + len(self.shazamed_songs) + len(self.junk_songs)
        
        print(f"\n{Style.BRIGHT}"
            + f"⇨ Number of Shazam-ed songs in playlist .... " 
            + f"{shazamed_total}")
        
        print(f"{Style.BRIGHT}"
            + f"⇨ Number of junk songs in playlist ......... " 
            + f"{junk_total}")
        
        print(f"\n{Fore.CYAN}"
            + f"⇨ Total number of songs in playlist ........ " 
            + f"{playlist_total}")

        # Print detailed reports if there are results
        if self.shazamed_songs:
            self._print_shazamed_songs()
        if self.junk_songs:
            self._print_junk_songs()
        if self.skipped_songs:
            self._print_skipped_songs()
        if self.failed_imports:
            self._print_failed_imports()


    def _print_shazamed_songs(self) -> None:
        """
        Print report of successfully Shazamed songs.
        """

        print(f"\n\n{Back.YELLOW}{Fore.WHITE} New Shazam-ed song report ")
        for song in self.shazamed_songs:
            print(f"\n- YouTube ID: {Fore.BLUE}{song.youtube_id}")
            print(f"  Song name:  {Fore.CYAN}{song.song_name}")
            print(f"  Detail:     {Fore.LIGHTGREEN_EX}{song.detail}")
            print(f"  Filename:   {Fore.LIGHTYELLOW_EX}{song.filename}")


    def _print_junk_songs(self) -> None:
        """
        Print report of songs classified as junk.
        """

        print(f"\n\n{Back.MAGENTA}{Fore.WHITE} New junk song report ")
        for song in self.junk_songs:
            print(f"\n- YouTube ID: {Fore.BLUE}{song.youtube_id}")
            print(f"  Song name:  {Fore.CYAN}{song.song_name}")
            print(f"  Reason:     {Fore.LIGHTGREEN_EX}{song.reason}")
            print(f"  Filename:   {Fore.MAGENTA}{song.filename}")


    def _print_skipped_songs(self) -> None:
        """
        Print report of skipped songs.
        """

        print(f"\n\n{Back.LIGHTYELLOW_EX}{Fore.WHITE} Skipped song report ")
        for song in self.skipped_songs:
            print(f"\n- YouTube ID: {Fore.BLUE}{song.youtube_id}")
            print(f"  Song name:  {Fore.CYAN}{song.song_name}")


    def _print_failed_imports(self) -> None:
        """
        Print report of failed import attempts.
        """

        print(f"\n\n{Back.RED}{Fore.WHITE} Import failure report ")
        for song in self.failed_imports:
            print(f"\n- YouTube ID: {Fore.BLUE}{song.youtube_id}")
            print(f"  Song name:  {Fore.CYAN}{song.song_name}")
            print(f"  Issue:      {Fore.RED}{song.issue}")


def _create_progress_callback(label_formatter: LabelFormatter) -> Callable:
    """
    Creates a progress bar callback function.
    
    Args:
        label_formatter: Formatter for progress labels
        
    Returns:
        Callback function for progress updates
    """

    def progress_callback(percentage: float, label: str = "") -> None:
        """
        Callback function to update the progress bar.
        """

        label = label_formatter.format(label)
        progress_filled = "■" * int(percentage / 2)
        progress_empty = "□" * (50 - int(percentage / 2))
        progress_bar = f"{Fore.LIGHTRED_EX}{progress_filled}{Fore.RESET}" \
                     + f"{Fore.LIGHTRED_EX}{progress_empty}{Fore.RESET}"
        
        print(("", "\x1b[K")[percentage < 100], end="\r")
        print(
            f"{label}{progress_bar} {Style.DIM}{int(percentage)}%".strip() + " ", 
            end=("\n", "")[percentage < 100], 
            flush=True
        )
    
    return progress_callback


async def _import_song(
    video: YouTube,
    playlist_path: Path,
    shazam_threshold: float,
    label_formatter: LabelFormatter
) -> Optional[SongModel]:
    """
    Process a single video: download, convert to MP3, and Shazam verify.
    
    Args:
        video: YouTube video object
        playlist_path: Path to save the MP3
        shazam_threshold: Minimum Shazam match score
        label_formatter: Formatter for progress labels
        
    Returns:
        SongModel: Created song object
        None: If user chooses not to import the song
        
    Raises:
        ImportPlaylistError: If song creation fails
    """

    progress_callback = _create_progress_callback(label_formatter)
    
    async def before_connect(youtube_id):
        label = label_formatter.format("Connecting to YouTube API:")
        print(f"{label}Please, wait... ", end="", flush=True)
        
    async def after_connect(props):
        label = label_formatter.format("Connecting to YouTube API:")
        print("\x1b[K", end="\r")
        print(f"{label}Ready to import video")

    async def before_shazam(song):
        label = label_formatter.format("Shazam-ing audio track:")
        print(f"{label}Please, wait... ", end="", flush=True)
        
    async def after_shazam(song):
        label = label_formatter.format("Shazam-ing audio track:")
        print("\x1b[K", end="\r")
        print(
            f"{label}"
            + f"Artist: {Fore.LIGHTCYAN_EX}{song.shazam_artist}{Fore.RESET}, "
            + f"Title: {Fore.LIGHTCYAN_EX}{song.shazam_title}{Fore.RESET}, "
            + f"Match: {Fore.LIGHTCYAN_EX}{song.shazam_match_score}%"
        )

    song = await SongModel.create_from_youtube(
        video.video_id,
        playlist_path,
        shazam_threshold,
        verbose=True,
        use_default_verbosity=False,
        before_connect_to_video=before_connect,
        after_connect_to_video=after_connect,
        progress_logger_for_download_audio=SimpleNamespace(
            label="Streaming audio:",
            callback=progress_callback
        ),
        progress_logger_for_encode_to_mp3=SimpleNamespace(
            label="Encoding audio stream to MP3:",
            callback=progress_callback
        ),
        progress_logger_for_download_cover_art=SimpleNamespace(
            label="Downloading cover art:",
            callback=progress_callback
        ),
        before_shazam_song=before_shazam,
        after_shazam_song=after_shazam
    )

    return song


async def import_playlist(args) -> None:
    """
    Import or sync a YouTube playlist to local MP3 files.
    
    Args:
        args: Command line arguments containing:
            - repo: Repository path
            - playlist: Playlist name/ID
            - keywords: Filter keywords
            - match: Minimum match threshold for keywords
            - thresh: Minimum Shazam match threshold
            - prompt: Whether to prompt for confirmation
            
    Raises:
        Various exceptions from YouTube API and file operations
    """

    repository_path = Path(args.repo)
    selected_playlist = get_repository_playlist(
        repository_path, 
        args.playlist, 
        must_exist=False
    )
    
    logger.info(f"Retrieving data for playlist \"{selected_playlist.id}\"")
    
    print(
        f"\n{Fore.LIGHTGREEN_EX}Retrieving YouTube playlist from:" 
        + f"\n{Fore.LIGHTYELLOW_EX}{selected_playlist.url}"
        + f"\n{Fore.LIGHTGREEN_EX}Please, wait...\n"
    )
    
    # Retrieve YouTube playlist data and handle potential errors
    try:
        plst = Playlist(selected_playlist.url, "WEB")
    except Exception as exc:
        raise ImportPlaylistException(
            f"Failed to retrieve playlist \"{selected_playlist.id}\" from YouTube"
        ) from exc

    # Check if playlist data is empty
    if not plst or not plst.videos:
        raise ImportPlaylistException(
            f"Playlist \"{selected_playlist.id}\" is empty or inaccessible."
        )
    
    # Log playlist information
    logger.info(
        f"Found {len(plst.videos)}/{plst.length} accessible videos "
        + f"in playlist \"{plst.title}\" owned by \"{plst.owner}\""
    )
    
    # Display playlist information
    print(
        f"{Back.YELLOW}{Style.BRIGHT} Found {len(plst.videos)}/{plst.length} " 
        + f"accessible videos in playlist \"{plst.title}\" " 
        + f"owned by \"{plst.owner}\" "
    )

    # Create playlist folder if it doesn't exist
    playlist_folder = f"{plst.owner} - {plst.title} [{selected_playlist.id}]"
    playlist_path = repository_path / playlist_folder
    try:
        playlist_path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise ImportPlaylistException(
            f"Failed to create playlist folder: {playlist_path}"
        ) from exc

    # Initialize tracking sets
    existing_songs = frozenset(
        map(extract_youtube_id_from_filename, playlist_path.glob("*.mp3"))
    )
    junk_songs = frozenset(
        map(extract_youtube_id_from_filename, playlist_path.glob("* (JUNK).mp3"))
    )
    video_ids = frozenset(
        map(extract_youtube_id_from_url, plst.video_urls)
    )
    
    # Calculate number of new songs to import
    new_song_count = len(video_ids - existing_songs)

    logger.info(
        f"Discovered {new_song_count} new videos to import from playlist " \
        + f"\"{plst.title} [{plst.playlist_id}]\""
    )
    
    # If no song to import, return
    if new_song_count == 0:
        print(f"\n{Fore.LIGHTYELLOW_EX}No new videos to import.")
        return
    
    print(
        f"\n{Fore.LIGHTYELLOW_EX}Number of new videos to import:  {Fore.RESET}"
        + f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{new_song_count}"
    )
    
    # Display import filter criteria if provided
    if args.keywords:
        print(
            f"\n{Fore.WHITE}{Style.DIM} ⇨ Import filter:  "
            + f"{Fore.LIGHTBLUE_EX}{args.keywords}  "
            + f"{Style.DIM}(match threshold: {args.match}%)"
        )

    # Initialize progress tracking
    progress_counter = ProgressCounter(new_song_count)
    label_formatter = LabelFormatter(28 + progress_counter.pad_size)
    padding_diff = label_formatter.tab_size - progress_counter.pad_size
    report = ImportReport()
    
    # Process each video
    for song_index, video_id in enumerate(video_ids - existing_songs, 1):

        # Skip already imported songs
        if video_id in existing_songs:
            continue

        # Get video details
        try:
            video_url = f"https://youtube.com/watch?v={video_id}"
            video = YouTube(video_url, client="WEB")

        except Exception as exc:
            # Log YouTube API error, append error to report and skip this video
            logger.error(
                exc, 
                f"Failed to retrieve YouTube details for video \"{video_id}\""
            )
            report.failed_imports.append(SongReport(
                youtube_id=video_id,
                song_name=f"Video ID: {video_id}",
                issue=f"Failed to retrieve YouTube details ({str(exc)})"
            ))
            continue

        # Check if video matches import filter criteria
        counter = progress_counter.format(song_index)
        song_name = f"{video.author} {video.title}"
        song_ref = f"{song_name} [{video.video_id}]"
        match_score = calculate_fuzzy_match_score(video.author, video.title, args.keywords)

        if match_score < args.match:

            # Video does not match filter criteria
            logger.info(
                f"Filter match ({match_score:.1f}%) too low " 
                + f"to import song \"{song_ref}\"" 
            )
            if song_index == 1:
                line_break = "\n"  # Handle line break particular case
            print(
                f"{line_break}{counter}{Fore.WHITE}" 
                + f" ⇨ Match too low ({match_score:.1f}%)".ljust(padding_diff, " ")
                + f" {Fore.RESET}{Fore.GREEN}{song_name}{Fore.RESET}" 
                + f" {Fore.BLUE}[{video.video_id}]"
            )

            # Disable line break for consecutive 
            # skipped song imports printed to the console
            line_break = "" 

            # Skip to next video
            continue

        # Restaure line break to seperate 
        # succesfull song imports in the console
        line_break = "\n"

        # Display new video to import
        print(
            f"\n{counter}{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}" 
            + " ⇨ New video to import!".ljust(padding_diff, " ") 
            + f" {Fore.LIGHTGREEN_EX}{song_name}{Fore.RESET}" 
            + f" {Fore.BLUE}[{video.video_id}]"
        )
        
        # Prompt user to add new song to playlist
        if args.prompt: 

            try:
                response = input(
                    f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}Do you want " 
                    + f"to import new song in playlist{Style.RESET_ALL} " 
                    + f"({Fore.CYAN}yes{Fore.RESET}/" 
                    + f"{Fore.CYAN}no{Fore.RESET}/" 
                    + f"{Fore.CYAN}abort{Fore.RESET}) ? ")
                
                if response != "yes" and response != "abort":
                    # Skip song if user chooses not to import
                    logger.info(
                        f"User skipped importing song \"{song_ref}\""
                    )
                    report.skipped_songs.append(SongReport(
                        youtube_id = video.video_id, 
                        song_name = song_name,  
                    ))
                    continue

                elif response == "abort":
                    # Raise KeyboardInterrupt to trigger abort
                    raise KeyboardInterrupt()
                
            except KeyboardInterrupt:
                # Print import report and let interrupt bubble
                report.print_import_report(len(existing_songs), len(junk_songs))
                raise

        # Import song from YouTube
        try:
            # Log song import attempt
            logger.info(f"Start importing song \"{song_ref}\"")

            # Perform import
            song = await _import_song(
                video, 
                playlist_path, 
                args.thresh, label_formatter
            )

            if not song.has_junk_filename:
                # Song import successful
                logger.info(f"Song successfully saved to \"{song.filename}\"")
                print(
                    label_formatter.format('MP3 file saved successfully:') 
                    + f'{Fore.LIGHTYELLOW_EX + Style.BRIGHT}{song.filename}'
                )
                report.shazamed_songs.append(SongReport(
                    youtube_id = video.video_id, 
                    song_name = f"{video.author} - {video.title}", 
                    detail = f'Shazam match score OK ({song.shazam_match_score}%)',
                    filename = song.filename
                ))
            else:
                # Song imported but classified as junk (Shazam match too low)
                logger.info(
                    f"Shazam match ({song.shazam_match_score}%) too low; " 
                    + f"song saved as junk to \"{song.filename}\""
                )
                print(
                    label_formatter.format('MP3 file saved as junk song:') 
                    + f'{Fore.MAGENTA}{song.filename}'
                )
                report.junk_songs.append(SongReport(
                    youtube_id = video.video_id, 
                    song_name = f"{video.author} - {video.title}",  
                    reason = f'Shazam match score too low ({song.shazam_match_score}%)',
                    filename = song.filename
                ))

        except KeyboardInterrupt:
            # Print import report and let interrupt bubble
            report.print_import_report(len(existing_songs), len(junk_songs))
            raise

        except Exception as exc:
            # Log import error, append error to report and skip this video
            logger.error(exc, f"Failed to import song \"{song_ref}\"")
            report.failed_imports.append(SongReport(
                youtube_id=video_id,
                song_name=f"{video.author} - {video.title}",
                issue=f"Failed to import video to MP3 ({str(exc)})"
            ))
            continue

    # Print final import report
    report.print_import_report(len(existing_songs), len(junk_songs))