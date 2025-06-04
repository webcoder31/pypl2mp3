# Technical Documentation

This section contains detailed technical information about PYPL2MP3, including its requirements, dependencies, and architectural design.

## Navigation

- [Requirements](requirements.md) - System and software requirements
- [Dependencies](dependencies.md) - External libraries and tools
- [Architecture](architecture.md) - System design and components
- [Coding style](coding-style.md) - Python coding style guidelines

## Technical Stack Overview

### Core Technology
- Language: Python ≥ 3.7
- Package Manager: UV
- Audio Processing: FFmpeg
- Authentication: BotGuard (POT Generation)

### Key Integrations
- YouTube: via pytubefix
- Audio Recognition: Shazam API
- Audio Processing: FFmpeg
- File System: Direct OS integration

### System Design
- Command-line interface
- Modular command structure
- File-based storage
- Event-driven audio player