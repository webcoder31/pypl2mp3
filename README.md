
# PYPL2MP3 - YouTube playlist MP3 converter<br>that can also shazam, tag and play songs

PYPL2MP3 is a Python program that downloads audio from entire YouTube playlists and saves the tracks in MP3 format with Shazam-confirmed ID3 tags and proper cover art.

The program runs from the command line and is designed for a clean and user-friendly experience.

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

---

## Features

- Import YouTube playlist songs in MP3 format  
- Automatically identify songs using Shazam to set accurate ID3 tags and cover art  
- Manually tag or clean up unmatched ("junk") songs  
- List songs and playlists with detailed info  
- Play songs directly from the CLI or open their YouTube videos  
- Filter and sort songs via fuzzy search  

---

## Limitations

- Only public playlists can be imported  
- Region-restricted videos are excluded  
- Age-restricted videos cannot be imported (but do not block others)  

---

## Requirements

PYPL2MP3 requires:

- Python ≥ 3.7  
- [`pytubefix`](https://pytubefix.readthedocs.io/) (used under the hood)  

### Dependency Manager

- [Poetry](https://python-poetry.org/docs/) is required to manage dependencies.

### Audio Tools

- [`ffmpeg`](https://www.ffmpeg.org/) and `ffprobe` must be installed for audio conversion and tagging.

### Proof of Origin Token

- A Proof of Origin Token (POT) is needed to access YouTube audio streams, generated using [Node.js](https://nodejs.org/en/download) via BotGuard.  
- Supported automatically from `pytubefix` version `8.12`.  
  → [Details here](https://pytubefix.readthedocs.io/en/latest/user/po_token.html)

---

## Installation

```sh
poetry install
```

---

## Configuration

PYPL2MP3 works out of the box, storing imported playlists in `~/pypl2mp3` by default.

### Optional Environment Variables

- **`PYPL2MP3_DEFAULT_REPOSITORY_PATH`** – Custom path for storing playlists  
- **`PYPL2MP3_DEFAULT_PLAYLIST_ID`** – Default YouTube playlist ID for quick access

Example setup (in terminal):
```sh
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="/your/custom/path"
export PYPL2MP3_DEFAULT_PLAYLIST_ID="yourPlaylistID"
```

To persist settings, add these to your `.bashrc` or `.zshrc`.

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

**Note:** In the command usages described bellow, the term "INDEX" refers to the rank of an item in a list of songs or playlists resulting from a command; it therefore only make sense at the time the command is ran.


### Global Options
- `-r, --repo <path>`: Set playlist repository (default: `~/pypl2mp3`)  
- `-h, --help`: Show command-specific help  

---

### `import` – Import songs from a YouTube playlist
```sh
pypl2mp3 import [options] <playlist>
```
Options:
- `playlist`: ID, URL or INDEX of a playlist to import (default: see configuration)
- `-f, --filter <inputs>`: Filter songs to import using keywords
- `-m, --match <level>`: Filter match threshold (0-100, default: 45)
- `-t, --thresh <level>`: Shazam match threshold (0-100, default: 50)
- `-p, --prompt`: Prompt before importing each new song

This command imports a new YouTube playlist and also syncs previously imported tracks. When syncing, only tracks newly added to the YouTube playlist are eligible for import.

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
- `-f, --filter <inputs>`: Filter songs using keywords and sort by relevance
- `-m, --match <level>`: Filter match threshold (0-100, default: 45)
- `-v, --verbose`: Enable verbose output

---

### `junks` – List unmatched "junk" songs
```sh
pypl2mp3 junks [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <inputs>`: Filter songs using keywords and sort by relevance
- `-m, --match <level>`: Filter match threshold (0-100, default: 45)
- `-v, --verbose`: Enable verbose output

---

### `tag` – Add metadata to "junk" songs
```sh
pypl2mp3 tag [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <inputs>`: Filter songs using keywords and sort by relevance
- `-m, --match <level>`: Filter match threshold (0-100, default: 45)
- `-t, --thresh <level>`: Shazam match threshold (0-100, default: 50)
- `-p, --prompt`: Prompt to set ID3 tags and cover art for each song

---

### `untag` – Remove metadata from songs
```sh
pypl2mp3 untag [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <inputs>`: Filter songs using keywords and sort by relevance
- `-m, --match <level>`: Filter match threshold (0-100, default: 45)
- `-p, --prompt`: Prompt to removes ID3 tags and cover art from each song

---

### `videos` – Open YouTube videos for songs
```sh
pypl2mp3 videos [options]
```
Options:
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <inputs>`: Filter songs using keywords and sort by relevance
- `-m, --match <level>`: Filter match threshold (0-100, default: 45)
- `-v, --verbose`: Enable verbose output

---

### `play` – Play songs
```sh
pypl2mp3 play [options] [filter] [index]
```
Options:
- `filter`: Filter songs using keywords and sort by relevance
- `index`: INDEX of a song to play (0 for random song)
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-m, --match <level>`: Filter match threshold (0-100, default: 45)
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

**Import / sync playlist**
```sh
pypl2mp3 import PLP6XxNg42qDG3u8ldvEEtWC8q0p0BLJXJ
```

**Retrieve Jimmy Hendrix songs from imported playlists**
```sh
pypl2mp3 songs -f "hendrix"
```

**Tag Shazam-unmatched (junk) songs interactively**
```sh
pypl2mp3 tag -p
```

**Play random Dire Straits songs from playlist #2**
```sh
pypl2mp3 play -l 2 -s "dire straits"
```

---

## Troubleshooting

Issues during import or tagging may be due to recent YouTube changes. Try updating `pytubefix`:
```sh
poetry add pytubefix@latest
```