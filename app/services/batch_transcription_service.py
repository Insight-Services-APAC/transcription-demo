import os
import time
import json
import requests
from urllib.parse import urlparse
import logging
from datetime import timedelta


class BatchTranscriptionService:
    """
    A helper class that aligns with the official 2024-11-15 version of
    Azure Batch Transcription REST API, using simple requests calls.
    """

    def __init__(self, subscription_key, region):
        self.subscription_key = subscription_key
        self.region = region
        # Updated base URL (no "/v3.1" suffix).
        # We'll attach /transcriptions:submit?api-version=2024-11-15 as needed.
        self.base_url = f"https://{region}.api.cognitive.microsoft.com/speechtotext"
        self.logger = logging.getLogger("BatchTranscriptionService")

        # Validate key and region
        if not subscription_key:
            raise ValueError(
                "Azure Speech API subscription key is required but was not provided. "
                "Check your .env and ensure AZURE_SPEECH_KEY is set."
            )
        if not region:
            raise ValueError(
                "Azure Speech API region is required but was not provided. "
                "Check your .env and ensure AZURE_SPEECH_REGION is set."
            )

        self.logger.info(f"Initialized BatchTranscriptionService with region: {region}")

    def submit_transcription(self, audio_url, locale="en-US", enable_diarization=True):
        """
        Submit a transcription job to the Azure Speech Service (API version 2024-11-15).

        Args:
            audio_url (str): SAS URL to the audio file in blob storage
            locale (str): Language code (e.g., "en-US")
            enable_diarization (bool): Whether to enable speaker diarization

        Returns:
            dict with keys: 'id' (transcription ID), 'status', 'location'
        """
        # Endpoint for submitting the transcription:
        # POST {base}/transcriptions:submit?api-version=2024-11-15
        url = f"{self.base_url}/transcriptions:submit?api-version=2024-11-15"

        if not audio_url:
            raise ValueError("Audio URL is required but was not provided.")

        # Validate audio_url
        parsed_url = urlparse(audio_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid audio URL format: {audio_url}")

        # Common “properties” to match the official sample
        # Adjust or remove as needed. Example timeToLive below = 12h.
        properties = {
            "timeToLiveHours": "12",  # 12 hours
            "diarization": {
                "enabled": enable_diarization
            },
            "wordLevelTimestampsEnabled": True,
            "displayFormWordLevelTimestampsEnabled": True,
            "punctuationMode": "DictatedAndAutomatic",
            "profanityFilterMode": "Masked"
        }

        # Payload to create the transcription
        data = {
            "contentUrls": [audio_url],
            "locale": locale,
            "displayName": os.path.basename(urlparse(audio_url).path),
            "properties": properties
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json"
        }

        self.logger.info(f"Submitting transcription request to: {url}")
        self.logger.info(f"Request payload: {json.dumps(data, indent=2)}")

        try:
            response = requests.post(url, json=data, headers=headers, timeout=60)
            if response.status_code not in (200, 201, 202):
                try:
                    error_content = response.json()
                except json.JSONDecodeError:
                    error_content = response.text
                raise Exception(
                    f"Azure Speech API returned HTTP {response.status_code}: {error_content}"
                )

            # The service should return a Location header with a /transcriptions/{id}
            if "Location" not in response.headers:
                raise Exception(
                    f"Azure Speech API did not include a Location header. Headers: {dict(response.headers)}"
                )

            transcription_location = response.headers["Location"]
            # Typically the location might look like:
            #   https://<region>.api.cognitive.microsoft.com/speechtotext/transcriptions/<transcriptionId>?api-version=2024-11-15
            # We'll parse out the actual ID from the end if needed:
            transcription_id = transcription_location.split("/")[-1]
            if "?api-version" in transcription_id:
                transcription_id = transcription_id.split("?")[0]

            self.logger.info(f"Submitted transcription. ID: {transcription_id}")

            # Return minimal info
            return {
                "id": transcription_id,
                "status": "NotStarted",
                "location": transcription_location
            }

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error submitting transcription job: {str(e)}")
            raise

    def get_transcription_status(self, transcription_id):
        """
        Get the status of a transcription job.

        GET {base}/transcriptions/{id}?api-version=2024-11-15

        Returns:
            dict with the entire JSON object from the service,
            including "status" field.
        """
        if not transcription_id:
            raise ValueError("Transcription ID is required but was not provided.")

        url = f"{self.base_url}/transcriptions/{transcription_id}?api-version=2024-11-15"
        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}

        try:
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code != 200:
                try:
                    error_content = resp.json()
                except json.JSONDecodeError:
                    error_content = resp.text
                raise Exception(
                    f"Azure Speech API status-check error ({resp.status_code}): {error_content}"
                )

            return resp.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error checking transcription status: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error checking transcription status: {str(e)}")
            raise

    def get_transcription_result(self, transcription_id):
        """
        Get the actual transcription result JSON (kind=Transcription).
        - First we do GET /transcriptions/{id}?api-version=2024-11-15
          to verify status is 'Succeeded'.
        - Then we do GET /transcriptions/{id}/files?api-version=2024-11-15
          to find the 'Transcription' file entry and fetch `contentUrl`.

        Returns:
            dict containing the entire transcription result JSON.
        """
        if not transcription_id:
            raise ValueError("Transcription ID is required but was not provided.")

        # Make sure the transcription is done
        transcription = self.get_transcription_status(transcription_id)
        status = transcription["status"]

        if status != "Succeeded":
            raise Exception(
                f"Cannot get results for transcription not completed. Current status: {status}"
            )

        # Now get the list of output files
        files_url = f"{self.base_url}/transcriptions/{transcription_id}/files?api-version=2024-11-15"
        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}

        resp = requests.get(files_url, headers=headers, timeout=60)
        if resp.status_code != 200:
            try:
                error_content = resp.json()
            except json.JSONDecodeError:
                error_content = resp.text
            raise Exception(
                f"Azure Speech API returned error while listing transcription files ({resp.status_code}): {error_content}"
            )

        files_data = resp.json()
        if "values" not in files_data or not files_data["values"]:
            raise Exception(
                "Transcription files response is empty or doesn't contain the expected 'values'."
            )

        # find the "kind":"Transcription" file
        transcription_file = None
        for file_info in files_data["values"]:
            if file_info.get("kind") == "Transcription":
                transcription_file = file_info
                break

        if not transcription_file:
            raise Exception("No Transcription file found in transcription files response.")

        content_url = transcription_file["links"].get("contentUrl")
        if not content_url:
            raise Exception(
                f"Transcription file missing 'contentUrl'. Info: {json.dumps(transcription_file, indent=2)}"
            )

        # Finally, download that JSON
        download_resp = requests.get(content_url, timeout=120)
        if download_resp.status_code != 200:
            raise Exception(
                f"Error downloading transcription content (Status {download_resp.status_code}): {download_resp.text}"
            )

        try:
            return download_resp.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error in transcription result: {str(e)}")
            self.logger.error(f"Raw response: {download_resp.text[:500]}...")
            raise Exception(f"Invalid JSON in transcription result: {str(e)}")

    def wait_for_transcription(
        self,
        transcription_id,
        polling_interval=30,
        max_polling_attempts=60
    ):
        """
        Wait for a transcription job to complete, polling by status.

        Args:
            transcription_id (str)
            polling_interval (int): how often (seconds) to check
            max_polling_attempts (int): give up after N polls

        Returns:
            dict: The final transcription JSON (the recognized phrases).
        """
        attempts = 0
        while attempts < max_polling_attempts:
            info = self.get_transcription_status(transcription_id)
            status = info["status"]

            self.logger.info(
                f"Transcription {transcription_id} status: {status} "
                f"(attempt {attempts+1}/{max_polling_attempts})"
            )
            if status == "Succeeded":
                return self.get_transcription_result(transcription_id)
            elif status == "Failed":
                error = info.get("properties", {}).get("error", {})
                error_message = error.get("message", "Unknown error")
                raise Exception(f"Transcription {transcription_id} failed: {error_message}")

            attempts += 1
            time.sleep(polling_interval)

        raise Exception(
            f"Transcription {transcription_id} did not complete after {max_polling_attempts} attempts."
        )
