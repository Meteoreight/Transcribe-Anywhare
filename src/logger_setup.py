import logging
import os
from logging.handlers import RotatingFileHandler

# Define project root as one level up from the 'src' directory where this file is located
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')

# Create logs directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)
    # print(f"Created logs directory: {LOGS_DIR}") # For debugging

log_file_path = os.path.join(LOGS_DIR, 'transcription_app.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file_path, maxBytes=1024*1024*5, backupCount=5), # 5 MB per file, 5 backup files
        logging.StreamHandler() # Also log to console
    ]
)

def get_logger(name):
    return logging.getLogger(name)

if __name__ == '__main__':
    # Example usage
    logger = get_logger(__name__)
    logger.info("Logging setup complete. This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
