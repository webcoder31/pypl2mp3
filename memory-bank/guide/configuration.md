# Configuration Guide

This document details all configuration options and customization possibilities for PYPL2MP3.

## Environment Variables

### Core Settings
```sh
# Repository Path
PYPL2MP3_DEFAULT_REPOSITORY_PATH="/path/to/repository"

# Default Playlist
PYPL2MP3_DEFAULT_PLAYLIST_ID="playlistID"
```

### Configuration Priority
1. Command-line arguments
2. Environment variables
3. Default values

## Command-Line Options

### Global Options
```sh
# Repository Location
-r, --repo <path>

# Debug Levels
-d, --debug        # Enable verbose errors and logging
-D, --deep         # Enable deep debug with stack trace
```

### Command-Specific Options

#### 1. Import Options
```sh
# Match Thresholds
-t, --thresh <percent>  # Shazam match threshold (default: 50)
-m, --match <percent>   # Filter match threshold (default: 45)

# Operation Mode
-p, --prompt           # Interactive mode
-f, --filter <string>  # Filter criteria
```

#### 2. List Options
```sh
# Playlist Selection
-l, --list <playlist>  # Specific playlist

# Display Options
-v, --verbose         # Detailed output
-f, --filter <string> # Search filter
```

#### 3. Play Options
```sh
# Playback Control
-s, --shuffle        # Random playback
-l, --list <playlist> # Playlist selection
index                # Specific song
```

## Thresholds and Matching

### 1. Shazam Recognition
```sh
# Conservative Recognition
pypl2mp3 import -t 75  # High confidence

# Permissive Recognition
pypl2mp3 import -t 40  # More matches, less accuracy
```

### 2. Search Matching
```sh
# Strict Matching
pypl2mp3 songs -m 80  # Close matches only

# Fuzzy Matching
pypl2mp3 songs -m 30  # More results, less precise
```

## File Organization

### Default Structure
```
~/pypl2mp3/
├── playlist_id_1/
│   ├── song1.mp3
│   └── song2.mp3
└── pypl2mp3.log
```

### Custom Structure
```sh
# Set custom base path
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="/music/youtube/playlists"

# Use alternate location for session
pypl2mp3 -r "/alternate/path" <command>
```

## Debug Configuration

### 1. Log Levels
```sh
# Basic Debug
pypl2mp3 -d <command>
# Results in:
# - Verbose console errors
# - Basic logging to file

# Deep Debug
pypl2mp3 -D <command>
# Results in:
# - Full stack traces
# - Detailed logging
# - API response logging
```

### 2. Log File
- Location: `<repository_path>/pypl2mp3.log`
- Format: Timestamped entries
- Content: Operations, errors, API calls

## Performance Tuning

### 1. Download Settings
- Chunk size: 1.12 MB
- Rate limiting: Auto-managed
- Retry logic: Built-in

### 2. Recognition Settings
```sh
# Balance between speed and accuracy
pypl2mp3 import -t 50  # Default

# Prioritize accuracy
pypl2mp3 import -t 70 -p

# Prioritize recognition rate
pypl2mp3 import -t 30
```

## Shell Integration

### 1. Bash/Zsh Configuration
```sh
# Add to ~/.bashrc or ~/.zshrc
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="/your/path"
export PYPL2MP3_DEFAULT_PLAYLIST_ID="favorite_playlist"

# Optional aliases
alias yt2mp3='pypl2mp3 import'
alias ytplay='pypl2mp3 play'
```

### 2. Shell Wrapper
```sh
# Using provided wrapper
sh /path/to/pypl2mp3.sh <command>
```

## Best Practices

### 1. Repository Management
- Use consistent paths
- Maintain single repository
- Regular backups
- Periodic cleanup

### 2. Performance Optimization
- Appropriate match thresholds
- Batch operations
- Regular maintenance

### 3. Error Handling
- Enable debug for issues
- Check logs first
- Maintain clean repository

## Configuration Examples

### 1. Production Setup
```sh
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="/media/music/youtube"
export PYPL2MP3_DEFAULT_PLAYLIST_ID="main_playlist"
```

### 2. Development Setup
```sh
export PYPL2MP3_DEFAULT_REPOSITORY_PATH="./test_repo"
pypl2mp3 -d -D <command>  # Full debugging
```

### 3. Custom Setup
```sh
# High quality focus
pypl2mp3 import -t 75 -p  # Strict matching, interactive
pypl2mp3 fix -t 70       # Strict fixing
```

## Maintenance

### 1. Log Rotation
- Regular check of log size
- Archive old logs
- Clean up temporary files

### 2. Cache Management
- Clear temporary files
- Verify file integrity
- Check storage usage

### 3. Updates
```sh
# Update dependencies
uv lock --upgrade

# Verify configuration
pypl2mp3 --help