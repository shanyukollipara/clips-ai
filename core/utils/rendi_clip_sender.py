import subprocess
import os
import tempfile
from django.conf import settings
from typing import Dict, Optional

class FFmpegClipProcessor:
    """Local FFmpeg processor for creating video clips"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def create_clip(self, input_path: str, start_time: float, end_time: float, 
                   output_filename: Optional[str] = None) -> Dict:
        """
        Create a video clip using local FFmpeg
        
        Args:
            input_path: Path to the source video file
            start_time: Start time in seconds
            end_time: End time in seconds
            output_filename: Output filename (optional)
            
        Returns:
            Dictionary containing clip info and output path
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video file not found: {input_path}")
        
        # Generate output filename if not provided
        if not output_filename:
            import uuid
            output_filename = f"clip_{uuid.uuid4().hex[:8]}.mp4"
        
        # Create output path
        output_path = os.path.join(self.temp_dir, output_filename)
        
        # Build FFmpeg command for vertical 9:16 format
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', input_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-vf', 'scale=720:1280,crop=ih*9/16:ih',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'fast',
            '-crf', '23',
            '-movflags', '+faststart',
            '-y',  # Overwrite output file if it exists
            output_path
        ]
        
        try:
            # Run FFmpeg command
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check if output file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                return {
                    'success': True,
                    'output_path': output_path,
                    'output_filename': output_filename,
                    'file_size': file_size,
                    'duration': end_time - start_time,
                    'resolution': '720x1280',
                    'ffmpeg_output': result.stdout,
                    'ffmpeg_stderr': result.stderr
                }
            else:
                raise Exception("FFmpeg completed but output file not found")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg failed: {e.stderr}")
        except Exception as e:
            raise Exception(f"Failed to create clip: {str(e)}")
    
    def get_video_info(self, input_path: str) -> Dict:
        """
        Get video information using FFprobe
        
        Args:
            input_path: Path to the video file
            
        Returns:
            Dictionary containing video metadata
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Video file not found: {input_path}")
        
        ffprobe_cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            input_path
        ]
        
        try:
            result = subprocess.run(
                ffprobe_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            info = json.loads(result.stdout)
            
            # Extract relevant information
            format_info = info.get('format', {})
            video_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), {})
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'file_size': int(format_info.get('size', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'codec': video_stream.get('codec_name', ''),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'format': format_info.get('format_name', '')
            }
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFprobe failed: {e.stderr}")
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up a video file
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted successfully
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def is_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg is available on the system
        
        Returns:
            True if FFmpeg is available
        """
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False 