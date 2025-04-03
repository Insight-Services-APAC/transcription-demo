import os
import time
import json
import datetime
import requests
from urllib.parse import urlparse
import logging
from datetime import timedelta
from app.errors.exceptions import ValidationError, ServiceError, TranscriptionError
from app.errors.logger import log_exception


class BatchTranscriptionService:
    """
    A helper class that aligns with the official 2024-11-15 version of
    Azure Batch Transcription REST API, using simple requests calls.
    """

    def __init__(self, subscription_key, region, locale="en-AU"):
        self.subscription_key = subscription_key
        self.region = region
        self.locale = locale
        self.base_url = f"https://{region}.api.cognitive.microsoft.com/speechtotext"
        self.logger = logging.getLogger("app.services.transcription")
        if not subscription_key:
            raise ValidationError(
                "Azure Speech API subscription key is required but was not provided. Check your .env and ensure AZURE_SPEECH_KEY is set.",
                field="subscription_key",
            )
        if not region:
            raise ValidationError(
                "Azure Speech API region is required but was not provided. Check your .env and ensure AZURE_SPEECH_REGION is set.",
                field="region",
            )
        self.logger.info(f"Initialized BatchTranscriptionService with region: {region}")

    def submit_transcription(
        self, audio_url, enable_diarization=True, model_id=None, locale="en-AU"
    ):
        """
        Submit a transcription job using the optional custom/base model if provided.
        If no model_id is provided, the Whisper model URL is used by default.
        """
        url = f"{self.base_url}/transcriptions:submit?api-version=2024-11-15"
        if not audio_url:
            raise ValidationError(
                "Audio URL is required but was not provided.", field="audio_url"
            )
        parsed_url = urlparse(audio_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValidationError(
                f"Invalid audio URL format: {audio_url}", field="audio_url"
            )
        properties = {
            "timeToLiveHours": "12",
            "diarization": {"enabled": enable_diarization},
            "wordLevelTimestampsEnabled": True,
            "displayFormWordLevelTimestampsEnabled": True,
            "punctuationMode": "DictatedAndAutomatic",
            "profanityFilterMode": "Masked",
        }
        use_locale = locale or self.locale or "en-US"
        self.logger.info(f"Using locale: {use_locale} for transcription")
        data = {
            "contentUrls": [audio_url],
            "locale": use_locale,
            "displayName": os.path.basename(urlparse(audio_url).path),
            "properties": properties,
        }
        if model_id:
            self.logger.info(f"Using model with URL: {model_id}")
            data["model"] = {"self": model_id}
        else:
            self.logger.info("Using default Whisper model")
            whisper_url = f"https://{self.region}.api.cognitive.microsoft.com/speechtotext/v3.2/models/base/e418c4a9-9937-4db7-b2c9-8afbff72d950"
            data["model"] = {"self": whisper_url}
            data["properties"].pop("wordLevelTimestampsEnabled", None)
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
        }
        self.logger.info(f"Submitting transcription request to: {url}")
        self.logger.debug(f"Request payload: {json.dumps(data, indent=2)}")
        try:
            response = requests.post(url, json=data, headers=headers, timeout=60)
            if response.status_code not in (200, 201, 202):
                try:
                    error_content = response.json()
                except json.JSONDecodeError:
                    error_content = response.text
                raise TranscriptionError(
                    f"Azure Speech API returned HTTP {response.status_code}: {error_content}",
                    service="azure_speech",
                    status_code=response.status_code,
                )
            if "Location" not in response.headers:
                raise TranscriptionError(
                    f"Azure Speech API did not include a Location header.",
                    service="azure_speech",
                    headers=dict(response.headers),
                )
            transcription_location = response.headers["Location"]
            transcription_id = transcription_location.split("/")[-1]
            if "?api-version" in transcription_id:
                transcription_id = transcription_id.split("?")[0]
            self.logger.info(f"Submitted transcription. ID: {transcription_id}")
            return {
                "id": transcription_id,
                "status": "NotStarted",
                "location": transcription_location,
            }
        except requests.exceptions.RequestException as e:
            log_exception(e, self.logger)
            raise TranscriptionError(
                f"Network error communicating with Azure Speech API: {str(e)}",
                service="azure_speech",
            )
        except TranscriptionError:
            raise
        except Exception as e:
            log_exception(e, self.logger)
            raise TranscriptionError(
                f"Error submitting transcription job: {str(e)}", service="azure_speech"
            )

    def get_transcription_status(self, transcription_id):
        """
        Get the status of a transcription job.

        GET {base}/transcriptions/{id}?api-version=2024-11-15

        Returns:
            dict with the entire JSON object from the service,
            including "status" field.
        """
        if not transcription_id:
            raise ValidationError(
                "Transcription ID is required but was not provided.",
                field="transcription_id",
            )
        url = (
            f"{self.base_url}/transcriptions/{transcription_id}?api-version=2024-11-15"
        )
        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code != 200:
                try:
                    error_content = resp.json()
                except json.JSONDecodeError:
                    error_content = resp.text
                raise TranscriptionError(
                    f"Azure Speech API status-check error ({resp.status_code}): {error_content}",
                    service="azure_speech",
                    status_code=resp.status_code,
                    transcription_id=transcription_id,
                )
            return resp.json()
        except requests.exceptions.RequestException as e:
            log_exception(e, self.logger)
            raise TranscriptionError(
                f"Network error checking transcription status: {str(e)}",
                service="azure_speech",
                transcription_id=transcription_id,
            )
        except TranscriptionError:
            raise
        except Exception as e:
            log_exception(e, self.logger)
            raise TranscriptionError(
                f"Error checking transcription status: {str(e)}",
                service="azure_speech",
                transcription_id=transcription_id,
            )

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
            raise ValidationError(
                "Transcription ID is required but was not provided.",
                field="transcription_id",
            )
        transcription = self.get_transcription_status(transcription_id)
        status = transcription["status"]
        if status != "Succeeded":
            raise TranscriptionError(
                f"Cannot get results for transcription not completed. Current status: {status}",
                service="azure_speech",
                transcription_id=transcription_id,
                status=status,
            )
        files_url = f"{self.base_url}/transcriptions/{transcription_id}/files?api-version=2024-11-15"
        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
        try:
            resp = requests.get(files_url, headers=headers, timeout=60)
            if resp.status_code != 200:
                try:
                    error_content = resp.json()
                except json.JSONDecodeError:
                    error_content = resp.text
                raise TranscriptionError(
                    f"Azure Speech API returned error while listing transcription files ({resp.status_code}): {error_content}",
                    service="azure_speech",
                    status_code=resp.status_code,
                    transcription_id=transcription_id,
                )
            files_data = resp.json()
            if "values" not in files_data or not files_data["values"]:
                raise TranscriptionError(
                    "Transcription files response is empty or doesn't contain the expected 'values'.",
                    service="azure_speech",
                    transcription_id=transcription_id,
                )
            transcription_file = None
            for file_info in files_data["values"]:
                if file_info.get("kind") == "Transcription":
                    transcription_file = file_info
                    break
            if not transcription_file:
                raise TranscriptionError(
                    "No Transcription file found in transcription files response.",
                    service="azure_speech",
                    transcription_id=transcription_id,
                )
            content_url = transcription_file["links"].get("contentUrl")
            if not content_url:
                raise TranscriptionError(
                    "Transcription file missing 'contentUrl'.",
                    service="azure_speech",
                    transcription_id=transcription_id,
                    file_info=transcription_file,
                )
            download_resp = requests.get(content_url, timeout=120)
            if download_resp.status_code != 200:
                raise TranscriptionError(
                    f"Error downloading transcription content (Status {download_resp.status_code})",
                    service="azure_speech",
                    status_code=download_resp.status_code,
                    transcription_id=transcription_id,
                )
            try:
                return download_resp.json()
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parse error in transcription result: {str(e)}")
                self.logger.error(f"Raw response: {download_resp.text[:500]}...")
                raise TranscriptionError(
                    f"Invalid JSON in transcription result: {str(e)}",
                    service="azure_speech",
                    transcription_id=transcription_id,
                )
        except requests.exceptions.RequestException as e:
            log_exception(e, self.logger)
            raise TranscriptionError(
                f"Network error downloading transcription: {str(e)}",
                service="azure_speech",
                transcription_id=transcription_id,
            )
        except TranscriptionError:
            raise
        except Exception as e:
            log_exception(e, self.logger)
            raise TranscriptionError(
                f"Error getting transcription result: {str(e)}",
                service="azure_speech",
                transcription_id=transcription_id,
            )

    def wait_for_transcription(
        self, transcription_id, polling_interval=30, max_polling_attempts=60
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
                f"Transcription {transcription_id} status: {status} (attempt {attempts + 1}/{max_polling_attempts})"
            )
            if status == "Succeeded":
                return self.get_transcription_result(transcription_id)
            elif status == "Failed":
                error = info.get("properties", {}).get("error", {})
                error_message = error.get("message", "Unknown error")
                raise TranscriptionError(
                    f"Transcription {transcription_id} failed: {error_message}",
                    service="azure_speech",
                    transcription_id=transcription_id,
                    error=error,
                )
            attempts += 1
            time.sleep(polling_interval)
        raise TranscriptionError(
            f"Transcription {transcription_id} did not complete after {max_polling_attempts} attempts.",
            service="azure_speech",
            transcription_id=transcription_id,
            max_attempts=max_polling_attempts,
        )

    def list_models(self, model_type="base"):
        """
        Retrieve all available models of the specified type (e.g., "base" or "custom")
        using the 2024-11-15 API version.

        Implements pagination to retrieve ALL models, not just the first 100,
        and filters out deprecated models based on current date.
        """
        models_list = {"values": []}
        skip = 0
        top = 100
        current_date = datetime.datetime.utcnow()
        total_models = 0
        while True:
            url = f"{self.base_url}/models/{model_type}?api-version=2024-11-15&skip={skip}&top={top}"
            self.logger.info(f"Retrieving {model_type} models from: {url}")
            headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
            try:
                response = requests.get(url, headers=headers, timeout=60)
                if response.status_code != 200:
                    try:
                        error_content = response.json()
                    except json.JSONDecodeError:
                        error_content = response.text
                    raise TranscriptionError(
                        f"Azure Speech API error retrieving models ({response.status_code}): {error_content}",
                        service="azure_speech",
                        status_code=response.status_code,
                    )
                batch = response.json()
                batch_values = batch.get("values", [])
                total_models += len(batch_values)
                if not batch_values:
                    break
                for model in batch_values:
                    is_deprecated = False
                    deprecation_dates = model.get("properties", {}).get(
                        "deprecationDates", {}
                    )
                    transcription_date_str = deprecation_dates.get(
                        "transcriptionDateTime"
                    )
                    if transcription_date_str:
                        try:
                            transcription_date = datetime.datetime.strptime(
                                transcription_date_str, "%Y-%m-%dT%H:%M:%SZ"
                            )
                            if transcription_date < current_date:
                                is_deprecated = True
                                self.logger.debug(
                                    f"Filtering out deprecated model: {model.get('displayName', 'Unknown')} (deprecated on {transcription_date_str})"
                                )
                        except ValueError:
                            self.logger.warning(
                                f"Could not parse deprecation date: {transcription_date_str}"
                            )
                    if not is_deprecated:
                        models_list["values"].append(model)
                if "@nextLink" not in batch:
                    break
                skip += top
            except requests.exceptions.RequestException as e:
                log_exception(e, self.logger)
                raise TranscriptionError(
                    f"Network error retrieving models: {str(e)}", service="azure_speech"
                )
        self.logger.info(
            f"Retrieved {len(models_list.get('values', []))} non-deprecated models out of {total_models} total models."
        )
        return models_list
