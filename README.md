# NSWCC Transcription Demo

A web application for automated audio transcription with speaker recognition using Azure Speech Services. This application provides a user-friendly interface for uploading audio files, processing them with Azure's Speech-to-Text service, and viewing the resulting transcripts with synchronized audio playback.

## Overview

The NSWCC Transcription Demo is designed to streamline the process of converting speech to text, with particular emphasis on multi-speaker environments. It leverages Azure Cognitive Services for high-quality transcription and speaker diarization (identifying who said what).

The application features a complete user authentication system, file management, asynchronous processing, and a sophisticated transcript player that allows users to navigate through transcribed content while listening to the corresponding audio.

## Features

- **User Authentication & Authorization**
  - User registration with admin approval workflow
  - Role-based access control (admin/standard users)
  - Secure password management with temporary password flows

- **File Management**
  - Support for WAV and MP3 audio uploads (up to 5GB)
  - Drag-and-drop file upload with progress tracking
  - Browse and manage uploaded files

- **Transcription Processing**
  - Integration with Azure Speech Services for speech-to-text conversion
  - Speaker diarization to distinguish between different speakers
  - Multiple transcription model support with language locale options
  - Background processing with status tracking

- **Transcript Viewing**
  - Interactive transcript player with synchronized audio playback
  - Word-level highlighting and navigation
  - Speaker segmentation with visual differentiation
  - Confidence scoring for transcribed content

- **Administration**
  - User management dashboard for administrators
  - Create, approve, deactivate, and delete user accounts
  - Password reset functionality

## System Architecture

The application is built using a Flask backend with a Bootstrap-based frontend. It employs a celery worker for handling asynchronous tasks such as file uploads and transcription processing. Files are stored in Azure Blob Storage, and the transcription is performed via Azure Speech Services.

### Key Components

#### Backend (Python/Flask)

- **Flask Application**
  - `app.py`: Main application entry point
  - `config.py`: Configuration settings for different environments
  - `celery_worker.py`: Celery worker for background task processing

- **Application Modules**
  - `app/__init__.py`: Flask application factory
  - `app/extensions.py`: Flask extensions (SQLAlchemy, CSRFProtect, etc.)
  - `app/models/`: Database models for users and files
  - `app/admin/`: Admin panel functionality
  - `app/auth/`: Authentication and user management
  - `app/errors/`: Error handling and logging
  - `app/files/`: File upload and management
  - `app/transcripts/`: Transcript generation and viewing
  - `app/services/`: External service integrations (Azure Blob Storage, Azure Speech)
  - `app/tasks/`: Celery tasks for asynchronous processing

#### Frontend

- **Templates**
  - Base templates and layout in `app/templates/`
  - Feature-specific templates for auth, files, transcripts, etc.

- **Static Assets**
  - CSS: Style sheets for UI components
  - JavaScript:
    - `file-upload/`: Handling file uploads with progress tracking
    - `file-detail/`: File information display
    - `transcript-player/`: Interactive transcript player
    - `utils/`: Utility functions

#### External Services

- **Azure Blob Storage**: For storing uploaded audio files and generated transcripts
- **Azure Speech Services**: For speech-to-text processing and speaker diarization
- **Redis**: For Celery task queue and progress tracking
- **SQLite/PostgreSQL**: Database for storing application data

## Technology Stack

- **Backend**: Python 3, Flask, SQLAlchemy, Celery
- **Frontend**: HTML5, CSS, JavaScript, Bootstrap 5
- **Storage**: Azure Blob Storage, SQLite/PostgreSQL
- **Services**: Azure Speech Services (Batch Transcription API)
- **Infrastructure**: Redis for task queue

## Usage Flow

1. Users register and await admin approval
2. Once approved, users can upload audio files (MP3 or WAV)
3. Users can optionally select a specific transcription model
4. Files are uploaded to Azure Blob Storage
5. Transcription is processed asynchronously by Azure Speech Services
6. Users can monitor processing status on the file detail page
7. Once complete, users can view the transcript with synchronized audio playback
8. Transcript view shows speaker segments and word-level confidence

This application provides a complete end-to-end solution for speech transcription with a focus on usability, reliability, and accuracy.