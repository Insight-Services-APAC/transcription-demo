import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Float, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class File(Base):
    __tablename__ = 'files'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='uploaded')  # uploaded, processing, completed, error
    error_message = Column(Text, nullable=True)
    
    # Progress tracking
    current_stage = Column(String(50), nullable=True)  # transcribing
    progress_percent = Column(Float, default=0.0)  # Overall progress percentage
    stage_progress = Column(Float, default=0.0)  # Progress of current stage
    
    # Storage URLs
    blob_url = Column(String(512), nullable=True)
    transcript_url = Column(String(512), nullable=True)
    
    # Azure Speech Service transcription ID
    transcription_id = Column(String(255), nullable=True)
    
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
            'current_stage': self.current_stage,
            'progress_percent': self.progress_percent,
            'stage_progress': self.stage_progress,
            'blob_url': self.blob_url,
            'transcript_url': self.transcript_url,
            'transcription_id': self.transcription_id,
            'duration_seconds': self.duration_seconds,
            'speaker_count': self.speaker_count
        }