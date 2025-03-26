import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class File(Base):
    __tablename__ = 'files'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='uploaded')  # uploaded, processing, completed, error
    error_message = Column(Text, nullable=True)
    
    # Storage URLs
    blob_url = Column(String(512), nullable=True)
    audio_url = Column(String(512), nullable=True)
    transcript_url = Column(String(512), nullable=True)
    diarization_url = Column(String(512), nullable=True)
    
    # Processing metadata
    duration_seconds = Column(String(50), nullable=True)
    speaker_count = Column(String(10), nullable=True)
    
    def __repr__(self):
        return f"<File(id='{self.id}', filename='{self.filename}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'upload_time': self.upload_time.isoformat(),
            'status': self.status,
            'error_message': self.error_message,
            'blob_url': self.blob_url,
            'audio_url': self.audio_url,
            'transcript_url': self.transcript_url,
            'diarization_url': self.diarization_url,
            'duration_seconds': self.duration_seconds,
            'speaker_count': self.speaker_count
        } 