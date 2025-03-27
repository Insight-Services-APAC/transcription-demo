# NSWCC Transcription Demo

The NSWCC Transcription Demo is a Flask-based web application that allows users to upload audio files (MP3 or WAV), process them asynchronously, and generate transcriptions with speaker diarization using Azure Speech Services. The application leverages Celery for background task processing, Redis for progress tracking, and Azure Blob Storage to securely store audio files and transcription results.

## Overview

The application provides an intuitive interface for uploading audio files and monitoring the processing pipeline. Once an audio file is uploaded, it is temporarily stored locally and then transferred to Azure Blob Storage via a Celery task. The file is then submitted to the Azure Speech Service Batch Transcription API where the transcription is processed in the background. Users can view real-time upload progress and check on the status of the transcription. When complete, the transcribed text—along with speaker information—is available through the web interface.

## Key Features

- **File Upload**: Supports .MP3 and .WAV files (up to 5GB) with drag-and-drop functionality.
- **Asynchronous Processing**: Uses Celery to handle file uploads and transcription tasks in the background.
- **Progress Tracking**: Real-time monitoring of upload progress and transcription status via Redis and API endpoints.
- **Azure Integration**:
  - **Blob Storage**: Securely stores uploaded audio files and transcription results.
  - **Speech Services**: Converts speech to text and identifies speakers using Azure’s Batch Transcription API.
- **User Interface**: Provides a dashboard to view file statuses, detailed processing progress, and final transcript output.

## Directory Structure

```
transcription-demo/
├── app.py                   -> Main entry point that creates and runs the Flask app.
├── celery_worker.py         -> Initializes and configures the Celery worker for asynchronous tasks.
├── config.py                -> Application configuration (database URI, Azure credentials, Celery settings, etc.).
├── ingest.sh                -> Script for code ingestion, excluding unnecessary files.
├── requirements.txt         -> List of Python dependencies.
├── run_debug.sh             -> Debug run script; checks for Redis and starts both Celery and the Flask server.
├── setup.py                 -> Setup script for packaging the application.
├── .env.example             -> Example file for environment variable configuration.
├── app/                     -> Main application package.
│   ├── __init__.py          -> Initializes the Flask app, registers blueprints, and sets up Celery.
│   ├── extensions.py        -> Initializes Flask extensions (e.g., SQLAlchemy).
│   ├── files/               -> Contains file management features:
│   │   ├── routes.py        -> Routes for file dashboard, details, and API endpoints.
│   │   ├── uploads.py       -> Handles file upload and storage operations.
│   │   └── progress.py      -> Provides endpoints to check upload progress.
│   ├── main/                -> Contains core routes (e.g., index redirection and health checks).
│   ├── models/              -> Contains database models (e.g., the File model).
│   ├── services/            -> Implements services to interact with external APIs:
│   │   ├── blob_storage.py  -> Manages file uploads to and downloads from Azure Blob Storage.
│   │   └── batch_transcription_service.py -> Integrates with Azure Speech Service for transcription.
│   ├── tasks/               -> Contains Celery tasks for asynchronous processing:
│   │   ├── transcription_tasks.py -> Orchestrates the transcription pipeline.
│   │   └── upload_tasks.py  -> Handles file uploads and triggers transcription.
│   ├── static/              -> Contains CSS and JavaScript assets for the UI.
│   ├── templates/           -> Jinja2 templates for rendering web pages.
│   └── transcripts/         -> Contains routes and logic for viewing and processing transcription results.
├── instance/                -> Contains instance-specific files (e.g., the SQLite database).
├── migrations/              -> Alembic migration scripts for managing database schema changes.
└── uploads/                 -> Temporary storage for uploaded audio files.
```
## Application Workflow

1. **File Upload**:  
   A user uploads an audio file through the web interface. The file is saved temporarily in the `uploads/` directory.

2. **Azure Blob Upload**:  
   A Celery task (from `upload_tasks.py`) uploads the file to Azure Blob Storage. Progress is tracked via Redis and updated on the client-side.

3. **Transcription Processing**:  
   Once the file is uploaded, another Celery task (from `transcription_tasks.py`) submits the file to Azure Speech Service for transcription. The application polls for job status until the transcription succeeds or fails.

4. **Viewing Results**:  
   When completed, the transcript (and additional metadata such as duration and speaker count) is stored and made available via the web interface. Users can view and download both the audio and the transcription JSON.

