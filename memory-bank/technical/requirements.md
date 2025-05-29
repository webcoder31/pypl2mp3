# System Requirements

This document outlines all requirements needed to run PYPL2MP3 successfully.

## Core Requirements

### Python Environment
- Python version ≥ 3.7
- UV package manager for dependency management
- Virtual environment support

### External Tools

1. **FFmpeg Tools**
   - `ffmpeg` for audio conversion
   - `ffprobe` for audio analysis
   - Must be installed and accessible in system PATH

2. **Node.js**
   - Required for Proof of Origin Token (POT) generation
   - Used by pytubefix version ≥ 8.12
   - BotGuard integration dependency

## System Resources

### Storage
- Sufficient disk space for:
  - Downloaded MP3 files
  - Temporary conversion files
  - Project files and dependencies
  - Log files (if debugging enabled)

### Network
- Active internet connection
- Access to:
  - YouTube servers
  - Shazam API
  - Cover art sources

### Memory
- Sufficient RAM for:
  - Audio processing
  - File conversion
  - Metadata management
  - Playlist handling

## Operating System Support

### Compatible Systems
- Linux
- macOS
- Windows
- Any OS supporting Python ≥ 3.7 and FFmpeg

### File System Requirements
- Read/Write permissions in:
  - Repository directory
  - Temporary directory
  - Program directory

## Optional Components

### Environment Variables
- `PYPL2MP3_DEFAULT_REPOSITORY_PATH`
  - Custom storage location
  - Must have write permissions
- `PYPL2MP3_DEFAULT_PLAYLIST_ID`
  - Default YouTube playlist
  - Must be publicly accessible

### Debug Support
- Log file write permissions
- Terminal with ANSI color support
- Sufficient storage for debug logs

## Installation Requirements

### Package Manager
- UV installed and configured
- Access to PyPI or alternative package source
- Permission to install Python packages

### System Configuration
- PATH environment properly configured
- Audio playback capability
- Browser available for video links