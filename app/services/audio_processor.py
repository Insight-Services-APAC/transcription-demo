import os
import subprocess
import ffmpeg
import tempfile
from pydub import AudioSegment
import webrtcvad
import numpy as np
import wave

class AudioProcessor:
    def __init__(self, chunk_size_seconds=30, chunk_overlap_seconds=5):
        self.chunk_size_seconds = chunk_size_seconds
        self.chunk_overlap_seconds = chunk_overlap_seconds
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level (3 is most aggressive)
        
    def extract_audio(self, dcr_file_path, output_path=None):
        """
        Extract audio from DCR file to WAV format
        
        Args:
            dcr_file_path (str): Path to DCR file
            output_path (str, optional): Path for output WAV file. If None, uses the same name with .wav extension
            
        Returns:
            str: Path to the extracted WAV file
        """
        if output_path is None:
            output_path = os.path.splitext(dcr_file_path)[0] + '.wav'
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # Use ffmpeg to extract audio from DCR file
            ffmpeg.input(dcr_file_path).output(output_path, acodec='pcm_s16le', vn=None).run(quiet=True, overwrite_output=True)
            return output_path
        except ffmpeg.Error as e:
            # Fallback to subprocess if ffmpeg-python has issues
            cmd = ['ffmpeg', '-i', dcr_file_path, '-vn', '-acodec', 'pcm_s16le', output_path, '-y']
            subprocess.run(cmd, check=True)
            return output_path
    
    def chunk_audio(self, wav_file_path, output_dir):
        """
        Split WAV file into chunks with overlap
        
        Args:
            wav_file_path (str): Path to WAV file
            output_dir (str): Directory to save chunks
            
        Returns:
            list: List of paths to chunk files
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Load audio file
        audio = AudioSegment.from_wav(wav_file_path)
        
        # Calculate chunk size and overlap in milliseconds
        chunk_size_ms = self.chunk_size_seconds * 1000
        overlap_ms = self.chunk_overlap_seconds * 1000
        
        # Get audio duration
        duration_ms = len(audio)
        
        # Calculate chunk boundaries based on silence detection
        chunk_boundaries = self._get_smart_boundaries(wav_file_path, chunk_size_ms, overlap_ms)
        
        # Create chunks
        chunk_paths = []
        for i, (start_ms, end_ms) in enumerate(chunk_boundaries):
            chunk = audio[start_ms:end_ms]
            chunk_path = os.path.join(output_dir, f"chunk_{i:03d}.wav")
            chunk.export(chunk_path, format="wav")
            chunk_paths.append(chunk_path)
            
        return chunk_paths
    
    def _get_smart_boundaries(self, wav_file_path, chunk_size_ms, overlap_ms):
        """
        Calculate chunk boundaries based on silence detection
        
        This method attempts to split at silence boundaries when possible
        """
        # Open the wave file
        with wave.open(wav_file_path, 'rb') as wf:
            # Get basic info
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            n_channels = wf.getnchannels()
            n_frames = wf.getnframes()
            
            # Calculate duration
            duration_ms = (n_frames / sample_rate) * 1000
            
        # Simple chunking initially
        boundaries = []
        start_ms = 0
        
        while start_ms < duration_ms:
            end_ms = min(start_ms + chunk_size_ms, duration_ms)
            
            if end_ms >= duration_ms:
                # Last chunk
                boundaries.append((start_ms, end_ms))
                break
            
            # Add a chunk
            boundaries.append((start_ms, end_ms))
            
            # Move to next chunk with overlap
            start_ms = end_ms - overlap_ms
            
        return boundaries 