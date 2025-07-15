import os
import subprocess
import logging
from typing import Dict, Optional
from django.conf import settings
from urllib.parse import unquote

logger = logging.getLogger(__name__)

class FFmpegClipProcessor:
    """FFmpeg-based video clip processor"""
    
    def __init__(self):
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.clips_dir = os.path.join(self.media_root, 'clips')
        
        # Create clips directory if it doesn't exist
        os.makedirs(self.clips_dir, exist_ok=True)
        
        # Try to initialize GCS storage, but don't fail if it's not available
        self.gcs = None
        self.use_gcs = False
        
        try:
            from .gcs_storage import GCSStorage
            self.gcs = GCSStorage()
            self.use_gcs = True
            logger.info("✅ GCS storage initialized - clips will be uploaded to cloud")
        except Exception as e:
            logger.warning(f"⚠️ GCS storage not available: {str(e)}")
            logger.info("📁 Using local file storage only for clips")
    
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
        Create a video clip using FFmpeg and optionally upload to GCS
        
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
            logger.debug(f"🎬 Creating clip: {start_time}s - {end_time}s ({duration}s)")
            
            # Create output path
            local_output_path = os.path.join(self.clips_dir, output_filename)
            logger.debug(f"📁 Output path: {local_output_path}")
            
            # Handle input file (GCS URL or local path)
            local_input_path = input_path
            cleanup_input = False
            
            # If input is GCS URL, download it first (only if GCS is available)
            if input_path.startswith('https://storage.googleapis.com'):
                if self.use_gcs and self.gcs:
                    try:
                        # Extract and decode the blob name from the GCS URL
                        url_parts = input_path.split('/')
                        bucket_index = url_parts.index('clips-ai')
                        blob_name = '/'.join(url_parts[bucket_index + 1:])
                        blob_name = unquote(blob_name)  # URL decode
                        
                        logger.debug(f"🔍 Extracting blob name: {blob_name}")
                        
                        local_input_path = os.path.join(self.media_root, 'downloads', os.path.basename(blob_name))
                        os.makedirs(os.path.dirname(local_input_path), exist_ok=True)
                        
                        if not self.gcs.download_file(blob_name, local_input_path):
                            raise Exception("Failed to download input video from GCS")
                        
                        cleanup_input = True
                        logger.debug(f"✅ Downloaded from GCS: {local_input_path}")
                    except Exception as e:
                        logger.error(f"❌ Failed to download from GCS: {str(e)}")
                        raise Exception(f"Failed to download input video from GCS: {str(e)}")
                else:
                    raise Exception("Input is GCS URL but GCS storage is not available")
            
            # Probe input file first
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,duration',
                '-of', 'json',
                local_input_path
            ]
            
            logger.debug(f"🔍 Probing input file: {local_input_path}")
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            if probe_result.returncode != 0:
                raise Exception(f"FFprobe failed: {probe_result.stderr}")
            
            # FFmpeg command to create clip with better error handling
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-ss', str(start_time),  # Seek position
                '-i', local_input_path,  # Input file
                '-t', str(duration),  # Duration
                '-c:v', 'libx264',  # Video codec
                '-c:a', 'aac',  # Audio codec
                '-preset', 'fast',  # Encoding preset
                '-crf', '23',  # Quality
                '-movflags', '+faststart',  # Web playback optimization
                '-avoid_negative_ts', 'make_zero',  # Fix timestamp issues
                local_output_path
            ]
            
            logger.info(f"🎬 Running FFmpeg to create clip...")
            
            # Run FFmpeg command with full output capture
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"⚠️ FFmpeg stderr: {result.stderr}")
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            # Verify output file exists and has size
            if not os.path.exists(local_output_path):
                raise Exception("Output file not created")
            
            file_size = os.path.getsize(local_output_path)
            if file_size == 0:
                raise Exception("Output file is empty")
            
            logger.debug(f"✅ Clip created locally: {file_size} bytes")
            
            # Get video resolution
            resolution = self._get_video_resolution(local_output_path)
            
            # Try to upload to GCS if available
            final_path = local_output_path
            if self.use_gcs and self.gcs:
                try:
                    gcs_path = f"clips/{output_filename}"
                    gcs_url = self.gcs.upload_file(local_output_path, gcs_path)
                    
                    # Clean up local file after successful upload
                    os.remove(local_output_path)
                    final_path = gcs_url
                    logger.info(f"✅ Clip uploaded to GCS: {gcs_url}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to upload clip to GCS: {str(e)}")
                    logger.info("📁 Keeping clip in local storage")
            else:
                logger.info(f"📁 Clip stored locally: {local_output_path}")
            
            # Clean up input file if it was downloaded
            if cleanup_input and os.path.exists(local_input_path):
                try:
                    os.remove(local_input_path)
                    logger.debug(f"🧹 Cleaned up downloaded input: {local_input_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup input file: {str(e)}")
            
            logger.info(f"✅ Clip created successfully: {file_size} bytes, resolution: {resolution}")
            
            return {
                'success': True,
                'output_path': final_path,
                'output_filename': output_filename,
                'file_size': file_size,
                'resolution': resolution,
                'duration': duration,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg command timed out"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Failed to create clip: {str(e)}"
            logger.error(f"❌ {error_msg}")
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
            logger.warning(f"⚠️ Failed to get video resolution: {str(e)}")
            return None
    
    def cleanup_file(self, file_path: str):
        """Clean up a file if it exists"""
        try:
            # If it's a GCS URL, extract the path and delete from GCS
            if file_path.startswith('https://storage.googleapis.com'):
                if self.use_gcs and self.gcs:
                    # Extract and decode the blob name from the GCS URL
                    url_parts = file_path.split('/')
                    bucket_index = url_parts.index('clips-ai')
                    blob_name = '/'.join(url_parts[bucket_index + 1:])
                    blob_name = unquote(blob_name)  # URL decode
                    self.gcs.delete_file(blob_name)
                    logger.info(f"🧹 Cleaned up GCS file: {blob_name}")
            elif os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🧹 Cleaned up local file: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup {file_path}: {str(e)}") 