# JavaScript Architecture

This directory contains the JavaScript code for the NSWCC Transcription Demo application.

## Directory Structure

```
app/static/js/
├── components/               # Shared components
├── file-detail/              # File detail page specific code
│   ├── components/           # File detail components
│   ├── services/             # File detail services
│   └── index.js              # Main file detail controller
├── file-progress/            # File list page specific code
│   ├── components/           # File progress components
│   ├── services/             # File progress services
│   └── index.js              # Main file progress controller
├── transcript-player/        # Transcript player specific code
│   ├── components/           # Transcript player components
│   ├── services/             # Transcript player services
│   └── index.js              # Main transcript player controller
├── file-upload/              # File upload specific code
│   ├── components/           # File upload components
│   ├── services/             # File upload services
│   └── index.js              # Main file upload controller
└── utils/                    # Utility functions
```

## Architecture

The JavaScript code follows a component-based architecture where:

1. Each major feature has its own directory (file-upload, transcript-player, etc.)
2. Each feature is implemented with a main controller class in `index.js`
3. UI components are in the `components/` directory
4. Services for data fetching and processing are in the `services/` directory
5. Common utilities are shared across features

## Key Components

### File Upload
- `FileUploadApp`: Main controller for the upload page
- `FileUploadUIManager`: Manages the UI for file selection and progress display
- `FileUploadManager`: Handles the actual file upload process
- `UploadProgressTracker`: Tracks upload progress and updates the UI

### Transcript Player
- `TranscriptPlayerApp`: Main controller for the transcript player
- `AudioPlayerComponent`: Controls audio playback and timing
- `TranscriptRendererComponent`: Renders the transcript and handles highlighting
- `AudioTranscriptSynchronizer`: Synchronizes audio with transcript segments
- `EventBindingsManager`: Manages event listeners for user interactions

### File Progress
- `FileProgressApp`: Main controller for the files list page
- `ProgressManager`: Manages file progress state and UI updates
- `FilePollingService`: Polls for file status updates

### File Detail
- `FileDetailApp`: Main controller for the file detail page
- `FileDetailView`: Manages the file detail UI
- `DetailPollingService`: Polls for file detail status updates

## Utilities

- `formatters.js`: Utility functions for formatting values (file size, time, etc.)
- `dom-helpers.js`: Helper functions for DOM manipulation
- `api-service.js`: Utilities for making API requests
