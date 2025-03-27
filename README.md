# Transcription Demo Application

This project is a web-based transcription demo that enables users to upload audio files, process them asynchronously, and receive both transcriptions and speaker diarization results. It leverages Flask for the web interface, Celery for background task processing, and various Azure services (Blob Storage, Speech Services) to handle audio file storage and transcription. The application also includes features for tracking upload progress and real-time status updates.

## Overview

The Transcription Demo Application allows users to:
- **Upload Audio Files:** Supports common formats like MP3 and WAV (up to 5GB).
- **Process Files Asynchronously:** Uses Celery tasks to handle intensive operations such as audio extraction, transcription via Azure Speech Services, and speaker diarization.
- **Display Processing Status:** Provides real-time progress updates through a web dashboard.
- **View Transcripts:** Once processed, users can view the transcript with speaker labels and download both the audio and the JSON transcript.

## Key Features

- **Asynchronous Processing:** Heavy tasks like transcription are offloaded to Celery workers.
- **Azure Integration:** Utilizes Azure Blob Storage for file persistence and Azure Speech Services for batch transcription and speaker diarization.
- **Progress Monitoring:** Both local and Azure upload progress are tracked and displayed.
- **Audio Processing:** Includes functionality for audio extraction and chunking to prepare files for transcription.
- **Transcript Stitching:** Combines transcriptions from multiple audio chunks and applies speaker diarization for a coherent final transcript.

## Project Structure and Key Files

- **`app.py`**  
  The main entry point for the Flask application. It loads environment variables, creates the Flask app using the appropriate configuration, and runs the development server.

- **`celery_worker.py`**  
  Initializes the Flask application context for Celery, sets up the Celery worker, and ensures that the database session is ready for background tasks.

- **`config.py`**  
  Contains configuration classes for development, production, and testing. It includes settings for Flask, SQLAlchemy, Azure services, Celery, and file upload limits.

- **`ingest.sh`**  
  A helper script to ingest project files while excluding unnecessary directories and files (e.g., caches, tests).

- **`requirements.txt`**  
  Lists all the dependencies required for the project, including Flask, Celery, Azure SDKs, and other Python libraries.

- **`run_debug.sh`**  
  A shell script to run the application in debug mode. It checks for required services (e.g., Redis), starts the Celery worker, and then launches the Flask development server.

- **`setup.py`**  
  Provides packaging information and dependencies for installing the application as a Python package.

- **`.env.example`**  
  An example environment file that lists the necessary environment variables such as API keys, database URLs, and configuration settings.

- **`app/` Directory**  
  Contains the main application modules:
  - **`__init__.py`**  
    Initializes the Flask application, sets up the database, registers blueprints, and integrates the Celery instance.
  - **`models/`**  
    Contains SQLAlchemy model definitions (e.g., the `File` model) and database initialization logic.
  - **`routes/`**  
    Defines the application routes for uploading files, viewing files and transcripts, and API endpoints for progress updates.
  - **`services/`**  
    Provides service modules for:
    - **Audio Processing:** Extracting and chunking audio files.
    - **Blob Storage:** Handling file uploads/downloads to/from Azure Blob Storage.
    - **Batch Transcription:** Interfacing with Azure’s batch transcription API.
    - **Diarization:** Speaker identification using PyAnnote.
    - **Speech Service:** Transcribing audio files using Azure Speech Services.
    - **Transcript Stitching:** Merging and applying speaker labels to transcription segments.
  - **`tasks/`**  
    Contains Celery task definitions (e.g., the `transcribe_file` task) which orchestrate the transcription workflow.

- **`app/templates/`**  
  Contains Jinja2 HTML templates for rendering the web pages, including:
  - `base.html`: The base layout.
  - `upload.html`: The file upload page.
  - `files.html` and `file_detail.html`: Pages for listing and detailing uploaded files.
  - `transcript.html`: Page to view the final transcript.

- **`app/static/`**  
  Contains static assets:
  - **CSS:** Styling for the application interface.
  - **JavaScript:** Functionality for file upload progress, audio player controls, and transcript interaction.

- **`instance/app.db`**  
  The SQLite database file used for storing file records and processing metadata.

- **`uploads/`**  
  Directory where temporary file uploads are stored before being processed and uploaded to Azure Blob Storage.

## Setup and Running the Application

1. **Environment Setup:**  
   - Copy `.env.example` to `.env` and set the necessary environment variables (e.g., `AZURE_SPEECH_KEY`, `AZURE_STORAGE_CONNECTION_STRING`, etc.).
   - Install the dependencies using:
     ```bash
     pip install -r requirements.txt
     ```

2. **Database Initialization:**  
   The database is automatically initialized when the application starts. The `instance/app.db` file is created if it does not already exist.

3. **Running in Debug Mode:**  
   Use the provided shell script to start the application and the Celery worker in debug mode:
   ```bash
   ./run_debug.sh
   ```

4. **Accessing the Application:**  
   Open your browser and navigate to `http://0.0.0.0:5000/` to access the upload page and start using the application.

## Summary

This Transcription Demo Application provides an end-to-end solution for processing audio files with transcription and speaker diarization. Its modular design, integration with Azure services, and real-time progress tracking make it a robust demo project for applications requiring advanced audio processing and speech-to-text capabilities.
