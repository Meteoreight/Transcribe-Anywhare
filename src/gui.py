import flet as ft
import threading
import queue # For thread-safe communication with the GUI

# Handle relative imports for direct execution
try:
    from .logger_setup import get_logger
except ImportError:
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.logger_setup import get_logger

logger = get_logger(__name__)

# --- Constants ---
APP_TITLE = "Transcription App"
STATUS_IDLE = "Status: Idle"
STATUS_RECORDING = "● Recording..."
STATUS_TRANSCRIBING = "Transcribing..."
STATUS_ERROR = "Error!"

class TranscriptionGUI:
    def __init__(self, button_callback=None):
        self.page = None
        self.recording_status_text = STATUS_IDLE
        self.transcript_text = ""
        self.button_callback = button_callback

        # Queue for updates from other threads to the GUI
        self.gui_queue = queue.Queue()

        # UI Controls
        self.status_indicator = None
        self.timer_text = None
        self.reference_status = None
        self.x2_mode_checkbox = None
        self.record_button = None
        self.transcript_area = None
        self.status_bar = None
        self.is_recording = False

    def _build_ui(self, page: ft.Page):
        page.title = APP_TITLE
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_resizable = True
        page.window_width = 600
        page.window_height = 500

        # Initialize UI controls
        self.status_indicator = ft.Text(
            self.recording_status_text,
            size=16,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLACK87,
            expand=True
        )
        
        self.timer_text = ft.Text(
            "00:00:00",
            size=14,
            text_align=ft.TextAlign.RIGHT
        )
        
        self.reference_status = ft.Text(
            "Not loaded",
            size=12,
            color="grey"
        )
        
        self.x2_mode_checkbox = ft.Checkbox(
            label="x2 Speed Mode (Experimental)",
            tooltip="Convert audio to 2x speed before transcription to reduce token usage"
        )
        
        self.record_button = ft.ElevatedButton(
            "Start Recording",
            on_click=self._on_record_click,
            expand=True,
            bgcolor=ft.Colors.GREEN_400,
            color=ft.Colors.WHITE
        )
        
        self.transcript_area = ft.TextField(
            multiline=True,
            read_only=True,
            expand=True,
            min_lines=10,
            max_lines=10
        )
        
        self.status_bar = ft.Text(
            "",
            size=12,
            color="blue"
        )

        # Build the layout
        page.add(
            ft.Column([
                # Status and timer row
                ft.Row([
                    self.status_indicator,
                    self.timer_text
                ]),
                
                # Reference status row
                ft.Row([
                    ft.Text("Reference:", size=12),
                    self.reference_status
                ]),
                
                # x2 mode checkbox
                self.x2_mode_checkbox,
                
                # Record button
                ft.Container(
                    content=self.record_button,
                    alignment=ft.alignment.center
                ),

                # Transcript label
                ft.Text("Last Transcript:", size=14, weight=ft.FontWeight.W_500),
                
                # Transcript area
                self.transcript_area,
                
                # Status bar
                self.status_bar
            ], expand=True, spacing=10)
        )
        
        logger.info("GUI UI built.")
        
    def _on_record_click(self, e):
        if self.is_recording:
            logger.info("Stop recording button clicked.")
        else:
            logger.info("Start recording button clicked.")
        
        if self.button_callback:
            try:
                self.button_callback()
            except Exception as ex:
                logger.error(f"Error executing button callback: {ex}", exc_info=True)
                self.show_status_message(f"Error: {ex}")

    def update_status_indicator(self, status: str, color: str = "black"):
        self.recording_status_text = status
        if self.status_indicator:
            self.status_indicator.value = status
            if color == "red":
                self.status_indicator.color = ft.Colors.RED_600
            elif color == "yellow":
                self.status_indicator.color = ft.Colors.AMBER_600
            elif color == "orange":
                self.status_indicator.color = ft.Colors.ORANGE_600
            else:
                self.status_indicator.color = ft.Colors.BLACK87
            
            # Update recording state and button appearance
            if "Recording" in status:
                self.is_recording = True
                self._update_record_button()
            elif status == STATUS_IDLE:
                self.is_recording = False
                self._update_record_button()
            
            if self.page:
                self.page.update()
            logger.debug(f"Status indicator updated to: {status}")

    def update_timer(self, time_str: str):
        if self.timer_text:
            self.timer_text.value = time_str
            if self.page:
                self.page.update()

    def update_transcript_area(self, text: str):
        self.transcript_text = text
        if self.transcript_area:
            self.transcript_area.value = text
            if self.page:
                self.page.update()
            logger.debug("Transcript area updated.")

    def _update_record_button(self):
        """Update the record button text and color based on current state"""
        if self.record_button:
            if self.is_recording:
                self.record_button.text = "Stop Recording"
                self.record_button.bgcolor = ft.Colors.RED_400
                self.record_button.color = ft.Colors.WHITE
            else:
                self.record_button.text = "Start Recording"
                self.record_button.bgcolor = ft.Colors.GREEN_400
                self.record_button.color = ft.Colors.WHITE
            
            if self.page:
                self.page.update()
    
    def enable_record_button(self, enabled: bool = True):
        """Enable or disable the record button"""
        if self.record_button:
            self.record_button.disabled = not enabled
            if self.page:
                self.page.update()

    def show_status_message(self, message: str, duration_ms: int = 3000):
        if self.status_bar:
            self.status_bar.value = message
            if self.page:
                self.page.update()
            logger.info(f"Status bar: {message}")

    def update_reference_status(self, status_text: str, color: str = "green"):
        """Update the reference file status display"""
        if self.reference_status:
            self.reference_status.value = status_text
            self.reference_status.color = color
            if self.page:
                self.page.update()
            logger.debug(f"Reference status updated to: {status_text}")

    def get_x2_mode_enabled(self):
        """Get the current state of x2 speed mode toggle"""
        if self.x2_mode_checkbox:
            return self.x2_mode_checkbox.value
        return False


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
                    self.enable_record_button(data.get("record_enabled", True))
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
        Runs the GUI using Flet. This is a blocking call.
        """
        def main(page: ft.Page):
            self.page = page
            self._build_ui(page)
            
            # Start background thread to handle queue updates
            threading.Thread(target=self._queue_update_worker, daemon=True).start()
            
        ft.app(target=main)
        logger.info("GUI event loop finished.")
        
    def _queue_update_worker(self):
        """Background worker to handle GUI queue updates"""
        import time
        while True:
            try:
                self._handle_gui_queue_updates()
                time.sleep(0.1)  # Check queue every 100ms
            except Exception as e:
                logger.error(f"Error in queue update worker: {e}", exc_info=True)

    def close(self):
        if self.page:
            self.page.window_close()
            self.page = None
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
    threading.Thread(target=example_background_updates, args=(gui.gui_queue,), daemon=True).start()

    try:
        gui.run_ui_blocking()
    except Exception as e:
        logger.error(f"An error occurred running the GUI: {e}", exc_info=True)

    logger.info("Transcription GUI example finished.")
