# Audio Transcription Application

A robust Flask-based web application for transcribing audio files using Azure Speech Services, with speaker diarization capabilities to identify different speakers within recordings.

## Overview

This application provides a complete end-to-end solution for audio transcription:

- **User Authentication**: Secure registration and login system
- **File Upload**: Support for MP3 and WAV audio files up to 5GB
- **Asynchronous Processing**: Background task handling using Celery and Redis
- **Cloud Storage**: Azure Blob Storage for reliable file management
- **Speech Recognition**: Azure Speech Services for accurate transcription
- **Speaker Diarization**: Automatic identification of different speakers
- **Interactive Transcript Viewer**: Synchronized audio playback with transcript highlighting

## Key Features

- User account management with secure authentication
- Drag-and-drop file uploading with progress tracking
- Real-time processing status updates
- Interactive transcript viewer with synchronized audio playback
- Word-level timestamp navigation and confidence scoring
- Multi-speaker identification and highlighting
- Responsive web design for desktop and mobile use

## Project Structure

### Core Components

- **app.py**: Main application entry point
- **celery_worker.py**: Background task worker initialization
- **config.py**: Configuration settings for different environments (dev, production, testing)

### Application Modules

#### Auth Module
- **auth/routes.py**: Login, registration, and profile management
- **auth/forms.py**: Form validation for authentication 
- **models/user.py**: User account data model

#### Files Module
- **files/routes.py**: File management endpoints
- **files/uploads.py**: File upload handling
- **files/progress.py**: Upload progress tracking
- **models/file.py**: File metadata and status model

#### Transcription Pipeline
- **services/batch_transcription_service.py**: Azure Speech Service integration
- **services/blob_storage.py**: Azure Blob Storage integration
- **tasks/transcription_tasks.py**: Asynchronous transcription processing
- **tasks/upload_tasks.py**: Background file upload handling
- **transcripts/routes.py**: Transcript viewing and processing

#### Error Handling
- **errors/handlers.py**: Centralized error handling
- **errors/exceptions.py**: Custom exception definitions
- **errors/logger.py**: Structured logging
- **errors/middleware.py**: Request processing middleware

### Frontend Interface

- **templates/**: HTML templates for all views
- **static/css/**: Stylesheets for the application
- **static/js/**: JavaScript modules with component-based architecture
  - **file-upload/**: Upload management components
  - **file-progress/**: Progress tracking components
  - **transcript-player/**: Interactive transcript player
  - **utils/**: Shared utility functions

## Technical Details

The application is built with:

- **Flask**: Web framework
- **SQLAlchemy**: Database ORM
- **Celery**: Distributed task queue
- **Redis**: Message broker and caching
- **Azure Speech API**: Transcription service
- **Azure Blob Storage**: File storage
- **Bootstrap 5**: Frontend styling
- **Modern JavaScript**: Component-based architecture

## Getting Started

### Prerequisites

- Python 3.8+
- Redis server
- Azure account with:
  - Azure Speech Services subscription
  - Azure Blob Storage account

### Environment Variables

The application requires the following environment variables:

```
FLASK_ENV=development
SECRET_KEY=your-secret-key
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_SPEECH_KEY=your-speech-api-key
AZURE_SPEECH_REGION=eastus
```

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Initialize the database:
   ```
   flask db upgrade
   ```
4. Start Redis server
5. Run the debug server:
   ```
   ./run_debug.sh
   ```

## Usage Flow

1. Register for a new account or login
2. Upload an audio file (MP3 or WAV)
3. The file will be uploaded to Azure Blob Storage
4. Azure Speech Service will process the file for transcription
5. Once complete, view the interactive transcript with the audio player
6. Navigate through the transcript by clicking on sections or individual words