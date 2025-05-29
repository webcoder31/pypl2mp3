# Project Limitations

This document outlines the current limitations and constraints of PYPL2MP3. Understanding these limitations helps set appropriate expectations and identify potential areas for future improvement.

## Access Limitations

1. **Playlist Accessibility**
   - Only public YouTube playlists can be imported
   - Private and unlisted playlists are not supported
   - Region-restricted videos are excluded from import process

2. **Content Restrictions**
   - Age-restricted videos cannot be processed
   - Failed age-restricted imports don't block other imports
   - Some videos may require Proof of Origin Token (POT)

## Technical Limitations

1. **Dependencies**
   - Requires Python ≥ 3.7
   - Relies on external tools (ffmpeg, ffprobe)
   - Node.js requirement for POT generation

2. **System Integration**
   - Command-line interface only
   - No graphical user interface
   - Local filesystem-based storage

## Processing Limitations

1. **Audio Recognition**
   - Shazam matching may not recognize all songs
   - Match quality depends on audio clarity
   - Some songs may require manual metadata entry

2. **Performance**
   - One-at-a-time processing of playlist items
   - Network-dependent download speeds
   - Local processing capacity affects conversion speed

## Future Considerations

These limitations could potentially be addressed in future updates:
- Support for private/unlisted playlists (with authentication)
- Handling of age-restricted content
- Parallel processing of playlist items
- GUI interface option
- Alternative audio recognition services
- Cross-platform testing and validation

## Workarounds

For current limitations, several workarounds are available:
1. Use public playlist URLs when possible
2. Utilize the manual metadata entry option for unrecognized songs
3. Configure match thresholds for more permissive recognition
4. Implement proper error handling in scripts that use this tool