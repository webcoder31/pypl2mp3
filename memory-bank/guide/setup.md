# Setup Guide

This guide walks through the process of installing and configuring PYPL2MP3.

## Prerequisites

### Required Software
1. **Python ≥ 3.7**
   - Required for core functionality
   - Python 3.11 recommended

2. **UV Package Manager**
   - Required for dependency management
   - [Installation guide](https://docs.astral.sh/uv/)

3. **FFmpeg Tools**
   ```sh
   # macOS (using Homebrew)
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt-get install ffmpeg

   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

4. **Node.js**
   - Required for YouTube POT generation
   - [Download from nodejs.org](https://nodejs.org/)

## Installation

1. **Clone Repository**
   ```sh
   git clone https://github.com/webcoder31/pypl2mp3.git
   cd pypl2mp3
   ```

2. **Install Dependencies**
   ```sh
   uv sync
   ```

3. **Verify Installation**
   ```sh
   pypl2mp3 --help
   ```

## Configuration

### Environment Variables

1. **Repository Location**
   ```sh
   # Set custom storage location
   export PYPL2MP3_DEFAULT_REPOSITORY_PATH="/your/custom/path"
   ```

2. **Default Playlist**
   ```sh
   # Set favorite playlist ID
   export PYPL2MP3_DEFAULT_PLAYLIST_ID="yourPlaylistID"
   ```

### Persistence

Add to your shell configuration (~/.bashrc, ~/.zshrc):
```sh
# PYPL2MP3 Configuration
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="/your/custom/path"
export PYPL2MP3_DEFAULT_PLAYLIST_ID="yourPlaylistID"
```

## Directory Structure

```
~/pypl2mp3/              # Default repository
├── playlist_id_1/       # Playlist directories
│   ├── song1.mp3
│   └── song2.mp3
├── playlist_id_2/
│   └── ...
└── pypl2mp3.log        # Debug log file
```

## System Requirements

### Storage
- Sufficient space for MP3 files
- Write permissions in repository path
- Temporary storage for conversions

### Network
- Active internet connection
- Access to YouTube and Shazam
- Stable bandwidth for downloads

### Memory
- Minimum 2GB RAM recommended
- Additional space for audio processing

## Verification Steps

1. **Check Dependencies**
   ```sh
   # Verify FFmpeg
   ffmpeg -version
   ffprobe -version

   # Verify Node.js
   node --version

   # Verify Python
   python --version
   ```

2. **Test Repository Access**
   ```sh
   # Create test directory
   mkdir -p "$PYPL2MP3_DEFAULT_REPOSITORY_PATH"
   
   # Verify write permissions
   touch "$PYPL2MP3_DEFAULT_REPOSITORY_PATH/test.txt"
   rm "$PYPL2MP3_DEFAULT_REPOSITORY_PATH/test.txt"
   ```

3. **Test Basic Functionality**
   ```sh
   # List commands
   pypl2mp3 --help

   # Test playlist listing
   pypl2mp3 playlists
   ```

## Troubleshooting

### Common Issues

1. **FFmpeg Not Found**
   - Verify installation
   - Check PATH environment
   - Reinstall if necessary

2. **Permission Errors**
   ```sh
   # Fix repository permissions
   chmod -R u+rw "$PYPL2MP3_DEFAULT_REPOSITORY_PATH"
   ```

3. **YouTube API Issues**
   ```sh
   # Update pytubefix
   uv lock --upgrade-package pytubefix
   ```

### Debug Mode

Enable detailed logging:
```sh
pypl2mp3 -d <command>  # Basic debug
pypl2mp3 -D <command>  # Deep debug
```

## Updates

Keep dependencies up to date:
```sh
uv lock --upgrade  # Update all packages
```

## Next Steps

1. [Usage Examples](examples.md)
2. [Configuration Options](configuration.md)
3. Try basic commands:
   ```sh
   pypl2mp3 import <playlist_url>
   pypl2mp3 songs
   pypl2mp3 play