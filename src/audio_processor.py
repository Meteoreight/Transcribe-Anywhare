import os
import tempfile
from pydub import AudioSegment
from .logger_setup import get_logger

logger = get_logger(__name__)

class AudioProcessor:
    def __init__(self):
        # Supported audio and video extensions
        self.supported_audio_formats = ['.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg']
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    
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
    
    def is_supported_file(self, file_path: str) -> bool:
        """
        Check if the file format is supported for processing.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file format is supported, False otherwise
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in (self.supported_audio_formats + self.supported_video_formats)
    
    def is_video_file(self, file_path: str) -> bool:
        """
        Check if the file is a video file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file is a video file, False otherwise
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in self.supported_video_formats
    
    def extract_audio_from_video(self, video_path: str) -> str:
        """
        Extract audio from video file and save as WAV.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the extracted audio file (WAV format)
        """
        try:
            logger.info(f"Extracting audio from video: {video_path}")
            
            # Load the video file
            audio = AudioSegment.from_file(video_path)
            
            # Create output path for extracted audio
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(video_dir, f"extracted_{video_name}.wav")
            
            # Export as WAV
            audio.export(output_path, format="wav")
            
            logger.info(f"Successfully extracted audio to: {output_path}")
            logger.debug(f"Audio duration: {len(audio)}ms")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to extract audio from video: {e}", exc_info=True)
            raise
    
    def convert_to_wav(self, input_path: str) -> str:
        """
        Convert audio file to WAV format for transcription.
        
        Args:
            input_path: Path to the input audio/video file
            
        Returns:
            Path to the converted WAV file
        """
        try:
            # If it's already a WAV file, return as-is
            if input_path.lower().endswith('.wav'):
                logger.info(f"File is already in WAV format: {input_path}")
                return input_path
            
            logger.info(f"Converting file to WAV format: {input_path}")
            
            # Load the audio/video file
            audio = AudioSegment.from_file(input_path)
            
            # Create output path
            file_dir = os.path.dirname(input_path)
            file_name = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(file_dir, f"converted_{file_name}.wav")
            
            # Export as WAV
            audio.export(output_path, format="wav")
            
            logger.info(f"Successfully converted to WAV: {output_path}")
            logger.debug(f"Audio duration: {len(audio)}ms")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to convert file to WAV: {e}", exc_info=True)
            raise
    
    def prepare_file_for_transcription(self, input_path: str) -> str:
        """
        Prepare any supported audio/video file for transcription by converting to WAV.
        
        Args:
            input_path: Path to the input file
            
        Returns:
            Path to the WAV file ready for transcription
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if not self.is_supported_file(input_path):
            raise ValueError(f"Unsupported file format: {input_path}")
        
        logger.info(f"Preparing file for transcription: {input_path}")
        
        # Convert to WAV format (handles both audio and video files)
        wav_path = self.convert_to_wav(input_path)
        
        logger.info(f"File prepared for transcription: {wav_path}")
        return wav_path
    
    def cleanup_temp_file(self, file_path: str):
        """
        Clean up temporary files created during processing.
        
        Args:
            file_path: Path to the file to be deleted
        """
        try:
            if os.path.exists(file_path):
                # Clean up files with specific prefixes indicating they are temporary
                file_name = os.path.basename(file_path)
                if any(prefix in file_name for prefix in ["x2_", "extracted_", "converted_"]):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {file_path}: {e}")