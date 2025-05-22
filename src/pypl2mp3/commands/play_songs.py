#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module handles playback of MP3 files from playlists 
with keyboard controls and song information display.

Features:
- Play/pause/skip controls
- Playlist navigation (forward/backward)
- Song information display
- YouTube link integration

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
import os
from pathlib import Path
import random
from threading import Thread
import webbrowser
from dataclasses import dataclass
from typing import Optional

# Third party packages
from colorama import Fore, Style, init
from sshkeyboard import listen_keyboard, stop_listening

# Import pygame
# First set env var to hide pygame support prompt 
# This is necessary to avoid pygame's support prompt
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

# pypl2mp3 libs
from pypl2mp3.libs.exceptions import AppBaseException
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import (
    LabelFormatter, 
    CountFormatter, 
    check_and_display_song_selection_result,
    format_song_display,
    format_song_details_display
)

# Automatically clear style on each print
init(autoreset=True)


class PlaySongException(AppBaseException):
    """
    Custom exception for song player errors.
    """
    pass


@dataclass
class PlayerState:
    """
    Maintains the state of the music player.
    Attributes:
        song_files: List of song file paths
        song_count: Total number of songs
        current_index: Index of the currently playing song
        current_url: URL of the currently playing song
        is_running: Flag indicating if the player is running
        is_paused: Flag indicating if the player is paused
        play_direction: Direction of playback ('forward' or 'backward')
        count_formatter: Progress counter instance for displaying progress
        verbose: Flag for verbose output
        player_thread: Thread instance for running the player
    """
    song_files: list[Path] = None
    song_count: int = 0
    current_index: int = -1
    current_url: Optional[str] = None
    is_running: bool = False
    is_paused: bool = False
    play_direction: str = "forward"
    count_formatter: Optional[CountFormatter] = None
    verbose: bool = False
    player_thread: Optional[Thread] = None


# Global state instance
player = PlayerState()


def _init_pygame_mixer() -> None:
    """
    Initialize pygame mixer for audio playback.
    """

    pygame.mixer.init()


def _cleanup_player() -> None:
    """
    Clean up player resources and stop playback.
    """

    pygame.mixer.music.stop()
    stop_listening()
    pygame.quit()
    if player.player_thread:
        player.player_thread.join()


def _get_next_song_index(current: int, direction: str, total: int) -> int:
    """
    Calculate the next song index based on direction.

    Args:
        current: Current song index
        direction: Play direction ('forward' or 'backward')
        total: Total number of songs

    Returns:
        int: Next song index
    """

    step = 1 if direction == "forward" else -1
    next_index = current + step
    next_index = (next_index + total) % (2 * total) - total

    if next_index < 0:
        next_index = total + next_index

    return next_index


def _display_song_information(
        song: SongModel, 
        counter: str, 
        is_next: bool = False
    ) -> None:
    """
    Display song information with formatting.

    This function formats and prints the song information
    including the title, artist, duration, and other metadata.
    It also handles the display of the next song preview.

    Args:
        song: SongModel instance containing song metadata
        counter: Progress counter string
        is_next: Whether this is the next song preview
    """

    if not is_next:
        print("\033[2K\033[1G", end="\r")  # Clear line
        print(format_song_display(song, counter))
        
        if player.verbose:
            print(format_song_details_display(song, player.count_formatter))
    else:
        next_counter = player.count_formatter.placeholder(
            "<--" if player.play_direction == "backward" else "-->"
        )
        print(
            ("\n" if player.verbose else "") + 
            f"{next_counter}  {Fore.LIGHTYELLOW_EX}{Style.DIM}{song.duration}  "
            f"{song.artist}  {song.title}" 
            f"{' (JUNK)' if song.has_junk_filename else ''}{Style.RESET_ALL}",
            end="", 
            flush=True
        )


def _run_playback_loop() -> None:
    """
    Main loop for playing songs in the playlist.
    This function handles the playback of songs, including
    loading, playing, and handling user input for controls.
    """

    while True:
        player.current_index = _get_next_song_index(
            player.current_index, player.play_direction, player.song_count
        )
                
        current_file = player.song_files[player.current_index]
        current_song = SongModel(current_file)
        player.current_url = f"https://youtu.be/{current_song.youtube_id}"

        counter = player.count_formatter.format(player.current_index + 1)
        _display_song_information(current_song, counter)

        next_index = _get_next_song_index(
            player.current_index, player.play_direction, player.song_count
        )

        next_song = SongModel(player.song_files[next_index])
        _display_song_information(next_song, "", is_next=True)

        try:
            pygame.mixer.music.load(current_file)
            pygame.mixer.music.play()
            clock = pygame.time.Clock()
            player.is_running = True

            while player.is_running \
                    and (pygame.mixer.music.get_busy() or player.is_paused):
                clock.tick(1)

        # except KeyboardInterrupt:
        #     # Handle keyboard interrupt gracefully
        #     _cleanup_player()
        #     raise
        except pygame.error as exc:
            # Handle pygame error during playback
            _cleanup_player()
            raise PlaySongException(
                f"Audio mixer error playing song: {current_file}"
            ) from exc
        except Exception as exc:
            # Handle any other unexpected errors
            _cleanup_player()
            raise PlaySongException(
                f"Unexpected error playing song: {current_file}"
            ) from exc


async def _handle_keypress(key: str) -> None:
    """
    Handle keyboard input for player control.

    Args:
        key: Pressed key identifier
    """

    controls = {
        "right": lambda: setattr(player, "play_direction", "forward"),
        "left": lambda: setattr(player, "play_direction", "backward"),
        "space": _toggle_pause,
        "tab": lambda: webbrowser.open(player.current_url),
        "esc": _cleanup_player
    }

    if key in controls:
        controls[key]()

        if key in ("right", "left"):
            # Skip to next song
            player.is_running = False


def _toggle_pause() -> None:
    """
    Toggle play/pause state.
    """

    player.is_paused = not player.is_paused
    if player.is_paused:
        pygame.mixer.music.pause()
    else:
        pygame.mixer.music.unpause()


def _display_controls() -> None:
    """
    Display available keyboard controls.
    """

    controls = [
        ("  <--  ", "Prev song / Play backward"),
        ("  -->  ", "Next song / Play forward"),
        (" SPACE ", "Pause song / Play song"),
        ("  TAB  ", "Open song video in browser"),
        ("  ESC  ", "Quit player")
    ]

    print()
    for key, description in controls:
        print(
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}[{key}]  {Style.RESET_ALL}"
            f"{Fore.LIGHTMAGENTA_EX}{description}"
        )
    print()


def play_songs(args: any) -> None:
    """
    Main entry point for the song player.

    Args:
        args: Command line arguments containing:
            - repo: Repository path
            - keywords: Search keywords
            - verbose: Verbose output flag
            - match: Match threshold
            - index: Song index
            - playlist: Playlist identifier
            - shuffle: Shuffle playlist flag
    """
    
    player.verbose = args.verbose
    player.song_files = get_repository_song_files(
        Path(args.repo),
        keywords=args.keywords,
        filter_match_threshold=args.match,
        song_index=args.index,
        playlist_identifier=args.playlist,
    )

    # Check if some songs match selection crieria
    # iI none, then return
    try:
        check_and_display_song_selection_result(player.song_files)
    except SystemExit as exc:
        return

    if args.shuffle:
        random.shuffle(player.song_files)

    player.song_count = len(player.song_files)
    player.count_formatter = CountFormatter(player.song_count)

    _init_pygame_mixer()
    _display_controls()

    try:
        player.player_thread = Thread(target=_run_playback_loop, daemon=True)
        player.player_thread.start()
    except KeyboardInterrupt:
        # Handle keyboard interrupt gracefully
        _cleanup_player()
        raise

    listen_keyboard(on_press=_handle_keypress, sequential=True)
