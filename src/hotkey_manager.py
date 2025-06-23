import keyboard
import time
from .logger_setup import get_logger

logger = get_logger(__name__)

class HotkeyManager:
    def __init__(self, hotkey_str="ctrl+shift+r"):
        self.hotkey_str = hotkey_str
        self._callback = None
        self._is_running = False
        self._is_hooked = False # To track if keyboard.add_hotkey was successful

    def _on_hotkey_pressed(self):
        """Internal wrapper for the callback to log and execute."""
        logger.info(f"Hotkey '{self.hotkey_str}' pressed.")
        if self._callback:
            try:
                self._callback()
            except Exception as e:
                logger.error(f"Error executing hotkey callback: {e}", exc_info=True)
        else:
            logger.warning("Hotkey pressed, but no callback is registered.")

    def register_callback(self, callback_func):
        """
        Registers the function to be called when the hotkey is pressed.
        """
        self._callback = callback_func
        logger.info(f"Callback {callback_func.__name__ if hasattr(callback_func, '__name__') else 'anonymous'} registered for hotkey '{self.hotkey_str}'.")

    def start_listening(self):
        """
        Starts listening for the hotkey.
        This function will block if not run in a separate thread,
        unless keyboard library handles threading internally for add_hotkey.
        The `keyboard` library's `add_hotkey` is non-blocking in terms of setup,
        but relies on its own background listener.
        """
        if self._is_running:
            logger.warning("Hotkey listener is already running.")
            return

        if not self._callback:
            logger.error("Cannot start listening: No callback registered for hotkey.")
            return False

        try:
            # keyboard.add_hotkey is non-blocking in the sense that it sets up the hook
            # and returns. The actual listening happens in a background thread managed by the library.
            keyboard.add_hotkey(self.hotkey_str, self._on_hotkey_pressed, suppress=False) # suppress=False allows the key event to pass through
            self._is_hooked = True
            self._is_running = True
            logger.info(f"Hotkey listener started for '{self.hotkey_str}'. Press the hotkey to trigger.")
            return True
        except Exception as e:
            # This can happen for various reasons, e.g., on Linux if the process doesn't have root access
            # or cannot access /dev/input/event*
            logger.error(f"Failed to set up hotkey '{self.hotkey_str}': {e}", exc_info=True)
            logger.error("On Linux, this might require running as root or specific input group permissions.")
            self._is_hooked = False
            self._is_running = False
            return False

    def stop_listening(self):
        """
        Stops listening for the hotkey.
        """
        if not self._is_running and not self._is_hooked:
            logger.warning("Hotkey listener is not running or was never successfully hooked.")
            return

        try:
            if self._is_hooked: # Only try to remove if it was added
                keyboard.remove_hotkey(self.hotkey_str)
                logger.info(f"Hotkey '{self.hotkey_str}' removed.")
            self._is_hooked = False
        except Exception as e:
            # This can occur if the hotkey was already removed or never properly set.
            logger.warning(f"Error trying to remove hotkey '{self.hotkey_str}': {e}. It might have already been cleared or not set up.")

        self._is_running = False
        logger.info("Hotkey listener stopped.")

    def wait_for_exit(self, exit_hotkey_str=None):
        """
        A utility function to keep the listener active until an exit condition.
        This is mainly for testing or simple scripts. In a GUI app,
        the main app loop keeps things alive.
        If exit_hotkey_str is provided, it sets up another hotkey to stop.
        """
        if not self._is_running:
            logger.warning("Listener is not running, cannot wait.")
            return

        logger.info("Hotkey listener is active. Keep this process running.")
        if exit_hotkey_str:
            logger.info(f"Press '{exit_hotkey_str}' to stop listening and exit this test.")
            keyboard.wait(exit_hotkey_str, suppress=False)
            self.stop_listening() # Stop the main hotkey listener as well
        else:
            # If no specific exit hotkey, just keep alive.
            # This is a naive way; in a real app, the application's main loop handles this.
            # For the `keyboard` library, once `add_hotkey` is called,
            # its internal threads keep listening. This `wait` is more for a console app.
            try:
                while self._is_running: # This loop might not be strictly necessary if keyboard lib handles its thread well
                    time.sleep(0.1) # Keep the main thread alive if needed.
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received. Stopping listener...")
            finally:
                self.stop_listening()


if __name__ == '__main__':
    import os
    import sys
    if __package__ is None:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from src.logger_setup import get_logger
        # logger = get_logger(__name__) # Re-initialize if needed

    logger.info("Hotkey Manager Example")

    # --- Test Callback Function ---
    def my_hotkey_action():
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"--- Hotkey Action Triggered at {timestamp} ---")
        # In a real app, this would toggle recording, update GUI, etc.
        print(f"ACTION: Hotkey was pressed at {timestamp}!")

    hotkey_to_test = "ctrl+shift+a" # Using a different one for test to avoid conflict if main app uses default
    exit_hotkey_for_test = "ctrl+shift+q"

    manager = HotkeyManager(hotkey_str=hotkey_to_test)
    manager.register_callback(my_hotkey_action)

    if manager.start_listening():
        logger.info(f"Listening for '{hotkey_to_test}'. Press these keys to test.")
        logger.info(f"Press '{exit_hotkey_for_test}' to stop this example script.")

        # The keyboard.wait() function blocks the main thread until the specified hotkey is pressed.
        # This is useful for scripts that should run until a certain key combination.
        try:
            keyboard.wait(exit_hotkey_for_test, suppress=False)
            logger.info(f"'{exit_hotkey_for_test}' pressed. Exiting example.")
        except Exception as e:
            logger.error(f"Error during keyboard.wait: {e}")
        finally:
            manager.stop_listening() # Ensure listener is stopped
    else:
        logger.error(f"Could not start hotkey listener for '{hotkey_to_test}'. Check permissions or if another app is grabbing keys.")
        logger.error("On Linux, you might need to run as root or ensure your user has permissions for /dev/input/event*")
        logger.error("Try: 'sudo python src/hotkey_manager.py' if you encounter permission issues during test.")

    logger.info("Hotkey Manager example finished.")
