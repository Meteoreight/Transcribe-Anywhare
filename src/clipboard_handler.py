import pyperclip
from .logger_setup import get_logger

logger = get_logger(__name__)

def copy_to_clipboard(text: str):
    """
    Copies the given text to the OS clipboard.
    """
    try:
        pyperclip.copy(text)
        logger.info("Text successfully copied to clipboard.")
        return True
    except pyperclip.PyperclipException as e:
        # This can happen if a copy/paste mechanism is not available.
        # For example, on Linux, if 'xclip' or 'xsel' is not installed.
        logger.error(f"Error copying to clipboard: {e}")
        logger.error("Please ensure you have a copy/paste mechanism installed (e.g., xclip or xsel on Linux).")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while copying to clipboard: {e}")
        return False

if __name__ == '__main__':
    # Adjust path for direct execution
    import os
    import sys
    if __package__ is None:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        # Re-import logger if necessary, or ensure it's available
        from src.logger_setup import get_logger
        # logger = get_logger(__name__) # Re-initialize if it wasn't picked up

    logger.info("Clipboard Handler Example")

    test_text_1 = "Hello, this is a test string for the clipboard!"
    logger.info(f"Attempting to copy: \"{test_text_1}\"")
    if copy_to_clipboard(test_text_1):
        logger.info("Verify by pasting the text into another application.")
        try:
            pasted_text = pyperclip.paste()
            logger.info(f"Pasted text (for verification): \"{pasted_text}\"")
            if pasted_text == test_text_1:
                logger.info("Clipboard copy and paste verified successfully!")
            else:
                logger.warning("Pasted text does not match original. This might be due to environment limitations or other clipboard interference.")
        except pyperclip.PyperclipException as e:
            logger.warning(f"Could not verify paste: {e}. This is expected in some CI/headless environments.")
    else:
        logger.error("Failed to copy text to clipboard.")

    test_text_2 = "Another test with\nmultiline content and special characters: ©µηι¢ø∂€"
    logger.info(f"Attempting to copy: \"{test_text_2}\"")
    if copy_to_clipboard(test_text_2):
        logger.info("Verify by pasting.")
    else:
        logger.error("Failed to copy second text to clipboard.")

    # Test with empty string
    logger.info("Attempting to copy an empty string.")
    if copy_to_clipboard(""):
        logger.info("Empty string copied. Verify by pasting.")
    else:
        logger.error("Failed to copy empty string.")
