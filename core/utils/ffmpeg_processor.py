import os
import subprocess
from typing import Dict, Optional
from django.conf import settings
from .gcs_storage import GCSStorage

class FFmpegClipProcessor:
    """FFmpeg-based video clip processor"""
    
    def __init__(self):
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.clips_dir = os.path.join(self.media_root, 'clips')
        self.gcs = GCSStorage()
        
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
        Create a video clip using FFmpeg and upload to GCS
        
        Args:
            input_path: GCS URL or local path to input video file
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
            local_output_path = os.path.join(self.clips_dir, output_filename)
            
            # If input is GCS URL, download it first
            if input_path.startswith('https://storage.googleapis.com'):
                blob_name = input_path.split('/clips-ai/')[-1]
                local_input = os.path.join(self.media_root, 'downloads', os.path.basename(blob_name))
                if not self.gcs.download_file(blob_name, local_input):
                    raise Exception("Failed to download input video from GCS")
                input_path = local_input
            
            # Probe input file first
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,duration',
                '-of', 'json',
                input_path
            ]
            
            print(f"🔍 Probing input file: {input_path}")
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            if probe_result.returncode != 0:
                raise Exception(f"FFprobe failed: {probe_result.stderr}")
            
            # FFmpeg command to create clip with better error handling
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-ss', str(start_time),  # Seek position
                '-i', input_path,  # Input file
                '-t', str(duration),  # Duration
                '-c:v', 'libx264',  # Video codec
                '-c:a', 'aac',  # Audio codec
                '-preset', 'fast',  # Encoding preset
                '-crf', '23',  # Quality
                '-movflags', '+faststart',  # Web playback optimization
                '-avoid_negative_ts', 'make_zero',  # Fix timestamp issues
                local_output_path
            ]
            
            print(f"🎬 Creating clip: {start_time}s - {end_time}s ({duration}s)")
            print(f"📁 Output: {local_output_path}")
            
            # Run FFmpeg command with full output capture
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"⚠️ FFmpeg stderr: {result.stderr}")
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            # Verify output file exists and has size
            if not os.path.exists(local_output_path):
                raise Exception("Output file not created")
            
            file_size = os.path.getsize(local_output_path)
            if file_size == 0:
                raise Exception("Output file is empty")
            
            # Get video resolution
            resolution = self._get_video_resolution(local_output_path)
            
            # Upload to GCS
            gcs_path = f"clips/{output_filename}"
            gcs_url = self.gcs.upload_file(local_output_path, gcs_path)
            
            # Clean up local files
            os.remove(local_output_path)
            if input_path.startswith(self.media_root):
                os.remove(input_path)
            
            print(f"✅ Clip created successfully: {file_size} bytes, resolution: {resolution}")
            
            return {
                'success': True,
                'output_path': gcs_url,
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
            
        except Exception as e:
            print(f"⚠️ Failed to get video resolution: {str(e)}")
            return None
    
    def cleanup_file(self, file_path: str):
        """Clean up a file if it exists"""
        try:
            # If it's a GCS URL, extract the path
            if file_path.startswith('https://storage.googleapis.com'):
                blob_name = file_path.split('/clips-ai/')[-1]
                self.gcs.delete_file(blob_name)
            elif os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup {file_path}: {str(e)}") 