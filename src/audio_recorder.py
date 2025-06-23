import pyaudio
import wave
import os
import time
from datetime import datetime
import sys # Added for path adjustment

# Adjust path for direct execution
if __name__ == '__main__' and __package__ is None:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.logger_setup import get_logger
else:
    from .logger_setup import get_logger


logger = get_logger(__name__)

# Define project root as one level up from the 'src' directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class AudioRecorder:
    def __init__(self, output_folder_name="recordings"):
        self.output_folder = os.path.join(PROJECT_ROOT, output_folder_name)
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            logger.info(f"Created output folder: {self.output_folder}")

        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 1  # Mono
        self.fs = 16000  # Record at 16000 samples per second

        self.p = None
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.filename = None

    def _generate_filename(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_folder, f"recording_{timestamp}.wav")

    def start_recording(self):
        if self.is_recording:
            logger.warning("Recording is already in progress.")
            return False

        self.p = pyaudio.PyAudio()
        try:
            self.stream = self.p.open(format=self.sample_format,
                                      channels=self.channels,
                                      rate=self.fs,
                                      frames_per_buffer=self.chunk,
                                      input=True)
        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            if "Invalid input device" in str(e) or "No Default Input Device Available" in str(e):
                logger.error("No input device found. Please check your microphone connection and system settings.")
            self.p.terminate()
            self.p = None
            return False

        self.frames = []
        self.is_recording = True
        self.filename = self._generate_filename()
        logger.info(f"Recording started. Saving to {self.filename}")
        return True

    def stop_recording(self):
        if not self.is_recording:
            logger.warning("Recording is not in progress.")
            return None

        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
            self.p = None # Reset PyAudio instance

        logger.info("Recording stopped.")

        self._save_recording()
        return self.filename

    def _save_recording(self):
        if not self.frames:
            logger.warning("No frames recorded to save.")
            return

        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format) if self.p else pyaudio.PyAudio().get_sample_size(self.sample_format)) # Use a temporary instance if self.p is None
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        logger.info(f"Recording saved to {self.filename}")

    def record_audio_chunk(self):
        """Call this method repeatedly in a loop while is_recording is true."""
        if self.is_recording and self.stream:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
            except IOError as e:
                logger.error(f"Error reading from stream: {e}")
                # Could indicate a device disconnection or other issue
                self.stop_recording() # Stop recording if there's a stream error

if __name__ == '__main__':
    # Example Usage (Commented out for non-interactive environment)
    # logger.info("AudioRecorder example usage (currently commented out).")
    pass
    # recorder = AudioRecorder()

    # print("Attempting to start recording for 3 seconds (non-interactive test)...")
    # if recorder.start_recording():
    #     print("Recording started...")
    #     time.sleep(3) # Record for 3 seconds
    #     filepath = recorder.stop_recording()
    #     if filepath:
    #         print(f"Recording saved: {filepath}")
    #         # Verify file exists
    #         if os.path.exists(filepath):
    #             logger.info(f"File {filepath} successfully created.")
    #             # Optionally, check file size or content if possible non-interactively
    #             # For now, existence is the main check.
    #         else:
    #             logger.error(f"File {filepath} was NOT created.")
    #     else:
    #         print("Failed to save recording or no recording was made.")
    # else:
    #     print("Failed to start recording. Check logs for details (e.g., no microphone).")
    # logger.info("AudioRecorder non-interactive test finished.")
