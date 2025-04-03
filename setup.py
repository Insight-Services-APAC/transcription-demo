from setuptools import setup, find_packages

setup(
    name="transcription-demo",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask==3.1.0",
        "celery==5.4.0",
        "redis==5.2.1",
        "gunicorn==23.0.0",
        "azure-storage-blob==12.25.0",
        "azure-cognitiveservices-speech>=1.30.0",
        "pydub>=0.25.1",
        "webrtcvad>=2.0.10",
        "pyannote.audio>=3.0.1",
        "python-dotenv==1.1.0",
        "Flask-WTF==1.2.2",
        "azure-identity==1.21.0",
        "ffmpeg-python>=0.2.0",
        "numpy==1.26.1",
        "scipy==1.11.3",
        "SQLAlchemy==2.0.39",
        "psycopg2-binary==2.9.10",
        "Jinja2==3.1.6",
        "Flask-SQLAlchemy==3.1.1",
        "Flask-Migrate==4.1.0",
        "requests==2.32.3",
        "gitingest==0.1.4",
    ],
    extras_require={
        "dev": ["pytest", "pytest-cov", "flake8", "black", "alembic==1.15.1"]
    },
    python_requires=">=3.8",
)
