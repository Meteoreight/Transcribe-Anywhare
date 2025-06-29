import PySimpleGUI as sg
import threading
import queue # For thread-safe communication with the GUI
from .logger_setup import get_logger

logger = get_logger(__name__)

# --- Constants ---
APP_TITLE = "Transcription App"
STATUS_IDLE = "Status: Idle"
STATUS_RECORDING = "● Recording..."
STATUS_TRANSCRIBING = "Transcribing..."
STATUS_ERROR = "Error!"

# --- Themes ---
sg.theme("DarkGrey5") # Or choose another theme you like

class TranscriptionGUI:
    def __init__(self, button_callback=None): # Added button_callback
        self.window = None
        self.recording_status_text = STATUS_IDLE
        self.transcript_text = ""
        self.button_callback = button_callback # Store the callback

        # Queue for updates from other threads to the GUI
        self.gui_queue = queue.Queue()

        # --- Layout Definition ---
        self.layout = [
            [
                sg.Text(self.recording_status_text, key="-STATUS_INDICATOR-", size=(20,1), font=("Helvetica", 10, "bold")),
                sg.Text("00:00:00", key="-TIMER-", size=(10,1), justification="right")
            ],
            [
                sg.Text("Reference:", size=(10,1), font=("Helvetica", 8)),
                sg.Text("Not loaded", key="-REFERENCE_STATUS-", size=(20,1), font=("Helvetica", 8), text_color="gray")
            ],
            [
                sg.Button("Start Recording", key="-START_BUTTON-", expand_x=True),
                sg.Button("Stop Recording", key="-STOP_BUTTON-", expand_x=True, disabled=True)
            ],
            [sg.Text("Last Transcript:", font=("Helvetica", 10, "underline"))],
            [
                sg.Multiline(
                    self.transcript_text,
                    key="-TRANSCRIPT_AREA-",
                    size=(60, 10), # width, height in characters/rows
                    disabled=True,
                    autoscroll=True,
                    expand_x=True,
                    expand_y=True
                )
            ],
            [sg.StatusBar("", key="-STATUS_BAR-", size=(60,1))]
        ]

    def _create_window(self):
        if self.window:
            self.window.close()

        # For a floating window, some parameters might be needed depending on OS and final behavior.
        # PySimpleGUI doesn't have a direct "always on top" for all OSes without some platform-specific code.
        # For now, it will be a standard window.
        self.window = sg.Window(
            APP_TITLE,
            self.layout,
            finalize=True, # Important for later updates
            # keep_on_top=True, # This can be enabled but might have platform issues
            resizable=True,
            # element_justification='center', # If you want elements centered
        )
        logger.info("GUI Window created.")

    def update_status_indicator(self, status: str, color: str = "white"):
        self.recording_status_text = status
        if self.window:
            self.window["-STATUS_INDICATOR-"].update(value=status, text_color=color)
            logger.debug(f"Status indicator updated to: {status}")

    def update_timer(self, time_str: str):
        if self.window:
            self.window["-TIMER-"].update(value=time_str)

    def update_transcript_area(self, text: str):
        self.transcript_text = text
        if self.window:
            self.window["-TRANSCRIPT_AREA-"].update(value=text)
            logger.debug("Transcript area updated.")

    def enable_start_button(self, enabled: bool = True):
        if self.window:
            self.window["-START_BUTTON-"].update(disabled=not enabled)

    def enable_stop_button(self, enabled: bool = True):
        if self.window:
            self.window["-STOP_BUTTON-"].update(disabled=not enabled)

    def show_status_message(self, message: str, duration_ms: int = 3000):
        if self.window:
            self.window["-STATUS_BAR-"].update(value=message)
            # Basic way to clear status after duration. For more complex needs, use a timer event.
            # This might block if not handled carefully, using queue for this is better.
            # For now, we'll just update. Clearing will be part of event loop.
            logger.info(f"Status bar: {message}")

    def update_reference_status(self, status_text: str, color: str = "green"):
        """Update the reference file status display"""
        if self.window:
            self.window["-REFERENCE_STATUS-"].update(value=status_text, text_color=color)
            logger.debug(f"Reference status updated to: {status_text}")


    def _handle_gui_queue_updates(self):
        """Process messages from the GUI queue."""
        try:
            while True:
                message_type, data = self.gui_queue.get_nowait()
                if message_type == "update_status":
                    self.update_status_indicator(data.get("text"), data.get("color", "white"))
                elif message_type == "update_timer":
                    self.update_timer(data)
                elif message_type == "update_transcript":
                    self.update_transcript_area(data)
                elif message_type == "set_button_states":
                    self.enable_start_button(data.get("start_enabled", True))
                    self.enable_stop_button(data.get("stop_enabled", False))
                elif message_type == "show_status_message":
                    self.show_status_message(data.get("text"), data.get("duration", 3000))
                elif message_type == "update_reference_status":
                    self.update_reference_status(data.get("text"), data.get("color", "green"))
                # Add more message types as needed
                self.gui_queue.task_done()
        except queue.Empty:
            pass # No messages in queue

    def run_ui_blocking(self):
        """
        Runs the GUI event loop. This is a blocking call.
        In the main app, this might run in its own thread if other background tasks
        (like global hotkey listener) need to run concurrently without PySimpleGUI's own threading.
        However, PySimpleGUI itself is typically run in the main thread.
        """
        self._create_window()

        # --- Event Loop ---
        while True:
            event, values = self.window.read(timeout=100) # Timeout allows queue checks

            self._handle_gui_queue_updates() # Check for updates from other threads

            if event == sg.WIN_CLOSED:
                logger.info("GUI window closed by user.")
                break

            if event == "-START_BUTTON-" or event == "-STOP_BUTTON-":
                logger.info(f"GUI Button '{event}' pressed.")
                if self.button_callback:
                    try:
                        self.button_callback() # Call the main app's toggle logic
                    except Exception as e:
                        logger.error(f"Error executing button callback: {e}", exc_info=True)
                        self.gui_queue.put(("show_status_message", {"text": f"Error: {e}", "duration": 5000}))
                else:
                    logger.warning("Button pressed, but no callback registered with GUI.")
                    # Fallback to old simulation if no callback (optional, or remove)
                    if event == "-START_BUTTON-":
                        self.gui_queue.put(("update_status", {"text": STATUS_RECORDING, "color": "red"}))
                        self.gui_queue.put(("set_button_states", {"start_enabled": False, "stop_enabled": True}))
                    elif event == "-STOP_BUTTON-":
                         self.gui_queue.put(("update_status", {"text": STATUS_IDLE, "color": "white"}))
                         self.gui_queue.put(("set_button_states", {"start_enabled": True, "stop_enabled": False}))


        if self.window:
            self.window.close()
            self.window = None
        logger.info("GUI event loop finished.")

    def close(self):
        if self.window:
            self.window.close()
            self.window = None
        logger.info("GUI closed via method call.")

if __name__ == '__main__':
    # Adjust path for direct execution
    import os
    import sys
    if __package__ is None: # or not __package__
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from src.logger_setup import get_logger
        # logger = get_logger(__name__) # Re-initialize if needed

    logger.info("Starting Transcription GUI example...")

    gui = TranscriptionGUI()

    # Example of how another thread might send updates (for testing queue)
    def example_background_updates(gui_queue):
        import time
        time.sleep(3)
        gui_queue.put(("update_transcript", "Transcript update from background thread after 3s."))
        gui_queue.put(("show_status_message", {"text": "Background task updated transcript."}))
        time.sleep(2)
        gui_queue.put(("update_timer", "00:00:05")) # Example timer update

    # In a real app, the main controller would hold the gui_queue.
    # threading.Thread(target=example_background_updates, args=(gui.gui_queue,), daemon=True).start()

    try:
        gui.run_ui_blocking()
    except Exception as e:
        logger.error(f"An error occurred running the GUI: {e}", exc_info=True)

    logger.info("Transcription GUI example finished.")
