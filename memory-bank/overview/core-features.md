# Core Features

## Primary Capabilities

1. **YouTube Playlist Integration**
   - Import complete playlists as MP3 files
   - Support for public playlists
   - Automatic handling of new playlist additions
   - Flexible playlist identification via ID, URL, or INDEX

2. **Audio Processing**
   - MP3 format conversion
   - Shazam integration for song recognition
   - Automatic ID3 tag management
   - Cover art handling
   - Configurable match thresholds for Shazam recognition

3. **Metadata Management**
   - Automatic file naming based on artist and title
   - Batch metadata cleanup and restoration
   - Interactive prompt mode for manual metadata verification
   - "Junk" handling system for unmatched songs

4. **Search and Organization**
   - Fuzzy search across all playlists
   - Configurable match thresholds for searches
   - Sort capabilities by relevance
   - Playlist-specific filtering

5. **Playback and Interaction**
   - Built-in MP3 player with controls
   - Quick access to YouTube videos
   - Shuffle play functionality
   - Playlist navigation controls

6. **User Experience**
   - Command-line interface with consistent options
   - Verbose error reporting and debugging
   - Progress tracking for operations
   - Configurable repository locations
   - No database requirements

## Integration Features

- FFmpeg integration for audio processing
- Shazam API integration for song recognition
- YouTube API integration via pytubefix
- File system integration for MP3 management

## Command Structure

All features are accessible through a unified command structure with consistent options:
- Global repository configuration
- Debug levels
- Filter capabilities
- Match thresholds
- Verbose output options