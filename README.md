
# YouTube playlist MP3 converter<br>that can shazam, tag and also play songs

**PYPL2MP3** is a Python program that one-shot downloads audio from 
**entire YouTube playlists** and saves the tracks in MP3 format with 
shazam-confirmed ID3 tags and proper cover art. It also allows you to 
play imported MP3s, search for songs across all imported playlists, 
manage metadata, and much more.

The program runs from the command line and is designed for a clean and 
user-friendly experience.

![YLP2MP3 screenshot](/docs/readme/cover.jpg)

---

## Table of contents
[Features](#features)&nbsp;&nbsp; 
[Limitations](#limitations)&nbsp;&nbsp; 
[Requirements](#requirements)&nbsp;&nbsp; 
[Installation](#installation)&nbsp;&nbsp; 
[Configuration](#configuration)&nbsp;&nbsp; 
[Execution](#execution)&nbsp;&nbsp; 
[Usage](#usage)&nbsp;&nbsp; 
[Commands](#commands)&nbsp;&nbsp; 
[Examples](#examples)&nbsp;&nbsp;
[Troubleshooting](#troubleshooting)&nbsp;&nbsp; 
[Thanks](#thanks)&nbsp;&nbsp; 

---

## Features

- Import YouTube playlist songs in MP3 format  
- Automatically shazam songs to set accurate ID3 tags and cover art  
- Consistently name MP3 files by artist and song title
- Fix metadata to shazam-unmatched "junk" songs
- Cleanup existing metadata from imported songs
- List songs and playlists with detailed information  
- Easily play songs directly from the CLI and open related videos
- Filter and sort songs via fuzzy search (available for all commands)  

---

## Limitations

- Only public playlists can be imported  
- Region-restricted videos are excluded from import 
- Import of age-restricted videos fails but do not block others  

---

## Requirements

PYPL2MP3 requires:

- Python ≥ 3.7  

### Dependency Manager

- [Poetry](https://python-poetry.org/docs/) is required to manage dependencies 
  and run the program in its own virtual env.

### Audio Tools

- [`ffmpeg`](https://www.ffmpeg.org/) and `ffprobe` (shipped together) must be 
  installed for audio conversion and tagging.

### Proof of Origin Token

- A Proof of Origin Token (POT) is needed to access YouTube audio / video streams 
  ([details here](https://pytubefix.readthedocs.io/en/latest/user/po_token.html)).  
- It is automatically generated via **BotGuard** from `pytubefix` version `8.12` 
  and requires [`Node.js`](https://nodejs.org/en/download) to be installed.  

---

## Installation

```sh
poetry install
```

---

## Configuration

PYPL2MP3 works out of the box, storing imported playlists in `~/pypl2mp3` 
by default. It does not require any database.

### Optional Environment Variables

- **`PYPL2MP3_DEFAULT_REPOSITORY_PATH`** 
  – Folder path for storing imported MP3 playlists 
- **`PYPL2MP3_DEFAULT_PLAYLIST_ID`** 
  – Favorite YouTube playlist ID for quick access

Example setup (in terminal):
```sh
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="/your/custom/path"
export PYPL2MP3_DEFAULT_PLAYLIST_ID="yourFavoritePlaylistID"
```

To persist settings, add these to your `.bashrc` or `.zshrc` file.

---

## Execution

From the project root, run:
```sh
poetry run pypl2mp3 <command> [options]
```

Or use the shell wrapper from any directory:
```sh
sh /path/to/pypl2mp3.sh <command> [options]
```

---

## Usage

- Run a command:  
  ```sh
  pypl2mp3 <command> [options]
  ```

- List available commands:  
  ```sh
  pypl2mp3 --help
  ```

- Get help for a specific command:  
  ```sh
  pypl2mp3 <command> --help
  ```

---

## Commands

**Note:** 
In the command uses described below, the term "INDEX" refers to the rank of an 
item in a list of songs or playlists resulting from the applied filter criteria; 
it therefore only has meaning at the time of command execution.


### Global Options
- `-h, --help`: 
  Show command-specific help  
- `-r, --repo <path>`: 
  Set playlist repository (default: see [Configuration](#configuration))  
- `-d, --debug`: 
  Enable **verbose errors (*)** and logging to file `/repo/path/pypl2mp3.log`
- `-D, --deep`:
  Enable deep debug with fully detailed stack trace in log file

**(*) Verbose errors** display a shortened version of the stack trace:
```
[ERROR] Failed to import song "LANA DEL REY - COLA (OFFICIAL AUDIO)"
        [2] pypl2mp3.libs.song.SongModelException: Failed to stream audio track for YouTube video "UtVUkZ4Rx_I"
        [1] pytubefix.exceptions.AgeRestrictedError: UtVUkZ4Rx_I is age restricted, and can't be accessed without logging in.
```
---

### `import` – Import songs from a YouTube playlist
```sh
pypl2mp3 import [options] <playlist>
```
Arguments (may be optional if a favorite playlist is configured):
- `playlist`: ID, URL or INDEX of a playlist to import 
              (default: see [Configuration](#configuration))
  
  **Note:** 
  *Song URLs are also accepted; the playlist ID will be extracted from them.*

Options:
- `-f, --filter <filter>`: Filter songs to import using keywords
- `-m, --match <percent>`: Filter match threshold (0-100, default: 45)
- `-t, --thresh <percent>`: Shazam match threshold (0-100, default: 50)
- `-p, --prompt`: Prompt before importing each new song

This command imports a new YouTube playlist and also syncs previously imported 
tracks. When syncing, only tracks newly added to the YouTube playlist are 
eligible for import. It also provides a prompt mode to confirm each song import.

---

### `playlists` – List imported playlists
```sh
pypl2mp3 playlists
```

---

### `songs` – List songs in imported playlists
```sh
pypl2mp3 songs [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <filter>`: Filter songs using keywords and sort by relevance
- `-m, --match <percent>`: Filter match threshold (0-100, default: 45)
- `-v, --verbose`: Enable verbose output

---

### `junks` – List shazam-unmatched "junk" songs
```sh
pypl2mp3 junks [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <filter>`: Filter songs using keywords and sort by relevance
- `-m, --match <percent>`: Filter match threshold (0-100, default: 45)
- `-v, --verbose`: Enable verbose output

---

### `fix` – Fix metadata and rename "junk" songs
```sh
pypl2mp3 tag [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <filter>`: Filter songs using keywords and sort by relevance
- `-m, --match <percent>`: Filter match threshold (0-100, default: 45)
- `-t, --thresh <percent>`: Shazam match threshold (0-100, default: 50)
- `-p, --prompt`: Prompt to set ID3 tags and cover art for each song

This command attempts to batch retrieve "junk" song metadata from YouTube and 
then Shazam and automatically fix MP3 filenames. It also provides an interactive 
prompt mode to validate or fix the retrieved metadata for each of the selected 
songs and rename the MP3 files accordingly.

---

### `junkize` – Remove metadata and make songs "junk"
```sh
pypl2mp3 untag [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <filter>`: Filter songs using keywords and sort by relevance
- `-m, --match <percent>`: Filter match threshold (0-100, default: 45)
- `-p, --prompt`: Prompt to removes ID3 tags and cover art from each song

This command batch cleanup metadata for all selected songs and rename them as 
"junk". It also provides a prompt mode to confirm cleanup song by song.

---

### `videos` – Open YouTube videos for songs
```sh
pypl2mp3 videos [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <filter>`: Filter songs using keywords and sort by relevance
- `-m, --match <percent>`: Filter match threshold (0-100, default: 45)
- `-v, --verbose`: Enable verbose output

This command prompts to open the YouTube video for each of the selected songs.

---

### `play` – Play songs
```sh
pypl2mp3 play [options] [filter] [index]
```

Arguments (optional):
- `filter`: Filter songs using keywords and sort by relevance
- `index`: INDEX of a single song to play (0 for random song)

Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-m, --match <percent>`: Filter match threshold (0-100, default: 45)
- `-s, --shuffle`: Play songs in random order
- `-v, --verbose`: Enable verbose output

**Player controls:**
```
[  <--  ] Previous song / Play backward
[  -->  ] Next song / Play forward
[ SPACE ] Pause song / Play song
[  TAB  ] Open song's video in browser
[  ESC  ] Quit player
```

---

## Examples

**Import / sync a YouTube playlist with accurate Shazam recognition**
```sh
pypl2mp3 import -t 70 "https://www.youtube.com/playlist?list=PLP6XxNg42qDG3u8ldvEEtWC8q0p0BLJXJ"
```

**Permissively retrieve Jimi Hendrix songs from all imported playlists**
```sh
pypl2mp3 songs -f "hendrix jim" -m 25
```

**Interactively fix shazam-unmatched "junk" songs in a given playlist**
```sh
pypl2mp3 fix -l PLP6XxNg42qDG3u8ldvEEtWC8q0p0BLJXJ -p
```

**Play random Dire Straits songs from playlist #2**
```sh
pypl2mp3 play -l 2 -s "dire straits"
```

---

## Troubleshooting

Issues during import or tagging may be due to recent YouTube changes. 
Try updating `pytubefix`:
```sh
poetry add pytubefix@latest
```

---

## Thanks

PYPL2MP3 relies primarily on [`pytubefix`](https://github.com/JuanBindez/pytubefix) 
and [`shazamio`](https://github.com/shazamio/ShazamIO) under the hood to provide 
its core features. These packages work perfectly and are well maintained. They 
also require a lot of effort to sync with the services they provide access to. 
So, if you like PYPL2MP3, please give them a&nbsp;★ on GitHub.