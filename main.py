import time
import threading
import os
import sys
from enum import Enum, auto
from dotenv import load_dotenv # Added for the __main__ block API key check

# Ensure src directory is in path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.logger_setup import get_logger
from src.audio_recorder import AudioRecorder
from src.transcriber import OpenAITranscriber
from src.clipboard_handler import copy_to_clipboard
from src.gui import TranscriptionGUI, STATUS_IDLE, STATUS_RECORDING, STATUS_TRANSCRIBING, STATUS_ERROR
from src.hotkey_manager import HotkeyManager

# Initialize logger for the main application
logger = get_logger("TranscriptionApp")

class AppState(Enum):
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto() # Covers stopping, saving, transcribing

class TranscriptionApp:
    def __init__(self):
        logger.info("Initializing Transcription Application...")
        # Pass the toggle method to the GUI
        self.gui = TranscriptionGUI(button_callback=self.toggle_recording_state)
        self.recorder = AudioRecorder() # Uses default ../recordings
        self.transcriber = OpenAITranscriber() # Loads .env internally
        self.hotkey_manager = HotkeyManager(hotkey_str="ctrl+shift+r") # Default hotkey

        self.current_state = AppState.IDLE
        self.recording_start_time = None
        self.recording_filepath = None
        self.audio_capture_active = False # To control the audio capture loop explicitly

        self._setup_callbacks()
        self._update_reference_status()
        logger.info("Application initialized.")

    def _setup_callbacks(self):
        """Set up callbacks for hotkeys. GUI buttons are handled by passing toggle_recording_state."""
        self.hotkey_manager.register_callback(self.toggle_recording_state)

    def _update_gui_status(self, status_text, color="white"):
        self.gui.gui_queue.put(("update_status", {"text": status_text, "color": color}))

    def _update_gui_timer(self, time_str):
        self.gui.gui_queue.put(("update_timer", time_str))

    def _update_gui_transcript(self, text):
        self.gui.gui_queue.put(("update_transcript", text))

    def _set_gui_button_states(self, start_enabled, stop_enabled):
        self.gui.gui_queue.put(("set_button_states", {"start_enabled": start_enabled, "stop_enabled": stop_enabled}))

    def _show_gui_status_message(self, text, duration=3000):
        self.gui.gui_queue.put(("show_status_message", {"text": text, "duration": duration}))

    def _update_reference_status(self):
        """Update the reference file status in the GUI"""
        status_text, color = self.transcriber.get_reference_status()
        self.gui.gui_queue.put(("update_reference_status", {"text": status_text, "color": color}))

    def _timer_thread_func(self):
        logger.debug("Timer thread started.")
        while self.current_state == AppState.RECORDING and self.recording_start_time:
            elapsed_seconds = int(time.time() - self.recording_start_time)
            timer_str = time.strftime('%H:%M:%S', time.gmtime(elapsed_seconds))
            self._update_gui_timer(timer_str)
            time.sleep(1) # Update timer every second
            if not (self.current_state == AppState.RECORDING): # Re-check state after sleep
                break
        logger.debug("Timer thread finished.")

    def _audio_capture_loop(self):
        logger.debug("Audio capture loop started.")
        try:
            while self.audio_capture_active: # Controlled by self.audio_capture_active
                if self.current_state == AppState.RECORDING and self.recorder.is_recording:
                    self.recorder.record_audio_chunk()
                    time.sleep(0.01) # Keep this short to quickly fill buffer
                else:
                    # If not recording or recorder stopped, exit loop
                    logger.debug("Audio capture loop condition false, exiting.")
                    break
        except Exception as e:
            logger.error(f"Exception in audio capture loop: {e}", exc_info=True)
        finally:
            logger.debug("Audio capture loop finished.")


    def start_recording(self):
        if self.current_state != AppState.IDLE:
            logger.warning(f"Cannot start recording: Current state is {self.current_state.name}, not IDLE.")
            return

        logger.info("Attempting to start recording...")
        self.current_state = AppState.PROCESSING # Short transition state

        self._update_gui_transcript("") # Clear previous transcript

        if self.recorder.start_recording():
            self.current_state = AppState.RECORDING
            self.recording_start_time = time.time()
            self._update_gui_status(STATUS_RECORDING, "red")
            self._set_gui_button_states(start_enabled=False, stop_enabled=True)
            self._show_gui_status_message("Recording started...")

            threading.Thread(target=self._timer_thread_func, daemon=True).start()

            self.audio_capture_active = True # Enable the capture loop
            threading.Thread(target=self._audio_capture_loop, daemon=True).start()
            logger.info("Recording started successfully.")
        else:
            self.current_state = AppState.IDLE # Revert to IDLE
            self._update_gui_status(STATUS_ERROR + ": Mic?", "orange")
            self._show_gui_status_message("Failed to start recording. Check microphone.", duration=5000)
            self._set_gui_button_states(start_enabled=True, stop_enabled=False) # Ensure buttons are reset
            logger.error("Failed to start recording (recorder.start_recording returned False).")

    def stop_recording_and_process(self):
        if self.current_state != AppState.RECORDING:
            logger.warning(f"Cannot stop recording: Current state is {self.current_state.name}, not RECORDING.")
            return

        logger.info("Attempting to stop recording...")
        self.current_state = AppState.PROCESSING
        self.audio_capture_active = False # Signal audio capture loop to stop

        # Wait a very brief moment for the audio capture loop to finish processing its current chunk
        time.sleep(0.1)

        self.recording_filepath = self.recorder.stop_recording() # This also saves the file

        self._update_gui_status(STATUS_TRANSCRIBING, "yellow")
        self._set_gui_button_states(start_enabled=False, stop_enabled=False) # Disable both during processing
        self._update_gui_timer("00:00:00") # Reset timer display
        self._show_gui_status_message("Recording stopped. Transcribing...")

        if self.recording_filepath and os.path.exists(self.recording_filepath):
            logger.info(f"Recording saved to: {self.recording_filepath}")
            threading.Thread(target=self._transcribe_and_update, args=(self.recording_filepath,), daemon=True).start()
        else:
            logger.error(f"Failed to save recording or file not found. Path: {self.recording_filepath}")
            self._update_gui_status(STATUS_ERROR + ": Save Fail", "red")
            self._show_gui_status_message("Error saving/finding recording file.", duration=5000)
            self.current_state = AppState.IDLE # Revert to IDLE
            self._set_gui_button_states(start_enabled=True, stop_enabled=False)


    def _transcribe_and_update(self, audio_path):
        logger.info(f"Starting transcription for {audio_path}...")
        transcript, error_msg = self.transcriber.transcribe_audio(audio_path)

        if error_msg:
            logger.error(f"Transcription failed: {error_msg}")
            self._update_gui_transcript(f"Transcription Error: {error_msg}")
            self._update_gui_status(STATUS_ERROR + ": API", "red")
            self._show_gui_status_message(f"Transcription Error: {error_msg[:50]}...", duration=5000)
        elif transcript is not None:
            logger.info("Transcription successful.")
            self._update_gui_transcript(transcript)
            if copy_to_clipboard(transcript):
                self._show_gui_status_message("Transcript copied to clipboard.")
            else:
                self._show_gui_status_message("Transcript ready (clipboard copy failed).", duration=4000)
            self._update_gui_status(STATUS_IDLE, "white")
        else:
            logger.error("Transcription returned no transcript and no error message.")
            self._update_gui_transcript("Transcription failed: Unknown error.")
            self._update_gui_status(STATUS_ERROR + ": Unknown", "red")
            self._show_gui_status_message("Transcription failed (unknown).", duration=5000)

        # Optional: File cleanup
        # if os.path.exists(audio_path):
        #     try:
        #         os.remove(audio_path)
        #         logger.info(f"Deleted recording file: {audio_path}")
        #     except OSError as e:
        #         logger.error(f"Error deleting recording file {audio_path}: {e}")

        self.current_state = AppState.IDLE
        self._set_gui_button_states(start_enabled=True, stop_enabled=False)
        logger.info("Processing finished. App back to IDLE state.")


    def toggle_recording_state(self):
        logger.debug(f"Toggle recording requested. Current state: {self.current_state.name}")
        if self.current_state == AppState.IDLE:
            self.start_recording()
        elif self.current_state == AppState.RECORDING:
            self.stop_recording_and_process()
        elif self.current_state == AppState.PROCESSING:
            logger.warning("Toggle requested while processing, ignoring.")
            self._show_gui_status_message("Processing... please wait.", duration=2000)


    def run(self):
        logger.info("Starting application UI and hotkey listener...")

        if not self.hotkey_manager.start_listening():
            # Log and show message in GUI status bar, but continue running
            logger.error("CRITICAL: Hotkey listener failed to start. Hotkeys will not function. Check logs for errors (e.g., Linux permissions).")
            self.gui.gui_queue.put(("show_status_message", {"text": "ERROR: Hotkeys disabled! Check logs.", "duration": 10000}))
            # You might want to show a popup here too, but the status bar message is a start.

        try:
            self.gui.run_ui_blocking() # This will block until the GUI is closed.
        except Exception as e:
            logger.critical(f"An unexpected error occurred in the main application run loop: {e}", exc_info=True)
        finally:
            logger.info("Application shutting down...")
            if self.hotkey_manager:
                self.hotkey_manager.stop_listening()

            # If recording was active, ensure it's stopped and threads are signaled
            if self.current_state == AppState.RECORDING:
                logger.warning("Application shutting down during recording. Attempting to stop.")
                self.audio_capture_active = False # Stop capture loop
                # Note: stop_recording() saves the file. If mid-transcription, that's harder to handle gracefully here.
                # For now, just ensure recording resources are freed.
                if self.recorder and self.recorder.is_recording:
                    self.recorder.stop_recording()
            elif self.current_state == AppState.PROCESSING and self.recorder.is_recording :
                 # If it was processing but somehow recorder still thinks it's on
                if self.recorder and self.recorder.is_recording:
                    self.recorder.stop_recording()

            logger.info("Shutdown complete.")


if __name__ == "__main__":
    load_dotenv() # Load .env variables for the check below
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("MODEL_NAME")

    if not api_key or api_key == "YOUR_OPENAI_API_KEY_HERE":
        warning_message = "OPENAI_API_KEY is not set or is a placeholder in .env. Transcription will fail."
        logger.warning(warning_message)
        # If PySimpleGUI is available, show a popup. This runs before GUI fully initializes.
        try:
            import PySimpleGUI as sg
            sg.popup_error("OpenAI API Key Missing", warning_message, title="Configuration Error")
        except Exception as e:
            logger.error(f"Could not show API key warning popup: {e}")
            print(f"WARNING: {warning_message}") # Fallback to console

    if not model_name:
        logger.warning("MODEL_NAME not found in .env, will default to 'gpt-4o' in OpenAITranscriber.")


    app = TranscriptionApp()
    app.run()
