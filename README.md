# Transcription Prototype

A web application for transcribing and labeling speakers in long-form audio files (`.DCR` format).

## Architecture Overview

| Component        | Technology                        |
|------------------|-----------------------------------|
| **Web Framework** | Flask (MPA)                      |
| **Frontend**      | Bootstrap 5 + Jinja2 Templates   |
| **Async Jobs**    | Celery + Redis                   |
| **Storage**       | Azure Blob Storage               |
| **Audio Extraction** | `ffmpeg`                      |
| **Audio Chunking** | `pydub`, `webrtcvad`            |
| **STT Engine**    | Azure OpenAI Whisper (via Azure Speech Services) |
| **Speaker Diarization** | `pyannote-audio`           |
| **Transcription Stitching** | Custom logic in Python |
| **DB**            | SQLite (dev) → PostgreSQL (prod) |

## Setup and Installation

### Prerequisites

- Python 3.8+
- Redis server
- FFmpeg
- Azure account with:
  - Azure Blob Storage
  - Azure Speech Services

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/transcription-prototype.git
   cd transcription-prototype
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install PyAnnote (with special instructions):
   ```
   pip install pyannote.audio
   ```
   Note: You need to get access to [pyannote/speaker-diarization-3.0](https://huggingface.co/pyannote/speaker-diarization-3.0) on Hugging Face and generate an access token.

5. Create a `.env` file:
   ```
   cp .env.example .env
   ```
   Then edit `.env` with your settings.

6. Create necessary directories:
   ```
   mkdir -p uploads instance
   ```

## Running the Application

### Development Mode

1. Start Redis (if not already running):
   ```
   redis-server
   ```

2. Start the Flask application:
   ```
   python app.py
   ```

3. Start Celery worker in a separate terminal:
   ```
   celery -A celery_worker.celery worker --loglevel=info -P threads
   ```

### Production Mode

For production deployment, use Gunicorn:

```
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Start Celery worker with appropriate concurrency:

```
celery -A celery_worker.celery worker --loglevel=info -c 4
```

## App Features

- Upload `.DCR` files (up to 5GB)
- Extract audio and process with Azure Speech-to-Text
- Identify speakers using speaker diarization
- View timestamped, speaker-labeled transcripts with audio playback
- Download transcripts in JSON and TXT formats

## Workflow

1. User uploads a `.DCR` file
2. System extracts audio using FFmpeg
3. Audio is chunked into ~30s segments with 5s overlap
4. Chunks are transcribed with Azure Speech-to-Text
5. Diarization is performed on the full audio
6. Transcript segments are stitched together with speaker labels
7. Final transcript is saved and displayed to user
