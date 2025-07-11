import os
import subprocess
import tempfile
from typing import Dict, Optional
from django.conf import settings

class FFmpegClipProcessor:
    """FFmpeg-based video clip processor"""
    
    def __init__(self):
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.clips_dir = os.path.join(self.media_root, 'clips')
        
        # Create clips directory if it doesn't exist
        os.makedirs(self.clips_dir, exist_ok=True)
    
    def is_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available in the system"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def create_clip(self, input_path: str, start_time: float, end_time: float, 
                   output_filename: str) -> Dict:
        """
        Create a video clip using FFmpeg
        
        Args:
            input_path: Path to input video file
            start_time: Start time in seconds
            end_time: End time in seconds
            output_filename: Name for the output file
            
        Returns:
            Dictionary with clip information
        """
        try:
            # Calculate duration
            duration = end_time - start_time
            
            # Create output path
            output_path = os.path.join(self.clips_dir, output_filename)
            
            # FFmpeg command to create clip
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-crf', '23',
                '-y',  # Overwrite output file
                output_path
            ]
            
            print(f"🎬 Creating clip: {start_time}s - {end_time}s ({duration}s)")
            print(f"📁 Output: {output_path}")
            
            # Run FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            # Get file information
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            # Get video resolution
            resolution = self._get_video_resolution(output_path)
            
            print(f"✅ Clip created successfully: {file_size} bytes")
            
            return {
                'success': True,
                'output_path': output_path,
                'output_filename': output_filename,
                'file_size': file_size,
                'resolution': resolution,
                'duration': duration,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg command timed out"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Failed to create clip: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def _get_video_resolution(self, video_path: str) -> Optional[str]:
        """Get video resolution using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Find video stream
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        width = stream.get('width')
                        height = stream.get('height')
                        if width and height:
                            return f"{width}x{height}"
            
            return None
            
        except Exception:
            return None
    
    def cleanup_file(self, file_path: str):
        """Clean up a file if it exists"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup {file_path}: {str(e)}") 