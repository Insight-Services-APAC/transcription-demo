import os
import torch
from pyannote.audio import Pipeline
from datetime import datetime
import json

class DiarizationService:
    def __init__(self, auth_token):
        self.auth_token = auth_token
        self._pipeline = None
        
    @property
    def pipeline(self):
        """Lazy-load the diarization pipeline"""
        if self._pipeline is None:
            # Initialize the pyannote diarization pipeline
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.0",
                use_auth_token=self.auth_token
            )
            
            # Use GPU if available
            if torch.cuda.is_available():
                self._pipeline = self._pipeline.to(torch.device("cuda"))
                
        return self._pipeline
    
    def diarize(self, audio_file_path):
        """
        Perform speaker diarization on audio file
        
        Args:
            audio_file_path (str): Path to audio file
            
        Returns:
            list: List of diarization segments with speaker labels and timestamps
        """
        # Run diarization
        diarization = self.pipeline(audio_file_path)
        
        # Process results
        segments = []
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # Format start and end time
            start_time = self._format_time(turn.start)
            end_time = self._format_time(turn.end)
            
            # Create segment
            segment = {
                'start': start_time,
                'end': end_time,
                'speaker': f"Speaker {speaker.split('_')[-1]}"  # Format as "Speaker 1", "Speaker 2", etc.
            }
            
            segments.append(segment)
            
        return segments
    
    def save_diarization(self, segments, output_file_path):
        """Save diarization results to JSON file"""
        with open(output_file_path, 'w') as f:
            json.dump(segments, f, indent=2)
            
        return output_file_path
    
    def _format_time(self, seconds):
        """Format time in HH:MM:SS format"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}" 