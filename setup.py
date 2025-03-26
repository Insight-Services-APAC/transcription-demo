from setuptools import setup, find_packages

setup(
    name="transcription-demo",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flask>=2.3.3",
        "celery>=5.3.4",
        "redis>=5.0.1",
        "gunicorn>=21.2.0",
        "azure-storage-blob>=12.18.3",
        "azure-cognitiveservices-speech>=1.30.0",
        "pydub>=0.25.1",
        "webrtcvad>=2.0.10",
        "pyannote.audio>=3.0.1",
        "python-dotenv>=1.0.0",
        "flask-wtf>=1.2.1",
        "azure-identity>=1.14.1",
        "ffmpeg-python>=0.2.0",
        "numpy>=1.26.1",
        "scipy>=1.11.3",
        "sqlalchemy>=2.0.23",
        "psycopg2-binary>=2.9.9",
        "jinja2>=3.1.2",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "flake8",
            "black",
        ],
    },
    python_requires=">=3.8",
)
