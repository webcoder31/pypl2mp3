#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module handles the tagging of "junk" songs - those 
with incomplete or incorrect metadata. It attempts to fix 
them using YouTube and Shazam data.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from types import SimpleNamespace

# Third party packages
from colorama import Fore, Back, Style, init
from pytubefix import YouTube

# pypl2mp3 libs
from pypl2mp3.libs.exceptions import AppBaseException
from pypl2mp3.libs.logger import logger
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import (
    LabelFormatter, 
    CountFormatter, 
    check_and_display_song_selection_result,
    format_song_display,
    prompt_user
)

# Automatically clear style on each print
init(autoreset=True)


class TagJunkSongException(AppBaseException):
    """
    Custom exception for junk song metadata management errors.
    """
    pass


@dataclass
class SongReport:
    """Data structure for song processing report."""
    song_name: str
    youtube_id: str
    filename: str
    detail: Optional[str] = None
    reason: Optional[str] = None

    def __getitem__(self, item: str):
        """
        Implement dictionary-like access to report attributes.
        By the way, this make it subscriptable to be used as a list item.

        Args:
            item: Key to access in the report

        Returns:
            The value associated with the key
        """

        return getattr(self, item)


class JunkSongTagger:
    """Handles the tagging and fixing of junk songs."""

    def __init__(
            self, 
            total_songs: int, 
            prompt_confirm: bool = False,
            shazam_threshold: int = 0, 
            label_width: int = 25
        ):
        """
        Initialize the JunkSongTagger.

        Args:
            total_songs: Total number of songs to process
            prompt_confirm: Whether to prompt for user confirmation
            shazam_threshold: Minimum threshold for Shazam match confidence
            label_width: Width for formatting labels in output
        """

        self.count_formatter = CountFormatter(total_songs)
        self.prompt_confirm = prompt_confirm
        self.shazam_threshold = shazam_threshold
        self.label_formatter = LabelFormatter(label_width)
        self.fixed_songs: List[SongReport] = []
        self.unfixed_songs: List[SongReport] = []


    def _log_success(self, song: SongModel, detail: str) -> None:
        """
        Log successful song fixing.

        Args:
            song: Current SongModel instance
            detail: Detail message for the log
        """

        self.fixed_songs.append(SongReport(
            song_name=f"{song.artist} - {song.title}",
            youtube_id=song.youtube_id,
            filename=song.filename,
            detail=detail
        ))


    def _log_failure(self, song: SongModel, reason: str) -> None:
        """
        Log song fixing failure.

        Args:
            song: Current SongModel instance
            reason: Reason for the failure
        """

        self.unfixed_songs.append(SongReport(
            song_name=f"{song.artist} - {song.title}",
            youtube_id=song.youtube_id,
            filename=song.filename,
            reason=reason
        ))


    async def _prompt_for_metadata(self, song: SongModel) -> bool:
        """
        Prompt user for song metadata input.

        Args:
            song: Current SongModel instance

        Returns:
            bool: True if user confirmed to fix metadata, False otherwise

        Raises:
            Exception: If metadata update fails
        """ 

        while True:
            print(f"{Style.BRIGHT}{Fore.WHITE}Please, input your own MP3 tags " 
                + f"or hit ENTER to confirm purposed ones:")

            # Prompt for artist name
            while True:
                artist_input = (
                    input(
                        f"{Fore.LIGHTBLUE_EX}⇨ Artist"
                        f"{Style.DIM}, default: {Style.RESET_ALL}" 
                        f"{Fore.GREEN}{Style.BRIGHT}{song.artist}"
                        f"{Style.RESET_ALL}: "
                    ) 
                    or song.artist
                ).strip()

                if artist_input == "":
                    print("\033[1A\x1b[K", end = "\r")
                    continue
                else:
                    print("\033[1A\x1b[K", end = "\r")
                    print(
                        self.label_formatter.format("⇨ Artist:")
                        + f"{Fore.LIGHTYELLOW_EX}{artist_input}"
                    )
                    break

            # Prompt for title
            while True:
                title_input = (
                    input(
                        f"{Fore.LIGHTBLUE_EX}⇨ Title"
                        f"{Style.DIM}, default: {Style.RESET_ALL}"
                        f"{Fore.GREEN}{Style.BRIGHT}{song.title}"
                        f"{Style.RESET_ALL}: "
                    ) 
                    or song.title
                ).strip()

                if title_input == "":
                    print("\033[1A\x1b[K", end = "\r")
                    continue
                else:
                    print("\033[1A\x1b[K", end = "\r")
                    print(
                        self.label_formatter.format("⇨ Title:") 
                        + f"{Fore.LIGHTYELLOW_EX}{title_input}"
                    )
                    break

            # Prompt for cover art URL
            while True:
                tip = (
                    "None - Hit ENTER to leave blank or type an URL", 
                    "Available - Hit ENTER to keep existing one or type an URL"
                )[song.cover_art_url is not None]

                cover_art_url_input = (
                    input(
                        f"{Fore.LIGHTBLUE_EX}⇨ Cover art"
                        f"{Style.DIM}, default: {Style.RESET_ALL}" 
                        f"{Fore.GREEN}{tip}"
                        f"{Style.RESET_ALL}: "
                    ) 
                    or (song.cover_art_url or "None")
                ).strip()

                if cover_art_url_input == "":
                    print("\033[1A\x1b[K", end = "\r")
                    continue
                else:
                    choice = (
                        cover_art_url_input, 
                        "Keep existing one"
                    )[cover_art_url_input == song.cover_art_url]

                    print("\033[1A\x1b[K", end = "\r")
                    print(
                        self.label_formatter.format("⇨ Cover art:") 
                        + f"{Fore.LIGHTYELLOW_EX}{Style.DIM}{choice}"
                    )

                    song.cover_art_url = (
                        (None, cover_art_url_input)[
                            cover_art_url_input == song.cover_art_url
                        ] 
                        or (None, cover_art_url_input)[
                            cover_art_url_input != "None"
                        ]
                    )
                    break

            # Prompt for saving MP3 tags and cover art
            save_tags_input = prompt_user(
                "Save MP3 tags and cover art",
                ["yes", "no", "retry"]
            )

            if save_tags_input == "yes":
                try:
                    # Update song MP3 tags with user input
                    song.update_state(
                        artist = artist_input,
                        title = title_input,
                        cover_art_url = cover_art_url_input
                    )

                    # Get song covert art and save it in MP3 file
                    on_download_cover_art = SimpleNamespace(
                        label=self.label_formatter.pad_only("⇨ Get cover art:"),
                        callback=None
                    )
                    await song.update_cover_art(
                        on_download_cover_art=on_download_cover_art
                    )
                    if song.has_cover_art:
                        print(
                            self.label_formatter.format("⇨ Fix MP3 tags:") 
                            + f"MP3 tags and cover art fixed from user input."
                        )
                    else:
                        print(
                            self.label_formatter.format("⇨ Fix MP3 tags:") 
                            + f"{Fore.MAGENTA}WARNING! MP3 tags fixed from " 
                            + f"YouTube but not cover art"
                        )
                except Exception as exc:
                    # Raise exception
                    raise TagJunkSongException(
                        f"Failed to save MP3 tags and cover art"
                    ) from exc

                return True
            
            # Retry if user wants to try again
            elif save_tags_input == "retry":
                continue

            # Exit if user doesn't want to fix metadata
            else:
                return False


    async def _process_single_song(
            self, 
            song: SongModel, 
            song_index: int
        ) -> None:
        """
        Process a single junk song for metadata fixing.

        Args:
            song: SongModel instance to process
            song_index: Current song index
        """

        # Print song information
        counter = self.count_formatter.format(song_index)
        print(
            f"\n{format_song_display(song, counter)}  "
            f"{Fore.WHITE}{Style.DIM}[https://youtu.be/{song.youtube_id}]"
        )
        print(
            self.label_formatter.format("⇨ Junk song filename:")
            + f"{Fore.MAGENTA}{song.filename}"
        )
        print(
            self.label_formatter.format("⇨ Junk song metadata:")
            + f"{Fore.LIGHTCYAN_EX}Artist: {song.artist}, Title: {song.title}, "
            + f"Cover art: {'Available' if song.cover_art_url else 'None'}"
        )
    
        # Prompt user for confirmation to fix junk song.
        # If user declined, log song as unfixed and return.
        if self.prompt_confirm and prompt_user(
            "Do you want to fix this junk song",
            ["yes", "no"]
        ) != "yes":
            
            print(f"{Fore.RED}User declined to fix junk song.")
            self._log_failure(song, "User declined to fix junk song")
            return
        
        # Check if reloading YouTube metadata is needed or prompt
        # user for confirmation to reload YouTube metadata anyway.
        if song.should_be_tagged or not song.has_cover_art:
            print(
                f"{Fore.WHITE}"
                f"Reloading YouTube metadata is required before fixing."
            )
        elif self.prompt_confirm and prompt_user(
            "Do you want to reload YouTube metadata before fixing",
            ["yes", "no"]
        ) == "yes":
            
            song.reset_state()

        try:
            # If required, retrieve song metadata from YouTube.
            if song.should_be_tagged or not song.has_cover_art:
                print(
                    f"Retrieving song metadata from YouTube: Please, wait... ", 
                    end="", 
                    flush=True
                )
                video_url = f"https://youtube.com/watch?v={song.youtube_id}"
                metadata = YouTube(video_url, client="WEB")
                print("\x1b[K", end="\r")
                print(
                    self.label_formatter.format("⇨ YouTube metadata:")
                    + f"{Fore.LIGHTCYAN_EX}Artist: {metadata.author}, " 
                    + f"Title: {metadata.title}, "
                    + f"Cover art: " 
                    + f"{'Available' if metadata.thumbnail_url else 'None'}"
                )
                
                # Update song MP3 tags with YouTube metadata
                song.update_state(
                    artist=metadata.author,
                    title=metadata.title,
                    cover_art_url=metadata.thumbnail_url
                )

                # Get song covert art and save it in MP3 file
                on_download_cover_art = SimpleNamespace(
                    label=self.label_formatter.pad_only("⇨ Get cover art:"),
                    callback=None
                )
                await song.update_cover_art(
                    on_download_cover_art=on_download_cover_art
                )
                if song.has_cover_art:
                    print(
                        self.label_formatter.format("⇨ Fix MP3 tags:")
                        + f"MP3 tags and cover art fixed from YouTube metadata."
                    )
                else:
                    print(
                        self.label_formatter.format("⇨ Fix MP3 tags:")
                        + f"{Fore.MAGENTA}MP3 tags fixed from YouTube metadata " 
                        + f"but not cover art"
                    )
                
            # Proceed to Shazam song recognition.
            # if match score is above threshold, update song MP3 tags 
            # and cover art.
            print(
                f"Submitting song to Shazam: Please, wait... ", 
                end="", 
                flush=True
            )

            await song.shazam_song(shazam_match_threshold=self.shazam_threshold)
            
            print("\x1b[K", end="\r")
            print(
                self.label_formatter.format("⇨ Shazam metadata:")
                + f"{Fore.LIGHTCYAN_EX}Artist: {song.shazam_artist}, "
                + f"Title: {song.shazam_title}, "
                + f"Match: {song.shazam_match_score}%"
            )
            if self.shazam_threshold > 0 \
                and song.shazam_match_score >= self.shazam_threshold:

                on_download_cover_art = SimpleNamespace(
                    label=self.label_formatter.pad_only("⇨ Get cover art:"),
                    callback=None
                )
                await song.update_cover_art(
                    on_download_cover_art=on_download_cover_art
                )
                if song.has_cover_art:
                    print(
                        self.label_formatter.format("⇨ Fix MP3 tags:")
                        + f"MP3 tags and cover art fixed from Shazam metadata."
                    )
                else:
                    print(
                        self.label_formatter.format("⇨ Fix MP3 tags:")
                        + f"{Fore.MAGENTA}MP3 tags fixed from Shazam metadata " 
                        + f"but not cover art"
                    )
            else:
                print(
                    self.label_formatter.format("⇨ Fix MP3 tags:")
                    + f"{Fore.RED}Cover art and MP3 tags not fixed because " 
                    + f"Shazam match is too low"
                )
                
            # If no user confirmation is required and Shazam match score 
            # is above threshold, rename song automatically and mark it 
            # as not junk and log it as fixed.
            # Otherwise, prompt user for metadata input.
            if not self.prompt_confirm:
                if self.shazam_threshold > 0 \
                    and song.shazam_match_score >= self.shazam_threshold:

                    song.fix_filename(mark_as_junk=False)
                    print(
                        f"{Fore.GREEN}{Style.BRIGHT}SUCCESS! Song renamed to: ", 
                        f"{Fore.LIGHTYELLOW_EX}{song.filename}{Fore.RESET} "
                        f"(match {song.shazam_match_score}%)"
                    )
                    self._log_success(
                        song, 
                        f"Song fixed from Shazam metadata " \
                            + f"(match {song.shazam_match_score}%)"
                    )
                    return
                else:
                    print(
                        f"{Fore.RED}"
                        f"Song not fixed because Shazam match is too low"
                        f"({song.shazam_match_score}%)"
                    )
                    self._log_failure(song, "Shazam match is too low")
                    return

        # If an error occured attempting to fix the song and no user 
        # confirmation is required, log the song as unfixed and raise 
        # an exception.
        # Otherwise, log the error and prompt user for metadata input.
        except Exception as exc:
            if not self.prompt_confirm:
                self._log_failure(
                    song, 
                    f"Failed to fix song automatically: {str(exc)}"
                )
                raise TagJunkSongException(
                    f"Failed to fix junk song automatically"
                ) from exc
            else:
                logger.error(exc, f"Failed to fix song")

        # Prompt user for metadata input.
        # If user declines, log the song as unfixed and return.
        if not await self._prompt_for_metadata(song):
            print(f"{Fore.RED}User declined to confirm or input metadata.")
            self._log_failure(
                song, 
                "User declined to confirm or input metadata"
            )
            return
        
        # Prompt for fixing junk song filename.
        # If user declines, log the song as unfixed and return.
        print(
            self.label_formatter.format("⇨ New filename from tags:") 
            + f"{Fore.CYAN}{Style.BRIGHT}{song.expected_filename}"
        )
        filename_fix_choice = prompt_user(
            "Fix junk song filename and optionally keep \"junk\" mark",
            ["yes", "no", "junk"]
        )
        if filename_fix_choice != "yes" and filename_fix_choice != "junk":
            print(f"{Fore.RED}User declined to fix junk song filename.")
            self._log_failure(
                song, 
                "User declined to fix junk song filename"
            )
            return
        
        # Attempt to fix the filename and mark the song as not junk.
        # If successful, log the song as fixed.
        # If an error occurs, log the song as unfixed and raise an exception.
        try:
            song.fix_filename(mark_as_junk=filename_fix_choice == "junk")
            detail = "Song fixed from Shazam metadata"
            if song.title != song.shazam_title \
                or song.artist != song.shazam_artist \
                or song.cover_art_url != song.shazam_cover_art_url:

                detail = "Song fixed from user input"

            if filename_fix_choice == "junk":
                print(
                    f"{Fore.MAGENTA}" 
                    f"Song fixed but kept marked as junk: "
                    f"{Fore.LIGHTYELLOW_EX}{song.filename}"
                )
                self._log_failure(
                    song, 
                    f"{detail} but kept marked as junk"
                )
            else:
                print(
                    f"{Fore.GREEN}{Style.BRIGHT}" 
                    f"SUCCESS! Song fixed and renamed to: "
                    f"{Fore.LIGHTYELLOW_EX}{song.filename}"
                )
                self._log_success(song, detail)
        except Exception as exc:
            self._log_failure(
                song, 
                f"Failed to rename junk song: {str(exc)}"
            )
            raise TagJunkSongException(
                f"Failed to rename junk song: {str(exc)}"
            ) from exc


    def _print_report(self) -> None:
        """
        Print final processing report.
        """
        print(f"\n\n{Back.BLUE}{Fore.WHITE} Report summary ")

        print(
            f"\n{Fore.LIGHTYELLOW_EX}"
            f"- Successfully fixed junk songs ........... " 
            f"{len(self.fixed_songs)}"
        )
        print(
            f"{Fore.MAGENTA}"
            f"- Unfixed junk songs ...................... " 
            f"{len(self.unfixed_songs)}"
        )
        print(
            f"\n{Fore.CYAN}"
            f"- Total number of processed songs ......... " 
            f"{len(self.fixed_songs) + len(self.unfixed_songs)}"
        )
        
        if len(self.fixed_songs) > 0:
            print(f"\n\n{Back.YELLOW}{Fore.WHITE} Fixed junk song report ")
            for item in self.fixed_songs:
                print()
                print(
                    f"{Fore.WHITE}{Style.DIM}- YouTube ID: {Style.NORMAL}" 
                    f"{Fore.WHITE}{item['youtube_id']}"
                )
                print(
                    f"{Fore.WHITE}{Style.DIM}  Song name:  {Style.NORMAL}" 
                    f"{Fore.CYAN}{item['song_name']}"
                )
                print(
                    f"{Fore.WHITE}{Style.DIM}  Filename:   {Style.NORMAL}" 
                    f"{Fore.CYAN}{item['filename']}"
                )
                print(
                    f"{Fore.WHITE}{Style.DIM}  Detail:     {Style.NORMAL}" 
                    f"{Fore.LIGHTYELLOW_EX}{item['detail']}"
                )

        if len(self.unfixed_songs) > 0:
            print(f"\n\n{Back.MAGENTA}{Fore.WHITE} Unfixed junk songs report ")
            for item in self.unfixed_songs:
                print()
                print(
                    f"{Fore.WHITE}{Style.DIM}- YouTube ID: {Style.NORMAL}" 
                    f"{Fore.WHITE}{item['youtube_id']}"
                )
                print(
                    f"{Fore.WHITE}{Style.DIM}  Song name:  {Style.NORMAL}" 
                    f"{Fore.CYAN}{item['song_name']}"
                )
                print(
                    f"{Fore.WHITE}{Style.DIM}  Filename:   {Style.NORMAL}" 
                    f"{Fore.CYAN}{item['filename']}"
                )
                print(
                    f"{Fore.WHITE}{Style.DIM}  Reason:     {Style.NORMAL}" 
                    f"{Fore.MAGENTA}{item['reason']}"
                )


async def fix_junks(args: any) -> None:
    """
    Main entry point for junk song fixing process.

    Args:
        args: Command line arguments containing:
            - repo: Repository path
            - prompt: Whether to prompt for confirmation
            - thresh: Shazam match threshold
            - keywords: Search keywords
            - match: Match filter threshold
            - playlist: Playlist identifier
    """
    
    song_files = get_repository_song_files(
        Path(args.repo),
        keywords=args.keywords,
        filter_match_threshold=args.match,
        junk_only=True,
        playlist_identifier=args.playlist,
    )

    # Check if some songs match selection crieria
    # iI none, then return
    try:
        check_and_display_song_selection_result(song_files)
    except SystemExit:
        return

    tagger = JunkSongTagger(
        len(song_files),
        prompt_confirm=args.prompt,
        shazam_threshold=args.thresh
    )

    print(f"\n{Fore.MAGENTA}NOTE: Type CTRL+C twice to exit.\n")

    if not args.prompt and prompt_user(
        f"bout to fix {len(song_files)} junk songs automatically. " \
            + f"Do you want to proceed",
        ["yes", "no"]
    ) != "yes":

        return

    for song_index, song_file in enumerate(song_files, 1):
        try:
            await tagger._process_single_song(SongModel(song_file), song_index)
        except KeyboardInterrupt:
            # Handle keyboard interrupt gracefully
            tagger._print_report()
            raise
        except Exception as exc:
            # Handle any exceptions that occur during processing
            # and skip to the next song.
            logger.error(exc, f"Error processing \"{song_file}\"")
            continue

    # Print final report
    tagger._print_report()