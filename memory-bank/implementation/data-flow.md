# Data Flow Documentation

This document details how data flows through the PYPL2MP3 system, including file operations, API interactions, and state transformations.

## Main Data Flows

### 1. Playlist Import Flow

```mermaid
graph TD
    A[User Command] -->|Import| B[Fetch Playlist]
    B -->|YouTube API| C[Video List]
    C -->|For Each Video| D[Download Audio]
    D -->|FFmpeg| E[Convert to MP3]
    E -->|Shazam API| F[Get Metadata]
    F -->|Match Check| G{Match Quality}
    G -->|Good Match| H[Tag MP3]
    G -->|Poor Match| I[Mark as Junk]
    H --> J[Save to Repository]
    I --> J
```

### 2. Metadata Processing

```mermaid
sequenceDiagram
    participant U as User
    participant C as Command
    participant S as Song Model
    participant A as APIs
    participant F as Filesystem

    U->>C: Fix Command
    C->>S: Load Song
    S->>A: Shazam Recognition
    A-->>S: Metadata
    S->>S: Match Analysis
    S->>F: Update Tags
    S->>F: Rename File
    F-->>U: Confirmation
```

## File Operations

### 1. Song Creation Path
```
YouTube Video
  ↓
Audio Stream (m4a)
  ↓
Temporary Storage
  ↓
FFmpeg Conversion
  ↓
MP3 with ID3 Tags
  ↓
Final Repository
```

### 2. File Naming Convention
```
Regular: ARTIST - TITLE [VIDEO_ID].mp3
Junk:   ARTIST - TITLE [VIDEO_ID] (JUNK).mp3
```

## State Management

### 1. Song State Transitions
```mermaid
stateDiagram-v2
    [*] --> Downloaded: Download Audio
    Downloaded --> Converting: FFmpeg Process
    Converting --> Converted: MP3 Created
    Converted --> Analyzing: Shazam Check
    Analyzing --> Tagged: Good Match
    Analyzing --> Junked: Poor Match
    Tagged --> [*]: Complete
    Junked --> [*]: Complete
```

### 2. Metadata Flow
```mermaid
graph LR
    A[YouTube Data] -->|Initial| B[Song Object]
    C[Shazam Data] -->|Recognition| B
    B -->|Verification| D{Match Quality}
    D -->|Good| E[Full Tags]
    D -->|Poor| F[Basic Tags]
```

## API Interactions

### 1. YouTube Integration
- Playlist information retrieval
- Video metadata fetching
- Audio stream download
- Rate limiting compliance

### 2. Shazam Integration
```mermaid
sequenceDiagram
    Song->>Shazam: Submit Audio
    Shazam-->>Song: Recognition Data
    Song->>Song: Calculate Match
    Song->>Song: Update State
```

## Progress Tracking

### 1. Operation Progress
```mermaid
graph TD
    A[Command Start] --> B[Download Progress]
    B --> C[Conversion Progress]
    C --> D[Recognition Progress]
    D --> E[Command Complete]
```

### 2. Progress Reporting
```
Download:  [■■■■■■····] 60%
Convert:   [■■■■■■■■··] 80%
Recognize: [■■■■■■■■■■] 100%
```

## Error Handling Flow

```mermaid
graph TD
    A[Operation] -->|Error| B{Error Type}
    B -->|Network| C[Retry Logic]
    B -->|File System| D[Cleanup & Retry]
    B -->|API| E[Rate Limit Check]
    C --> F[User Notification]
    D --> F
    E --> F
```

## Data Storage

### 1. Repository Structure
```
repository/
├── playlist_id/
│   ├── metadata/
│   │   └── playlist_info.json
│   └── songs/
│       ├── song1.mp3
│       └── song2.mp3
└── logs/
    └── pypl2mp3.log
```

### 2. Metadata Storage
- ID3v2.3 tags
- Custom TXXX fields
- Cover art embedding

## Cache Management

### 1. Temporary Storage
```mermaid
graph TD
    A[Download] -->|Temp| B[Process]
    B -->|Complete| C[Cleanup]
    B -->|Error| C
```

### 2. Resource Cleanup
- Automatic temporary file removal
- Failed download cleanup
- Incomplete conversion cleanup

## Command Results

### 1. Success Path
```mermaid
graph LR
    A[Command] -->|Execute| B[Operation]
    B -->|Success| C[Update State]
    C -->|Complete| D[Report]
```

### 2. Failure Path
```mermaid
graph LR
    A[Command] -->|Execute| B[Operation]
    B -->|Fail| C[Error Handler]
    C -->|Retry| B
    C -->|Give Up| D[Error Report]