import os
import requests
import yaml
from dotenv import load_dotenv
from .logger_setup import get_logger
from .audio_processor import AudioProcessor

logger = get_logger(__name__)

class OpenAITranscriber:
    def __init__(self):
        load_dotenv()  # Load environment variables from .env
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "gpt-4o-mini-transcribe") # Default to gpt-4o-mini-transcribe if not set

        if not self.api_key or self.api_key == "YOUR_OPENAI_API_KEY_HERE":
            logger.error("OPENAI_API_KEY not found or not set in .env file. Please set it to use OpenAI transcription.")
            # Potentially raise an exception or handle this state in the app
            # For now, we'll allow initialization but transcription will fail.

        # The new audio transcriptions endpoint for gpt-4o is slightly different
        # It's recommended to use the /v1/audio/transcriptions endpoint
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"
        
        # Load reference YAML if it exists
        self.reference_context = self._load_reference_yaml()
        
        # Initialize audio processor for speed conversion
        self.audio_processor = AudioProcessor()

    def _load_reference_yaml(self):
        """Load reference.yml from project root if it exists"""
        reference_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reference.yml")
        if os.path.exists(reference_path):
            try:
                with open(reference_path, 'r', encoding='utf-8') as f:
                    reference_data = yaml.safe_load(f)
                    logger.info(f"Loaded reference context from {reference_path}")
                    return reference_data
            except Exception as e:
                logger.warning(f"Failed to load reference.yml: {e}")
        return None

    def get_reference_status(self):
        """Get the status of reference.yml loading for UI display"""
        if self.reference_context:
            terms_count = len(self.reference_context.get('terminology', {}))
            has_context = bool(self.reference_context.get('context'))
            has_style = bool(self.reference_context.get('style'))
            
            status_parts = []
            if terms_count > 0:
                status_parts.append(f"{terms_count} terms")
            if has_context:
                status_parts.append("context")
            if has_style:
                status_parts.append("style")
            
            return f"Loaded ({', '.join(status_parts)})", "green"
        else:
            return "Not loaded", "gray"

    def _build_prompt_with_reference(self):
        """Build a prompt string with reference context if available"""
        if not self.reference_context:
            return None
        
        prompt_parts = []
        
        if 'terminology' in self.reference_context:
            terms = self.reference_context['terminology']
            if terms:
                prompt_parts.append("Use these specific terms when transcribing:")
                for term, description in terms.items():
                    prompt_parts.append(f"- {term}: {description}")
        
        if 'context' in self.reference_context:
            context = self.reference_context['context']
            if context:
                prompt_parts.append(f"Context: {context}")
        
        if 'style' in self.reference_context:
            style = self.reference_context['style']
            if style:
                prompt_parts.append(f"Style: {style}")
        
        return "\n".join(prompt_parts) if prompt_parts else None

    def transcribe_audio(self, audio_file_path, use_x2_speed=False):
        if not self.api_key or self.api_key == "YOUR_OPENAI_API_KEY_HERE":
            logger.error("Cannot transcribe: OPENAI_API_KEY is not configured.")
            return None, "OPENAI_API_KEY not configured"

        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None, "Audio file not found"

        # Process audio for x2 speed if requested
        processing_file_path = audio_file_path
        temp_file_created = False
        
        if use_x2_speed:
            logger.info("x2 Speed mode enabled - converting audio to 2x speed")
            processing_file_path = self.audio_processor.convert_to_x2_speed(audio_file_path)
            temp_file_created = (processing_file_path != audio_file_path)

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        files = {
            "file": (os.path.basename(processing_file_path), open(processing_file_path, 'rb'), "audio/wav"),
            "model": (None, self.model_name) # Correctly send model as part of multipart
        }
        
        # Add prompt if reference context is available
        prompt = self._build_prompt_with_reference()
        if prompt:
            files["prompt"] = (None, prompt)
            logger.debug(f"Using reference prompt: {prompt[:100]}...")

        # Parameters for transcription (optional, but good to be aware of)
        # data = {
        #     "model": self.model_name,
        #     # "language": "en", # Can be specified if needed
        #     # "response_format": "json", # Default is json
        #     # "temperature": 0, # For transcription, usually 0
        # }

        try:
            speed_info = " (x2 speed)" if use_x2_speed else ""
            logger.info(f"Sending {processing_file_path} to OpenAI for transcription using model {self.model_name}{speed_info}...")
            response = requests.post(self.api_url, headers=headers, files=files) # Removed data=data, model is in files
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            result = response.json()
            transcript = result.get("text")

            if transcript is None:
                logger.error(f"Transcription failed. API response did not contain 'text'. Response: {result}")
                return None, f"Transcription failed (no text in response)"

            logger.info(f"Transcription successful{speed_info}.")
            return transcript, None  # transcript, error_message (None if no error)

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if e.response is not None:
                logger.error(f"API Error Response: {e.response.status_code} - {e.response.text}")
                return None, f"API Error: {e.response.status_code} - {e.response.text}"
            return None, f"API Request Failed: {str(e)}"
        except Exception as e:
            logger.error(f"An unexpected error occurred during transcription: {e}")
            return None, f"Unexpected error: {str(e)}"
        finally:
            # Clean up temporary file if created
            if temp_file_created:
                self.audio_processor.cleanup_temp_file(processing_file_path)

if __name__ == '__main__':
    # This example assumes you have a .env file with your OPENAI_API_KEY
    # and a sample audio file.

    # Adjust path for direct execution
    if __package__ is None:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from src.logger_setup import get_logger # Re-import for this scope if needed, or ensure logger is global
        # If audio_recorder is needed for a test file:
        # from src.audio_recorder import AudioRecorder

    # Ensure logger is available if it wasn't setup by the class's module-level import
    # This is a bit tricky due to how __main__ interacts with module imports.
    # For simplicity, we'll rely on the module-level logger.

    logger.info("Starting OpenAITranscriber example.")

    # Create a dummy .env if it doesn't exist for basic testing (without a real key it will fail gracefully)
    if not os.path.exists("../.env"):
        logger.warning("No .env file found, creating a dummy one for the test.")
        with open("../.env", "w") as f:
            f.write("OPENAI_API_KEY=\"YOUR_OPENAI_API_KEY_HERE\"\n")
            f.write("MODEL_NAME=\"gpt-4o\"\n")

    transcriber = OpenAITranscriber()

    if not transcriber.api_key or transcriber.api_key == "YOUR_OPENAI_API_KEY_HERE":
        logger.warning("OpenAI API key is not set or is a placeholder. Transcription will not work.")
        logger.warning("Please create a .env file in the project root (next to src folder) with your actual OPENAI_API_KEY.")
        logger.warning("Example .env content:")
        logger.warning("OPENAI_API_KEY=\"sk-yourRealApiKeyGoesHere\"")
        logger.warning("MODEL_NAME=\"gpt-4o\"")
    else:
        logger.info("OpenAI API key loaded.")

    # Create a dummy WAV file for testing if one doesn't exist
    # This requires PyAudio and Wave, which might not be ideal for a standalone transcriber test.
    # For now, we'll assume a file exists or skip this part of the test if it doesn't.
    dummy_audio_path = "../recordings/test_audio.wav" # Ensure 'recordings' dir exists if creating file

    # Simplified: Check if the dummy file exists, if not, skip transcription test.
    if os.path.exists(dummy_audio_path):
        logger.info(f"Attempting to transcribe: {dummy_audio_path}")
        transcript, error = transcriber.transcribe_audio(dummy_audio_path)
        if error:
            logger.error(f"Transcription failed: {error}")
        elif transcript:
            logger.info(f"Transcript: {transcript}")
        else:
            logger.error("Transcription returned no transcript and no error message.")
    else:
        logger.warning(f"Test audio file not found: {dummy_audio_path}. Skipping transcription test.")
        logger.warning("To test transcription, place a valid WAV file at that location or modify the path.")
        # You could create a simple silent WAV file here for testing if needed:
        # import wave
        # sample_rate = 16000
        # duration = 1 # second
        # n_channels = 1
        # samp_width = 2 # 16-bit
        # n_frames = duration * sample_rate
        # comp_type = "NONE"
        # comp_name = "not compressed"
        # if not os.path.exists(os.path.dirname(dummy_audio_path)):
        #    os.makedirs(os.path.dirname(dummy_audio_path))
        # with wave.open(dummy_audio_path, 'wb') as wf:
        #    wf.setnchannels(n_channels)
        #    wf.setsampwidth(samp_width)
        #    wf.setframerate(sample_rate)
        #    wf.setnframes(n_frames)
        #    wf.setcomptype(comp_type, comp_name)
        #    wf.writeframes(b'\x00\x00' * n_frames) # silent audio
        # logger.info(f"Created a dummy silent WAV file for testing: {dummy_audio_path}")
        # Now you could re-run the transcription attempt.

    logger.info("OpenAITranscriber example finished.")
