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

## Key Files and Their Roles

- **app.py**:  
  Initializes the Flask app by loading environment variables, setting the configuration, and starting the development server.

- **celery_worker.py**:  
  Sets up the Celery worker in the Flask app context to run asynchronous tasks such as file upload and transcription processing.

- **config.py**:  
  Contains configuration classes for different environments (development, production, testing) including settings for the database, Azure services, and Celery.

- **ingest.sh**:  
  A shell script for ingesting project files while excluding temporary and non-essential files.

- **requirements.txt**:  
  Lists all Python packages required by the application.

- **run_debug.sh**:  
  A Bash script to run the app in debug mode. It checks if Redis is running, starts the Celery worker, and then launches the Flask server.

- **setup.py**:  
  Provides packaging details to install the application along with its dependencies.

- **.env.example**:  
  A template for environment variables needed for running the application (e.g., secret keys, database URL, Azure credentials).

- **app/__init__.py**:  
  Creates the Flask application, loads the configuration, initializes extensions, and registers blueprints and Celery.

- **app/extensions.py**:  
  Sets up Flask extensions, most notably SQLAlchemy for ORM support.

- **app/models/file.py**:  
  Defines the `File` model that tracks uploaded audio files and stores metadata such as file name, status, and transcription details.

- **app/files/**:  
  Implements functionality related to file handling:
  - **routes.py**: Manages file-related endpoints (listing, detail view, starting transcription).
  - **uploads.py**: Handles the uploading of files to the server and initiating the asynchronous upload process.
  - **progress.py**: Provides endpoints for checking the progress of file uploads and tasks.

- **app/services/blob_storage.py**:  
  Implements methods for uploading files to and downloading files from Azure Blob Storage, including SAS URL generation.

- **app/services/batch_transcription_service.py**:  
  Encapsulates communication with Azure Speech Service’s Batch Transcription API for submitting jobs, polling for status, and fetching transcription results.

- **app/tasks/**:  
  Contains Celery tasks:
  - **transcription_tasks.py**: Orchestrates the end-to-end transcription process—from submitting the job to updating file status with the final transcript.
  - **upload_tasks.py**: Manages the Azure Blob Storage upload process, updates progress in Redis, and triggers transcription upon successful upload.

- **app/static/**:  
  Contains static assets (CSS and JavaScript) used for styling and client-side interactions across various pages (upload, file details, transcript viewer).

- **app/templates/**:  
  Provides Jinja2 templates for the web UI, including pages for uploading files, viewing file details and progress, and displaying transcripts.

- **app/transcripts/**:  
  Handles the viewing and processing of transcript data, including regenerating SAS URLs and formatting the transcript for display.

- **instance/app.db**:  
  The local SQLite database (or other configured database) that stores application data such as file metadata.

- **migrations/**:  
  Contains Alembic migration scripts for database schema evolution, ensuring consistency between the models and the database.

## Application Workflow

1. **File Upload**:  
   A user uploads an audio file through the web interface. The file is saved temporarily in the `uploads/` directory.

2. **Azure Blob Upload**:  
   A Celery task (from `upload_tasks.py`) uploads the file to Azure Blob Storage. Progress is tracked via Redis and updated on the client-side.

3. **Transcription Processing**:  
   Once the file is uploaded, another Celery task (from `transcription_tasks.py`) submits the file to Azure Speech Service for transcription. The application polls for job status until the transcription succeeds or fails.

4. **Viewing Results**:  
   When completed, the transcript (and additional metadata such as duration and speaker count) is stored and made available via the web interface. Users can view and download both the audio and the transcription JSON.

