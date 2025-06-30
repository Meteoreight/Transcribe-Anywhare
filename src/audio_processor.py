import os
import tempfile
from pydub import AudioSegment
from .logger_setup import get_logger

logger = get_logger(__name__)

class AudioProcessor:
    def __init__(self):
        pass
    
    def convert_to_x2_speed(self, input_path: str) -> str:
        """
        Convert audio file to 2x speed and return path to the new file.
        
        Args:
            input_path: Path to the original audio file
            
        Returns:
            Path to the speed-converted audio file
        """
        try:
            logger.info(f"Converting audio to 2x speed: {input_path}")
            
            # Load the audio file
            audio = AudioSegment.from_wav(input_path)
            
            # Speed up by 2x (this reduces duration by half)
            # speedup_audio changes playback speed without changing pitch
            sped_up_audio = audio.speedup(playback_speed=2.0)
            
            # Create temporary file for the sped-up version
            temp_dir = os.path.dirname(input_path)
            temp_filename = f"x2_{os.path.basename(input_path)}"
            output_path = os.path.join(temp_dir, temp_filename)
            
            # Export the sped-up audio
            sped_up_audio.export(output_path, format="wav")
            
            logger.info(f"Successfully converted to 2x speed: {output_path}")
            logger.debug(f"Original duration: {len(audio)}ms, New duration: {len(sped_up_audio)}ms")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to convert audio to 2x speed: {e}", exc_info=True)
            # Return original path if conversion fails
            return input_path
    
    def cleanup_temp_file(self, file_path: str):
        """
        Clean up temporary files created during processing.
        
        Args:
            file_path: Path to the file to be deleted
        """
        try:
            if os.path.exists(file_path) and "x2_" in os.path.basename(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {file_path}: {e}")