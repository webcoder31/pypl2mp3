# Project Dependencies

This document details all dependencies required by PYPL2MP3, including Python packages, system tools, and external services.

## Core Python Dependencies

### Audio Processing & Metadata
- **mutagen** (≥1.47.0, <2)
  - Audio metadata reading and writing
  - ID3 tag management
  - File format support

- **moviepy** (≥1.0.3, <2)
  - Audio/video processing
  - Format conversion support
  - Integration with FFmpeg

### Audio Recognition & YouTube Integration
- **shazamio** (≥0.4.0, <0.5)
  - Shazam API integration
  - Song recognition
  - Metadata retrieval

- **pytubefix** (≥9.1.1, <10)
  - YouTube integration
  - Video information retrieval
  - Audio stream handling
  - POT (Proof of Origin Token) generation

### User Interface & Interaction
- **pygame** (≥2.6.0, <3)
  - Audio playback
  - Player controls
  - Event handling

- **colorama** (≥0.4.6, <0.5)
  - Cross-platform terminal colors
  - Output formatting

- **rich-argparse** (≥1.6.0, <2)
  - Enhanced command-line interface
  - Argument parsing
  - Help text formatting

- **sshkeyboard** (≥2.3.1, <3)
  - Keyboard input handling
  - Player controls
  - Interactive mode support

### Utility Libraries
- **python-slugify** (≥8.0.4, <9)
  - Text normalization
  - File name sanitization
  - URL-safe string generation

- **thefuzz** (≥0.22.1, <0.23)
  - Fuzzy string matching
  - Search functionality
  - Sort by relevance

- **proglog** (≥0.1.10, <0.2)
  - Progress logging
  - Operation status tracking
  - User feedback

## System Dependencies

### Audio Processing Tools
- **FFmpeg**
  - Audio conversion
  - Format handling
  - Stream processing
  
- **FFprobe**
  - Audio analysis
  - Metadata extraction
  - Format detection

### Runtime Dependencies
- **Node.js**
  - Required for pytubefix
  - POT generation
  - BotGuard functionality

## Build System
- **hatchling**
  - Project building
  - Package creation
  - Distribution management

## Python Environment
- Python ~= 3.11
- UV package manager

## External Services
1. **YouTube API**
   - Video information
   - Playlist management
   - Audio streams

2. **Shazam API**
   - Song recognition
   - Metadata retrieval
   - Cover art access