# Setting Up the Transcription Demo Application

This guide will walk you through setting up the transcription demo application in a local development environment. The application allows users to upload, transcribe, and analyze DCR audio files with speaker diarization.

## Prerequisites

Before getting started, ensure you have the following installed:

- Python 3.8 or higher
- Redis server
- FFmpeg
- Git (for cloning the repository)
- Azure account with the following services:
  - Azure Blob Storage (for file storage)
  - Azure Speech Services (for speech-to-text)
- Hugging Face account with access to PyAnnote models

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/transcription-demo.git
cd transcription-demo
```

## Step 2: Set Up a Virtual Environment

Create and activate a Python virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# For Windows:
venv\Scripts\activate
# For macOS/Linux:
source venv/bin/activate
```

## Step 3: Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### Special Installation for PyAnnote

PyAnnote requires special installation steps:

1. First, obtain access to the [pyannote/speaker-diarization-3.0](https://huggingface.co/pyannote/speaker-diarization-3.0) model on Hugging Face:
   - Visit the model page and request access
   - Generate a Hugging Face access token in your account settings

2. Install PyAnnote:
   ```bash
   pip install pyannote.audio
   ```

## Step 4: Set Up Azure Services

### Azure Blob Storage
1. Create an Azure Blob Storage account in the Azure portal
2. Create a container named `transcriptions` (or your preferred name)
3. Note your connection string from the "Access keys" section

### Azure Speech Services
1. Create an Azure Speech Services resource in the Azure portal
2. Note your Speech API key and region

## Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration details:

```
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secure-secret-key-for-development

# Database Configuration
DATABASE_URL=sqlite:///instance/app.db

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your-azure-storage-connection-string
AZURE_STORAGE_CONTAINER=transcriptions

# Azure Speech Services
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=eastus

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Audio Processing
CHUNK_SIZE_SECONDS=30
CHUNK_OVERLAP_SECONDS=5

# PyAnnote Configuration
PYANNOTE_AUTH_TOKEN=your-huggingface-access-token

# Upload Directory
UPLOAD_FOLDER=uploads
```

## Step 6: Create Required Directories

Ensure the necessary directories exist:

```bash
mkdir -p uploads instance
```

## Step 7: Start Redis Server

Start Redis server, which is required for Celery:

```bash
# On most systems:
redis-server

# On Windows using WSL or alternative methods
# On macOS with Homebrew:
brew services start redis
```

## Step 8: Initialize the Database

The application will automatically create the database on first run, but you can initialize it manually:

```bash
python -c "from app import create_app; from app.models import init_db; app = create_app('development'); init_db(app)"
```

## Step 9: Start the Application

### Start the Celery Worker

Open a new terminal, activate your virtual environment, and start the Celery worker:

```bash
# Activate the virtual environment first
# For Windows:
venv\Scripts\activate
# For macOS/Linux:
source venv/bin/activate

# Then start Celery worker
celery -A celery_worker.celery worker --loglevel=info -P threads
```

### Start the Flask Development Server

In another terminal with the virtual environment activated:

```bash
python app.py
```

The application should now be running at [http://localhost:5000](http://localhost:5000).

## Step 10: Using the Application

1. Access the application at [http://localhost:5000](http://localhost:5000)
2. Upload a DCR file through the upload interface
3. View your uploaded files in the Files dashboard
4. Start the transcription process for a file
5. Once processing is complete, view the transcript with speaker labels

## Troubleshooting

### FFmpeg Issues
- Ensure FFmpeg is properly installed and available in your PATH
- On Windows, download the FFmpeg executable and add it to your system PATH
- On macOS: `brew install ffmpeg`
- On Ubuntu: `sudo apt install ffmpeg`

### Redis Connection Issues
- Verify Redis is running: `redis-cli ping` should return `PONG`
- Check the Redis connection URL in your `.env` file

### PyAnnote Installation Problems
- Ensure you have the correct access token from Hugging Face
- PyAnnote requires specific versions of PyTorch - check compatibility

### Azure Services
- Verify your Azure credentials and connection strings
- Ensure your Azure services have the correct permissions
- Check the Azure region is correctly specified

## Running Tests

To run the automated tests:

```bash
./run_tests.sh
```

Or manually:

```bash
export FLASK_ENV=testing
export PYTHONPATH=$(pwd)
cp tests/.env.test .env.test
DOTENV_PATH=.env.test pytest --cov=app tests/ -v
```

## Production Deployment Considerations

For production deployment:

1. Use a production-grade web server:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. Run Celery with appropriate concurrency:
   ```bash
   celery -A celery_worker.celery worker --loglevel=info -c 4
   ```

3. Use PostgreSQL instead of SQLite:
   - Update `DATABASE_URL` in your `.env` file
   - Install psycopg2-binary if not already installed

4. Consider using a process manager like Supervisor to manage the processes

5. Set up proper logging and monitoring

6. Configure HTTPS with a valid SSL certificate