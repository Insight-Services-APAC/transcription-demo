import uuid
from datetime import datetime
from app.extensions import db


class File(db.Model):
    __tablename__ = "files"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="uploaded")
    error_message = db.Column(db.Text, nullable=True)
    current_stage = db.Column(db.String(50), nullable=True)
    progress_percent = db.Column(db.Float, default=0.0)
    stage_progress = db.Column(db.Float, default=0.0)
    blob_url = db.Column(db.String(512), nullable=True)
    transcript_url = db.Column(db.String(512), nullable=True)
    transcription_id = db.Column(db.String(255), nullable=True)
    duration_seconds = db.Column(db.String(50), nullable=True)
    speaker_count = db.Column(db.String(10), nullable=True)
    accuracy_percent = db.Column(db.Float, nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    model_id = db.Column(db.String(255), nullable=True)
    model_name = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<File(id='{self.id}', filename='{self.filename}', status='{self.status}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "upload_time": self.upload_time.isoformat(),
            "status": self.status,
            "error_message": self.error_message,
            "current_stage": self.current_stage,
            "progress_percent": self.progress_percent,
            "stage_progress": self.stage_progress,
            "blob_url": self.blob_url,
            "transcript_url": self.transcript_url,
            "transcription_id": self.transcription_id,
            "duration_seconds": self.duration_seconds,
            "speaker_count": self.speaker_count,
            "accuracy_percent": self.accuracy_percent,
            "user_id": self.user_id,
            "model_id": self.model_id,
            "model_name": self.model_name,
        }
