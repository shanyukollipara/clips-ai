import os
import tempfile
import logging
import traceback
from typing import List, Dict
from datetime import datetime
from django.conf import settings

from .apify_client import ApifyClient
from .gemini_analyzer import GeminiAnalyzer
from .yt_downloader import YouTubeDownloader
from .ffmpeg_processor import FFmpegClipProcessor

# Set up logging
logger = logging.getLogger(__name__)

class VideoProcessor:
    """Main processor for creating viral clips from YouTube videos"""
    
    def __init__(self):
        logger.debug("🔧 Initializing VideoProcessor components...")
        try:
            self.apify_client = ApifyClient()
            logger.debug("✅ ApifyClient initialized")
        except Exception as e:
            logger.error(f"❌ ApifyClient initialization failed: {str(e)}")
            raise
        
        try:
            self.gemini_analyzer = GeminiAnalyzer()
            logger.debug("✅ GeminiAnalyzer initialized")
        except Exception as e:
            logger.error(f"❌ GeminiAnalyzer initialization failed: {str(e)}")
            raise
        
        try:
            self.yt_downloader = YouTubeDownloader()
            logger.debug("✅ YouTubeDownloader initialized")
        except Exception as e:
            logger.error(f"❌ YouTubeDownloader initialization failed: {str(e)}")
            raise
        
        try:
            self.ffmpeg_processor = FFmpegClipProcessor()
            logger.debug("✅ FFmpegClipProcessor initialized")
        except Exception as e:
            logger.error(f"❌ FFmpegClipProcessor initialization failed: {str(e)}")
            raise
        
        logger.info("🎬 VideoProcessor fully initialized")
    
    def process_video(self, youtube_url: str, clip_duration: int) -> Dict:
        """
        Process a YouTube video to create viral clips with comprehensive debugging
        
        Args:
            youtube_url: YouTube video URL
            clip_duration: Desired clip duration in seconds
            
        Returns:
            Dictionary containing processing results and clip data
        """
        video_file_path = None
        clip_files = []
        step = "initialization"
        
        try:
            logger.info(f"🎬 Starting video processing for: {youtube_url}")
            logger.debug(f"📊 Processing parameters: duration={clip_duration}s")
            
            # Step 1: Check FFmpeg availability
            step = "ffmpeg_check"
            logger.debug("🔍 Checking FFmpeg availability...")
            if not self.ffmpeg_processor.is_ffmpeg_available():
                error_msg = "FFmpeg is not installed or not available in PATH"
                logger.error(f"❌ {error_msg}")
                raise Exception(error_msg)
            logger.info("✅ FFmpeg is available")
            
            # Step 2: Fetch transcript using Apify
            step = "transcript_fetch"
            logger.info("🎬 Fetching YouTube transcript...")
            transcript_start_time = datetime.now()
            
            try:
                transcript_data = self.apify_client.fetch_transcript(youtube_url)
                transcript_end_time = datetime.now()
                transcript_time = (transcript_end_time - transcript_start_time).total_seconds()
                logger.info(f"✅ Transcript fetched in {transcript_time:.2f}s")
                logger.debug(f"📊 Transcript data keys: {list(transcript_data.keys())}")
            except Exception as e:
                logger.error(f"❌ Transcript fetch failed: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise Exception(f"Transcript fetch failed: {str(e)}")
            
            # Validate transcript data
            if not transcript_data:
                logger.error("❌ Empty transcript data received")
                raise Exception("Empty transcript data received")
            
            video_title = transcript_data.get('title', 'Unknown')
            video_duration = transcript_data.get('duration', 0)
            transcript_segments = transcript_data.get('transcript', [])
            
            logger.info(f"📹 Video: '{video_title}' ({video_duration}s)")
            logger.info(f"🔢 Transcript segments: {len(transcript_segments)}")
            
            if not transcript_segments:
                logger.error("❌ No transcript segments found")
                raise Exception("No transcript segments found")
            
            # Log sample transcript segments
            logger.debug("📝 Sample transcript segments:")
            for i, segment in enumerate(transcript_segments[:3]):
                logger.debug(f"  {i+1}. {segment.get('start', 0):.1f}s: {segment.get('text', '')[:50]}...")
            
            # Step 3: Extract viral moments using Gemini AI
            step = "viral_analysis"
            logger.info("🤖 Analyzing transcript for viral moments with Gemini AI...")
            analysis_start_time = datetime.now()
            
            try:
                viral_moments = self.gemini_analyzer.extract_viral_moments(transcript_data, clip_duration)
                analysis_end_time = datetime.now()
                analysis_time = (analysis_end_time - analysis_start_time).total_seconds()
                logger.info(f"✅ Viral analysis completed in {analysis_time:.2f}s")
                logger.debug(f"📊 Found {len(viral_moments)} potential viral moments")
            except Exception as e:
                logger.error(f"❌ Gemini AI analysis failed: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise Exception(f"Gemini AI analysis failed: {str(e)}")
            
            if not viral_moments:
                logger.error("❌ No viral moments found after analysis")
                raise Exception("No viral moments found after analysis")
            
            # Log viral moments summary
            logger.info("🎯 Viral moments summary:")
            for i, moment in enumerate(viral_moments[:5]):  # Show top 5
                grade = moment.get('grade', self.gemini_analyzer.convert_score_to_grade(moment['virality_score']))
                logger.info(f"  {i+1}. {moment['start_timestamp']:.1f}s-{moment['end_timestamp']:.1f}s: Grade {grade} (Score: {moment['virality_score']:.2f})")
                logger.debug(f"     Justification: {moment.get('justification', 'N/A')[:100]}...")
            
            # Step 4: Download the full video
            step = "video_download"
            logger.info("📥 Downloading full video...")
            download_start_time = datetime.now()
            
            try:
                video_file_path = self.yt_downloader.download_video(youtube_url)
                download_end_time = datetime.now()
                download_time = (download_end_time - download_start_time).total_seconds()
                logger.info(f"✅ Video downloaded in {download_time:.2f}s")
                logger.debug(f"📁 Video file: {video_file_path}")
                
                # Check if file exists (handle both local files and GCS URLs)
                if video_file_path.startswith('https://storage.googleapis.com'):
                    # For GCS URLs, we trust that the upload was successful
                    # The FFmpeg processor will handle downloading it when needed
                    logger.debug("📊 Video uploaded to GCS successfully")
                elif os.path.exists(video_file_path):
                    file_size = os.path.getsize(video_file_path)
                    logger.debug(f"📊 Video file size: {file_size / (1024*1024):.1f} MB")
                else:
                    logger.error("❌ Downloaded video file not found")
                    raise Exception("Downloaded video file not found")
                    
            except Exception as e:
                logger.error(f"❌ Video download failed: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise Exception(f"Video download failed: {str(e)}")
            
            # Step 5: Create clips for each viral moment
            step = "clip_creation"
            logger.info("✂️ Creating viral clips...")
            clips_data = []
            clip_creation_start_time = datetime.now()
            
            for i, moment in enumerate(viral_moments):
                clip_step = f"clip_{i+1}"
                try:
                    grade = moment.get('grade', self.gemini_analyzer.convert_score_to_grade(moment['virality_score']))
                    logger.info(f"📹 Processing clip {i+1}/{len(viral_moments)} - Grade: {grade} (Score: {moment['virality_score']:.2f})")
                    logger.debug(f"⏱️ Clip timing: {moment['start_timestamp']:.1f}s to {moment['end_timestamp']:.1f}s")
                    
                    clip_start_time = datetime.now()
                    clip_result = self.ffmpeg_processor.create_clip(
                        input_path=video_file_path,
                        start_time=moment['start_timestamp'],
                        end_time=moment['end_timestamp'],
                        output_filename=f"viral_clip_{i+1}_{grade.replace('+', 'plus').replace('-', 'minus')}.mp4"
                    )
                    clip_end_time = datetime.now()
                    clip_time = (clip_end_time - clip_start_time).total_seconds()
                    
                    logger.debug(f"✅ Clip {i+1} created in {clip_time:.2f}s")
                    
                    if clip_result.get('output_path'):
                        clip_files.append(clip_result['output_path'])
                        logger.debug(f"📁 Clip saved: {clip_result['output_path']}")
                    else:
                        logger.warning(f"⚠️ Clip {i+1} created but no output path returned")
                    
                    clip_data = {
                        'rank': i + 1,
                        'start_timestamp': moment['start_timestamp'],
                        'end_timestamp': moment['end_timestamp'],
                        'duration': moment['end_timestamp'] - moment['start_timestamp'],
                        'virality_score': moment['virality_score'],
                        'grade': grade,
                        'justification': moment.get('justification', 'Viral potential detected'),
                        'emotional_keywords': moment.get('emotional_keywords', []),
                        'urgency_indicators': moment.get('urgency_indicators', []),
                        'output_path': clip_result.get('output_path'),
                        'clip_filename': clip_result.get('output_filename'),
                        'file_size': clip_result.get('file_size'),
                        'resolution': clip_result.get('resolution'),
                        'creation_time': clip_time,
                        'created_at': self._get_current_timestamp()
                    }
                    clips_data.append(clip_data)
                    
                    logger.info(f"✅ Clip {i+1} completed: {grade} - {clip_data['justification'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"❌ Clip creation failed for clip {i+1}: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    continue
            
            clip_creation_end_time = datetime.now()
            total_clip_time = (clip_creation_end_time - clip_creation_start_time).total_seconds()
            
            logger.info(f"🎯 All clips processed in {total_clip_time:.2f}s")
            logger.info(f"✅ Successfully created {len(clips_data)}/{len(viral_moments)} clips")
            
            if not clips_data:
                logger.error("❌ No clips were successfully created")
                raise Exception("No clips were successfully created")
            
            # Calculate processing statistics
            processing_stats = {
                'total_processing_time': total_clip_time,
                'transcript_fetch_time': transcript_time if 'transcript_time' in locals() else 0,
                'analysis_time': analysis_time if 'analysis_time' in locals() else 0,
                'download_time': download_time if 'download_time' in locals() else 0,
                'clip_creation_time': total_clip_time,
                'avg_virality_score': sum(clip['virality_score'] for clip in clips_data) / len(clips_data),
                'top_grade': clips_data[0]['grade'] if clips_data else 'N/A',
                'grade_distribution': self._calculate_grade_distribution(clips_data),
                'clips_created': len(clips_data),
                'clips_attempted': len(viral_moments)
            }
            
            result = {
                'success': True,
                'youtube_url': youtube_url,
                'clip_duration': clip_duration,
                'video_info': {
                    'title': video_title,
                    'duration': video_duration,
                    'video_id': transcript_data.get('video_id', ''),
                    'transcript_length': len(transcript_segments),
                    'file_size': file_size if 'file_size' in locals() else 0
                },
                'clips': clips_data,
                'total_clips': len(clips_data),
                'processing_stats': processing_stats
            }
            
            logger.info(f"🎉 Processing completed successfully!")
            logger.info(f"📊 Final stats: {len(clips_data)} clips, avg score: {processing_stats['avg_virality_score']:.2f}")
            return result
            
        except Exception as e:
            error_msg = f"Processing failed at step '{step}': {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            return {
                'success': False,
                'error': error_msg,
                'youtube_url': youtube_url,
                'clip_duration': clip_duration,
                'step_failed': step,
                'traceback': traceback.format_exc(),
                'debug_info': {
                    'step': step,
                    'video_file_path': video_file_path,
                    'clips_created': len(clip_files)
                }
            }
            
        finally:
            # Clean up downloaded video file
            if video_file_path:
                logger.info("🧹 Cleaning up downloaded video...")
                try:
                    # Handle both local files and GCS URLs
                    if video_file_path.startswith('https://storage.googleapis.com'):
                        # For GCS URLs, use the yt_downloader cleanup which handles GCS deletion
                        self.yt_downloader.cleanup_file(video_file_path)
                        logger.debug("✅ GCS video file cleaned up")
                    elif os.path.exists(video_file_path):
                        # For local files, use the standard cleanup
                        self.yt_downloader.cleanup_file(video_file_path)
                        logger.debug("✅ Local video file cleaned up")
                    else:
                        logger.debug("📁 Video file already cleaned up or not found")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to clean up video file: {str(e)}")
            
            # Keep clip files for serving (don't clean them up)
            logger.info(f"💾 Keeping {len(clip_files)} generated clips for download")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    def _calculate_grade_distribution(self, clips_data: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of grades across clips"""
        distribution = {}
        for clip in clips_data:
            grade = clip.get('grade', 'Unknown')
            distribution[grade] = distribution.get(grade, 0) + 1
        return distribution
    
    def get_processing_status(self, processing_id: str) -> Dict:
        """
        Get the status of a processing job
        
        Args:
            processing_id: Processing job ID
            
        Returns:
            Dictionary containing processing status
        """
        logger.debug(f"🔍 Checking processing status for ID: {processing_id}")
        # This would typically check a database or job queue
        # For now, return a simple status
        return {
            'processing_id': processing_id,
            'status': 'completed',
            'message': 'Processing completed successfully'
        } 