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

# Third party packages
from colorama import Fore, Back, Style, init
from pytubefix import YouTube

# pypl2mp3 libs
from pypl2mp3.libs.exceptions import AppBaseException
from pypl2mp3.libs.logger import logger
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel, ProgressBarInterface
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
    """
    Data structure for song processing report.
    """

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
    """
    Handles the tagging and fixing of junk songs.
    """

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
            song: SongModel instance to process
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
            song: SongModel instance to process
            reason: Reason for the failure
        """

        self.unfixed_songs.append(SongReport(
            song_name=f"{song.artist} - {song.title}",
            youtube_id=song.youtube_id,
            filename=song.filename,
            reason=reason
        ))


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


    async def _prompt_for_metadata(self, song: SongModel) -> bool:
        """
        Prompt user for song metadata input.

        Args:
            song: SongModel instance to process

        Returns:
            bool: True if user confirmed to fix metadata, False otherwise

        Raises:
            TagJunkSongException: If metadata update fails
        """ 

        while True:
            print(
                f"{Style.BRIGHT}{Fore.WHITE}" 
                "Please, input your own MP3 tags " 
                "or hit ENTER to confirm purposed ones:"
            )

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
                    "Exists - Hit ENTER to keep existing one or type an URL"
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

                # Update song MP3 tags with user input
                song.update_state(
                    artist = artist_input,
                    title = title_input,
                    cover_art_url = cover_art_url_input
                )

                try:
                    # Get song covert art and save it in MP3 file
                    on_download_cover_art = ProgressBarInterface(
                        label=self.label_formatter.pad_only("⇨ Get cover art:"),
                        callback=None
                    )
                    await song.update_cover_art(
                        on_download_cover_art=on_download_cover_art
                    )
                except Exception as exc:
                    # Raise exception
                    raise TagJunkSongException(
                        f"Failed to download specified cover art"
                    ) from exc

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

                return True
            
            # Retry if user wants to try again
            elif save_tags_input == "retry":
                continue

            # Exit if user doesn't want to fix metadata
            else:
                return False


    async def _get_youtube_metadata(self, song: SongModel) -> None:
        """
        Retrieve and update song metadata from YouTube.

        Args:
            song: SongModel instance to process

        Raises:
            TagJunkSongException: If YouTube metadata retrieval fails
                or YouTube cover art download fails
        """

        print(
            f"Retrieving song metadata from YouTube: Please, wait... ", 
            end="", 
            flush=True
        )

        try:
            video_url = f"https://youtube.com/watch?v={song.youtube_id}"
            metadata = YouTube(video_url, client="WEB")

            cover_art_status = 'Exists' if metadata.thumbnail_url else 'None'

            print("\x1b[K", end="\r")
            print(
                self.label_formatter.format("⇨ YouTube metadata:")
                + f"{Fore.LIGHTCYAN_EX}"
                + f"{Style.DIM}Artist:{Style.NORMAL} {metadata.author}, "
                + f"{Style.DIM}Title:{Style.NORMAL} {metadata.title}, "
                + f"{Style.DIM}Cover art:{Style.NORMAL} {cover_art_status}"
            )
        except Exception as exc:
            # Raise exception
            print()  # Jump to next line in terminal before printing error
            raise TagJunkSongException(
                f"Failed to retrieve YouTube metadata"
            ) from exc

        song.update_state(
            artist=metadata.author,
            title=metadata.title,
            cover_art_url=metadata.thumbnail_url
        )

        try:
            on_download_cover_art = ProgressBarInterface(
                label=self.label_formatter.pad_only("⇨ Get cover art:"),
                callback=None
            )
            await song.update_cover_art(
                on_download_cover_art=on_download_cover_art
            )
        except Exception as exc:
            # Raise exception
            raise TagJunkSongException(
                f"Failed to download YouTube cover art"
            ) from exc

        if song.has_cover_art:
            print(
                self.label_formatter.format("⇨ Fix MP3 tags:")
                + "MP3 tags and cover art fixed from YouTube metadata."
            )
        else:
            print(
                self.label_formatter.format("⇨ Fix MP3 tags:")
                + f"{Fore.MAGENTA}" 
                + "MP3 tags fixed from YouTube metadata but not cover art"
            )


    async def _process_shazam_recognition(self, song: SongModel) -> bool:
        """
        Process Shazam song recognition and update metadata 
        if match is good enough.

        Args:
            song: SongModel instance to process

        Returns:
            bool: True if song recognition succeeded, False otherwise

        Raises:
            TagJunkSongException: If Shazam song recognition fails
                or Shazam cover art download fails
        """

        print(
            "Submitting song to Shazam: Please, wait... ", 
            end="", 
            flush=True
        )

        try:
            await song.shazam_song(shazam_match_threshold=self.shazam_threshold)
        except Exception as exc:
            raise TagJunkSongException(
                "Failed to perfom Shazam song recognition"
            ) from exc
        
        print("\x1b[K", end="\r")
        print(
            self.label_formatter.format("⇨ Shazam metadata:")
            + f"{Fore.LIGHTCYAN_EX}"
            + f"{Style.DIM}Artist:{Style.NORMAL} {song.shazam_artist}, "
            + f"{Style.DIM}Title:{Style.NORMAL} {song.shazam_title}, "
            + f"{Style.DIM}Match:{Style.NORMAL} {song.shazam_match_score}%"
        )

        if self.shazam_threshold > 0 \
            and song.shazam_match_score >= self.shazam_threshold:

            try:
                on_download_cover_art = ProgressBarInterface(
                    label=self.label_formatter.pad_only("⇨ Get cover art:"),
                    callback=None
                )
                await song.update_cover_art(
                    on_download_cover_art=on_download_cover_art
                )
            except Exception as exc:
                # Raise exception
                raise TagJunkSongException(
                    f"Failed to download Shazam cover art"
                ) from exc
            
            if song.has_cover_art:
                print(
                    self.label_formatter.format("⇨ Fix MP3 tags:")
                    + "MP3 tags and cover art fixed from Shazam metadata."
                )
            else:
                print(
                    self.label_formatter.format("⇨ Fix MP3 tags:")
                    + f"{Fore.MAGENTA}" 
                    + "MP3 tags fixed from Shazam metadata but not cover art"
                )
            return True
        else:
            print(
                self.label_formatter.format("⇨ Fix MP3 tags:")
                + f"{Fore.RED}" 
                + "Cover art and MP3 tags not fixed " 
                + "because Shazam match is too low"
            )
            return False


    async def _fix_filename(self, song: SongModel) -> None:
        """
        Handle filename fixing process.
        
        Args:
            song: SongModel instance to process

        Raises:
            TagJunkSongException: If it fails to rename MP3 file
        """
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
            self._log_failure(song, "User declined to fix junk song filename")
            return

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
                    "Song fixed but kept marked as junk: "
                    f"{Fore.LIGHTYELLOW_EX}{song.filename}"
                )
                self._log_failure(song, f"{detail} but kept marked as junk")
            else:
                print(
                    f"{Fore.GREEN}{Style.BRIGHT}" 
                    "SUCCESS! Song fixed and renamed to: "
                    f"{Fore.LIGHTYELLOW_EX}{song.filename}"
                )
                self._log_success(song, detail)

        except Exception as exc:
            self._log_failure(song, f"Failed to rename junk song: {str(exc)}")
            raise TagJunkSongException(
                f"Failed to rename junk song: {str(exc)}"
            ) from exc


    async def _process_single_song(self, 
            song: SongModel, 
            song_index: int
        ) -> None:
        """
        Process a single junk song for metadata fixing.

        Args:
            song: SongModel instance to process
            song_index: Index of the song
        """

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
            + f"{Fore.LIGHTMAGENTA_EX}"
            + f"{Style.DIM}Artist:{Style.NORMAL} {song.artist}, "
            + f"{Style.DIM}Title:{Style.NORMAL} {song.title}, "
            + f"{Style.DIM}Cover art:{Style.NORMAL} "
            + f"{'Exists' if song.cover_art_url else 'None'}"
        )

        if self.prompt_confirm \
            and prompt_user(
                "Do you want to fix this junk song", 
                ["yes", "no"]
            ) != "yes":

            print(f"{Fore.RED}User declined to fix junk song.")
            self._log_failure(song, "User declined to fix junk song")
            return

        try:
            if song.should_be_tagged or not song.has_cover_art:
                print(
                    f"{Fore.WHITE}" 
                    "Reloading YouTube metadata is required before fixing."
                )
                await self._get_youtube_metadata(song)
            elif self.prompt_confirm \
                and prompt_user(
                    "Do you want to reload YouTube metadata before fixing", 
                    ["yes", "no"]
                ) == "yes":

                song.reset_state()
                await self._get_youtube_metadata(song)

            shazam_success = await self._process_shazam_recognition(song)
            
            if not self.prompt_confirm:
                if shazam_success:
                    song.fix_filename(mark_as_junk=False)
                    print(
                        f"{Fore.GREEN}{Style.BRIGHT}SUCCESS! Song renamed to: ",
                        f"{Fore.LIGHTYELLOW_EX}{song.filename}{Fore.RESET} "
                        f"(match {song.shazam_match_score}%)"
                    )
                    self._log_success(
                        song, 
                        "Song fixed from Shazam metadata " 
                        + f"(match {song.shazam_match_score}%)"
                    )
                    return
                else:
                    print(
                        f"{Fore.RED}Song not fixed because Shazam match " 
                        f"is too low({song.shazam_match_score}%)"
                    )
                    self._log_failure(song, "Shazam match is too low")
                    return

        except Exception as exc:
            if not self.prompt_confirm:
                self._log_failure(
                    song, 
                    f"Failed to fix song automatically: {str(exc)}"
                )
                raise TagJunkSongException(
                    "Failed to fix junk song automatically"
                ) from exc
            else:
                logger.error(exc, "Failed to fix song")

        if not await self._prompt_for_metadata(song):
            print(f"{Fore.RED}User declined to confirm or input metadata.")
            self._log_failure(
                song, 
                "User declined to confirm or input metadata"
            )
            return

        await self._fix_filename(song)


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
            + "Do you want to proceed",
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