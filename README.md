# Transcription Demo Application

A Flask-based web application for uploading, transcribing, and analyzing audio files with speaker diarization capabilities, powered by Azure Speech Services.

## Overview

This application provides a user-friendly interface for audio transcription with the following features:

- File upload handling with progress tracking
- Azure Blob Storage integration for file storage
- Asynchronous transcription processing using Celery
- Speaker diarization (identifying different speakers in audio)
- Interactive transcript viewer with synchronized audio playback
- Word-level confidence highlighting

## Technology Stack

- **Backend**: Flask, SQLAlchemy, Celery
- **Frontend**: Bootstrap 5, JavaScript, HTML/CSS
- **Storage**: Azure Blob Storage
- **Transcription**: Azure Speech Services
- **Task Queue**: Redis
- **Database**: SQLite (development), PostgreSQL (production)

## Project Structure

### Core Application Files

- `app.py` - Entry point for the Flask application
- `celery_worker.py` - Worker process for Celery task queue
- `config.py` - Configuration classes for different environments
- `run_debug.sh` - Shell script to start the application in debug mode
- `setup.py` - Python package definition and dependencies

### App Module

The `app/` directory contains the main application components:

#### Models

- `app/models/__init__.py` - Database initialization
- `app/models/file.py` - File model for tracking upload and transcription status

#### Routes

- `app/routes/files.py` - Handles file uploads and listing
- `app/routes/transcripts.py` - Serves transcript data and view
- `app/routes/main.py` - Main application routes

#### Services

- `app/services/batch_transcription_service.py` - Azure Speech Services API integration
- `app/services/blob_storage.py` - Azure Blob Storage integration

#### Tasks

- `app/tasks/transcription_tasks.py` - Celery task definitions for async processing
- `app/tasks/celery_app.py` - Celery application configuration

#### Templates

- `app/templates/base.html` - Base template with common layout
- `app/templates/file_detail.html` - File details view
- `app/templates/files.html` - File listing dashboard
- `app/templates/transcript.html` - Interactive transcript viewer
- `app/templates/upload.html` - File upload interface

#### Static Assets

- `app/static/css/style.css` - Custom CSS styles
- `app/static/js/main.js` - JavaScript functionality

## Key Features

### File Upload

The application supports large audio file uploads (up to 5GB) with real-time progress tracking. Files are first uploaded to the local server, then transferred to Azure Blob Storage for permanent storage.

### Transcription Pipeline

1. **Upload**: User uploads an audio file through the web interface
2. **Storage**: File is stored in Azure Blob Storage
3. **Processing**: Celery worker submits the file to Azure Speech Service
4. **Transcription**: Azure processes the audio for speech-to-text and speaker diarization
5. **Storage**: Resulting transcript is stored in Azure Blob Storage
6. **Presentation**: Interactive transcript is made available to the user

### Interactive Transcript Viewer

The transcript viewer provides:

- Synchronized audio playback with transcript highlighting
- Word-level confidence indicators (color-coded based on recognition confidence)
- Speaker identification with color-coded segments
- Clickable transcript for navigation
- Playback speed control
- Keyboard shortcuts for audio control

## Configuration

The application uses environment variables for configuration, stored in a `.env` file. An example configuration is provided in `.env.example`.

Key configuration options include:

- Azure Speech Services API credentials
- Azure Blob Storage connection details
- Database connection settings
- Redis connection for Celery

## Development Setup

1. Create and activate a virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables using `.env.example` as a template
4. Run the development server: `./run_debug.sh`

## Production Deployment

For production deployment, consider:

- Using gunicorn as the WSGI server
- Setting up a PostgreSQL database
- Configuring proper Azure permissions
- Setting up multiple Celery workers for transcription tasks
- Implementing proper authentication and user management