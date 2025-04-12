# A YouTube playlist MP3 converter<br>that can also shazam, tag and play songs

PYPL2MP3 is a Python program that allows you to download audio tracks from YouTube videos for entire playlists and store them in MP3 format on your computer with Shazam-confirmed ID3 tags and proper cover art.

The program works from the command line. Nevertheless, it is crafted to be friendly, offering a clean and pleasant user experience.

![YLP2MP3 screenshot](/docs/readme/cover.jpg)


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


## Features

PYPL2MP3 offers the following features:

- Import songs of YouTube playlists in MP3 format 
- Automatically "shazam" songs to get and set confirmed ID3 tags with proper cover art
- Manually set or fix ID3 tags and manage "junk" songs (no match found on Shazam)
- List imported songs and playlists with detailed information
- Play MP3 songs from CLI and open related videos in your default web browser
- Filter and sort songs via fuzzy search in MP3 playlists


## Limitations

PYPL2MP3 has the following limitations:

- Only public YouTube playlists can be imported.
- Videos restricted to countries that do not match yours are excluded from import.
- Uploading an age-restricted video will fail but will not prevent other videos in the playlist from being downloaded and converted.


## Requirements

PYPL2MP3 run under Python 3 (version `3.7` or higher) and uses `pytubefix` package under the hood.


### Package manager

PYPL2MP3 requires `poetry` to manage its dependencies. So you need it to install the program on your computer ([install instructions here](https://python-poetry.org/docs/)).


### Audio framework

To perform MP3 conversion and to set ID3 tags to MP3 files, PYPL2MP3 needs `ffmpeg` and `ffprobe` binaries to be installed on your computer (see [FFmpeg website](https://www.ffmpeg.org/)).


### Proof of origin token

To access YouTube audio streams, a "proof of origin token" (POT) is required. Otherwise PYPL2MP3 may be banned as a bot.

This token is generated by BotGuard third-party program to attest the requests are coming from a genuine client. It needs you have `nodejs` installed on your computer to run ([install instructions here](https://nodejs.org/en/download)). 

**Note:** Support for automatic generation of POT is available from the version `8.12` of `pytubefix` ([more details here](https://pytubefix.readthedocs.io/en/latest/user/po_token.html)).


## Installation

Once `poetry` installed, type the following command to install PYPL2MP3 dependencies:
```sh
poetry install
```


## Configuration

PYPL2MP3 works out of the box. It does not need any configuration file nor use a database. 

By default, PYPL2MP3 store imported playlists in a folder named `pypl2mp3` on your $HOME directory. If this does not suit your needs, you can set the environment variable `PYPL2MP3_DEFAULT_REPOSITORY_PATH` to the path where you want imported playlists to be stored. This will avoid you to pass this path via the `--repo` option to the PYPL2MP3 commands.

In the same way, if you regularly import songs from a favorite YouTube playlist you use to add newly discovered songs, you can define it as your default playlist by setting its YouTube ID in the environment variable `PYPL2MP3_DEFAULT_PLAYLIST_ID`. This will avoid you to pass this ID as argument or option to the PYPL2MP3 commands.

To set your default repository path and your default YouTube playlist for current shell and all processes started from it, type the following in your terminal:
```sh
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="</full/path/to/your/repository>"
export PYPL2MP3_DEFAULT_PLAYLIST_ID="<Your favorite YouTube playlist ID>"
```

To set them permanently for all future terminal sessions, add the same instructions to your `.bashrc` file (or `.zshrc` and so on) in your $HOME directory.


## Execution

To run a PYPL2MP3 command, type the following in your terminal, from the root folder of this package (the folder containing this README file):
```sh
poetry run pypl2mp3 <command> [options]
```

Or, more convenient, call the following shell script from any location of your computer without having to leave your current working directory to execute the `poetry` command:
```sh
sh /absolute/or/relative/path/to/pypl2mp3.sh <command> [options]
```


## Usage

Run a command:
```sh
pypl2mp3 <command> [options]
```

List all the avaible commands:
```sh
pypl2mp3 --help
```

Get usage for a particular command:
```sh
pypl2mp3 <command> --help
```


## Commands

PYPL2MP3 provides the following commands:

- [`import`](#import-songs-from-a-youtube-playlist): Import songs from a YouTube playlist
- [`playlists`](#list-created-mp3-playlists): List created MP3 playlists
- [`songs`](#list-songs-in-mp3-playlists): List songs in MP3 playlists
- [`junks`](#list-junk-songs): List "junk" songs in MP3 playlists
- [`tag`](#tag-junk-songs): Tag "junk" songs and set cover art
- [`untag`](#untag-songs): Remove tags and cover art or restaure them from YouTube ones
- [`visit`](#visit-songs-youtube-url): Visit song's YouTube URL in a browser
- [`play`](#play-mp3-files-from-playlists): Play MP3 files from imported playlists

**Note:** In the command usages described bellow, the term "INDEX" refers to the rank of an item in a list of songs or playlists resulting from a command; it therefore only make sense at the time the command is ran.


### Global options

These options are shared with all commands:
- `-r, --repo <path>`: Set the repository (folder) where playlists are stored (default: `~/Desktop/playlists`)
- `-h, --help`: Show help for a specific command


### Import songs from a YouTube playlist

```sh
pypl2mp3 import [options] <playlist>
```
- `playlist`: ID, URL or INDEX of a YouTube playlist (default: from `PYPL2MP3_DEFAULT_PLAYLIST_ID` env. var)
- `-f, --filter <expr>`: Filter songs using keywords
- `-m, --match <level>`: Minimum filter match level (0-100, default: 45)
- `-t, --thresh <level>`: Shazam match threshold (0-100, default: 50)
- `-p, --prompt`: Prompt to import each new song discovered in YouTube playlist


### List created MP3 playlists

```sh
pypl2mp3 playlists
```


### List songs in MP3 playlists

```sh
pypl2mp3 songs [options]
```
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <expr>`: Filter songs by filename using keywords
- `-m, --match <level>`: Minimum filter match level (0-100, default: 45)
- `-v, --verbose`: Enable verbose output


### List "junk" songs

```sh
pypl2mp3 junks [options]
```
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <expr>`: Filter songs by filename using keywords
- `-m, --match <level>`: Minimum filter match level (0-100, default: 45)
- `-v, --verbose`: Enable verbose output


### Tag "junk" songs

```sh
pypl2mp3 tag [options]
```
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <expr>`: Filter songs by filename using keywords
- `-m, --match <level>`: Minimum filter match level (0-100, default: 45)
- `-t, --thresh <level>`: Shazam match threshold (0-100, default: 50)
- `-p, --prompt`: Prompt to set ID3 tags and cover art for each song


### Untag songs

```sh
pypl2mp3 untag [options]
```
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <expr>`: Filter songs by filename using keywords
- `-m, --match <level>`: Minimum filter match level (0-100, default: 45)
- `-p, --prompt`: Prompt to removes ID3 tags and cover art from each song


### Visit song's YouTube URL
```sh
pypl2mp3 visit [options]
```
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-f, --filter <expr>`: Filter songs by filename using keywords
- `-m, --match <level>`: Minimum filter match level (0-100, default: 45)
- `-v, --verbose`: Enable verbose output


### Play MP3 files from playlists

```sh
pypl2mp3 play [options] [filter] [index]
```
- `filter`: Filter songs by filename using keywords
- `index`: INDEX of a song to play (0 for random song)
- `-l, --list <playlist>`: Specify a particular playlist by its ID, URL or INDEX
- `-m, --match <level>`: Minimum filter match level (0-100, default: 45)
- `-s, --shuffle`: Play songs in random order
- `-v, --verbose`: Enable verbose output

Once the player is running, you can use the following keyboard keys:
```
[  <--  ] Previous song / Play backward
[  -->  ] Next song / Play forward
[ SPACE ] Pause song / Play song
[  TAB  ] Open song's video in browser
[  ESC  ] Quit player
```

## Examples

### Import the best playlist of YouTube ;)

```sh
pypl2mp3 import PLP6XxNg42qDG3u8ldvEEtWC8q0p0BLJXJ
```


### List songs with filtering

```sh
pypl2mp3 songs -f "hendrix"
```


### Tag "junk" songs with a prompt

```sh
pypl2mp3 tag -p
```


### Play songs of band Dire Straits, in random order, from playlist #2

```sh
pypl2mp3 play -l 2 -s "dire straits"
```


## Troubleshooting

If you experiment some issues, notably when importing song (command `ìmport`) or adding ID3 tags to MP3 files (command `tag`), it is probably due to recent changes on YouTube side. In this case, try to update the `pytubefix` package to its latest version.

To do so, run the following command in your terminal from the root folder of this project:
```sh
poetry add pytubefix@latest
```