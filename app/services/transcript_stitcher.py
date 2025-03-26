import json
import datetime
import re

class TranscriptStitcher:
    def __init__(self):
        pass
    
    def stitch(self, chunk_transcripts, diarization_segments):
        """
        Stitch together chunk transcripts and apply diarization
        
        Args:
            chunk_transcripts (list): List of transcripts from audio chunks
            diarization_segments (list): List of diarization segments
            
        Returns:
            list: Stitched transcript with speaker labels
        """
        # Flatten chunk transcripts
        flat_transcript = []
        for chunk in chunk_transcripts:
            flat_transcript.extend(chunk)
            
        # Sort by start time
        flat_transcript.sort(key=lambda x: self._time_to_seconds(x['start']))
        
        # Merge overlapping segments
        merged_transcript = self._merge_overlapping_segments(flat_transcript)
        
        # Apply diarization
        labeled_transcript = self._apply_diarization(merged_transcript, diarization_segments)
        
        return labeled_transcript
    
    def _merge_overlapping_segments(self, segments):
        """Merge transcript segments that overlap significantly"""
        if not segments:
            return []
            
        merged = [segments[0]]
        
        for current in segments[1:]:
            previous = merged[-1]
            
            # Calculate overlap
            prev_end = self._time_to_seconds(previous['end'])
            curr_start = self._time_to_seconds(current['start'])
            
            # If segments overlap by more than 50% of the smaller segment
            if curr_start <= prev_end:
                # Calculate overlap percentage
                curr_end = self._time_to_seconds(current['end'])
                prev_duration = prev_end - self._time_to_seconds(previous['start'])
                curr_duration = curr_end - curr_start
                min_duration = min(prev_duration, curr_duration)
                overlap = prev_end - curr_start
                
                # If overlap is significant and text is different
                if overlap > 0 and overlap / min_duration > 0.5 and previous['text'] != current['text']:
                    # Merge the segments
                    merged[-1]['end'] = max(previous['end'], current['end'], key=self._time_to_seconds)
                    merged[-1]['text'] = previous['text'] + " " + current['text']
                elif overlap <= 0 or previous['text'] == current['text']:
                    # Just add the current segment if no significant overlap or duplicate text
                    merged.append(current)
            else:
                # No overlap, just add the segment
                merged.append(current)
                
        return merged
    
    def _apply_diarization(self, transcript, diarization):
        """
        Apply diarization information to transcript segments
        
        This maps each transcript segment to a speaker based on the maximum overlap
        """
        labeled_transcript = []
        
        for segment in transcript:
            segment_start = self._time_to_seconds(segment['start'])
            segment_end = self._time_to_seconds(segment['end'])
            
            # Find the speaker with maximum overlap
            best_speaker = None
            max_overlap = 0
            
            for diar_segment in diarization:
                diar_start = self._time_to_seconds(diar_segment['start'])
                diar_end = self._time_to_seconds(diar_segment['end'])
                
                # Calculate overlap
                overlap_start = max(segment_start, diar_start)
                overlap_end = min(segment_end, diar_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = diar_segment['speaker']
            
            # Create new segment with speaker label
            labeled_segment = {
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'],
                'speaker': best_speaker if best_speaker else "Unknown"
            }
            
            labeled_transcript.append(labeled_segment)
            
        return labeled_transcript
    
    def save_transcript(self, transcript, json_path, txt_path=None):
        """
        Save transcript to JSON and optionally to TXT format
        
        Args:
            transcript (list): Labeled transcript
            json_path (str): Path to save JSON
            txt_path (str, optional): Path to save text version
            
        Returns:
            tuple: Paths to saved files
        """
        # Save JSON
        with open(json_path, 'w') as f:
            json.dump(transcript, f, indent=2)
            
        # Save TXT if specified
        if txt_path:
            with open(txt_path, 'w') as f:
                for segment in transcript:
                    f.write(f"[{segment['start']} - {segment['end']}] {segment['speaker']}: {segment['text']}\n\n")
            
        return json_path, txt_path if txt_path else None
    
    def _time_to_seconds(self, time_str):
        """Convert HH:MM:SS time string to seconds"""
        try:
            h, m, s = map(int, time_str.split(':'))
            return h * 3600 + m * 60 + s
        except ValueError:
            # Handle milliseconds format if present
            pattern = r'(\d+):(\d+):(\d+)\.?(\d*)'
            match = re.match(pattern, time_str)
            if match:
                h, m, s, ms = match.groups()
                seconds = int(h) * 3600 + int(m) * 60 + int(s)
                if ms:
                    seconds += int(ms) / 10**(len(ms))
                return seconds
            return 0 