import azure.cognitiveservices.speech as speechsdk
import os
import json
import time
from datetime import datetime

class SpeechService:
    def __init__(self, speech_key, speech_region='eastus'):
        self.speech_key = speech_key
        self.speech_region = speech_region
        
    def transcribe_audio_file(self, audio_file_path, language="en-US"):
        """
        Transcribe audio file using Azure Speech Service (Whisper model)
        
        Args:
            audio_file_path (str): Path to audio file
            language (str): Language code
            
        Returns:
            dict: Transcription result with text and timestamps
        """
        # Create speech config
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )
        
        # Set the speech recognition language
        speech_config.speech_recognition_language = language
        
        # Request word-level timestamps
        speech_config.request_word_level_timestamps()
        
        # Use Whisper model
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_SingleLanguageIdPriority,
            "WhisperDefault"
        )
        
        # Create audio config
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
        
        # Create speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, 
            audio_config=audio_config
        )
        
        # Start continuous recognition
        all_results = []
        done = False
        
        def recognized_cb(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                result_dict = json.loads(evt.result.json)
                all_results.append(result_dict)
                
        def canceled_cb(evt):
            nonlocal done
            done = True
            
        def session_stopped_cb(evt):
            nonlocal done
            done = True
            
        # Connect callbacks
        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.session_stopped.connect(session_stopped_cb)
        speech_recognizer.canceled.connect(canceled_cb)
        
        # Start continuous recognition
        speech_recognizer.start_continuous_recognition()
        
        # Wait for completion
        while not done:
            time.sleep(0.5)
            
        # Stop recognition
        speech_recognizer.stop_continuous_recognition()
        
        # Process results
        transcript = self._process_results(all_results)
        return transcript
        
    def _process_results(self, all_results):
        """
        Process results from Azure Speech Service
        
        Args:
            all_results (list): List of result dictionaries
            
        Returns:
            dict: Processed transcript
        """
        transcript = []
        
        for result in all_results:
            # Skip if no recognition
            if not result.get('NBest'):
                continue
                
            best_result = result['NBest'][0]
            
            # Get start and end time in proper format
            start_time = self._format_time(result['Offset'] / 10000000)  # Convert to seconds
            end_time = self._format_time((result['Offset'] + result['Duration']) / 10000000)
            
            # Get recognized text
            text = best_result.get('Display', best_result.get('Lexical', ''))
            
            # Create entry
            entry = {
                'start': start_time,
                'end': end_time,
                'text': text,
                'words': best_result.get('Words', [])
            }
            
            transcript.append(entry)
            
        return transcript
    
    def _format_time(self, seconds):
        """Format time in HH:MM:SS format"""
        return str(datetime.utcfromtimestamp(seconds).strftime('%H:%M:%S')) 