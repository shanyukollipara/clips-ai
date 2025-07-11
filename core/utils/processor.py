import os
import tempfile
from typing import List, Dict
from django.conf import settings

from .apify_client import ApifyClient
from .grok_analyzer import GrokAnalyzer
from .yt_downloader import YouTubeDownloader
from .rendi_clip_sender import FFmpegClipProcessor

class VideoProcessor:
    """Main processor for creating viral clips from YouTube videos"""
    
    def __init__(self):
        self.apify_client = ApifyClient()
        self.grok_analyzer = GrokAnalyzer()
        self.yt_downloader = YouTubeDownloader()
        self.ffmpeg_processor = FFmpegClipProcessor()
    
    def process_video(self, youtube_url: str, clip_duration: int) -> Dict:
        """
        Process a YouTube video to create viral clips
        
        Args:
            youtube_url: YouTube video URL
            clip_duration: Desired clip duration in seconds
            
        Returns:
            Dictionary containing processing results and clip data
        """
        video_file_path = None
        clip_files = []
        
        try:
            # Check if FFmpeg is available
            if not self.ffmpeg_processor.is_ffmpeg_available():
                raise Exception("FFmpeg is not installed or not available in PATH")
            
            # Step 1: Fetch transcript using Apify
            print("Fetching transcript...")
            transcript_data = self.apify_client.fetch_transcript(youtube_url)
            
            # Step 2: Extract viral moments using Grok
            print("Extracting viral moments...")
            viral_moments = self.grok_analyzer.extract_viral_moments(transcript_data, clip_duration)
            
            # Step 3: Download the full video using yt-dlp
            print("Downloading video...")
            video_file_path = self.yt_downloader.download_video(youtube_url)
            
            # Step 4: Create clips for each viral moment using FFmpeg
            print("Creating clips...")
            clips_data = []
            
            for i, moment in enumerate(viral_moments):
                print(f"Processing clip {i+1}/{len(viral_moments)}...")
                
                # Create clip using FFmpeg
                clip_result = self.ffmpeg_processor.create_clip(
                    input_path=video_file_path,
                    start_time=moment['start_timestamp'],
                    end_time=moment['end_timestamp'],
                    output_filename=f"clip_{i+1}.mp4"
                )
                
                # Store clip file path for cleanup
                if clip_result.get('output_path'):
                    clip_files.append(clip_result['output_path'])
                
                # Score the clip for virality
                virality_score = self.grok_analyzer.score_virality(moment)
                
                # Combine clip data
                clip_data = {
                    'start_timestamp': moment['start_timestamp'],
                    'end_timestamp': moment['end_timestamp'],
                    'justification': moment['justification'],
                    'emotional_keywords': moment['emotional_keywords'],
                    'urgency_indicators': moment['urgency_indicators'],
                    'virality_score': virality_score,
                    'clip_path': clip_result.get('output_path'),
                    'clip_filename': clip_result.get('output_filename'),
                    'file_size': clip_result.get('file_size'),
                    'duration': clip_result.get('duration'),
                    'resolution': clip_result.get('resolution')
                }
                
                clips_data.append(clip_data)
            
            # Sort clips by virality score (highest first)
            clips_data.sort(key=lambda x: x['virality_score'] or 0, reverse=True)
            
            return {
                'success': True,
                'youtube_url': youtube_url,
                'clip_duration': clip_duration,
                'video_info': transcript_data,
                'clips': clips_data,
                'total_clips': len(clips_data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'youtube_url': youtube_url,
                'clip_duration': clip_duration
            }
            
        finally:
            # Clean up downloaded video file
            if video_file_path and os.path.exists(video_file_path):
                self.yt_downloader.cleanup_file(video_file_path)
            
            # Clean up clip files (optional - you might want to keep them)
            # for clip_file in clip_files:
            #     if os.path.exists(clip_file):
            #         self.ffmpeg_processor.cleanup_file(clip_file)
    
    def get_processing_status(self, processing_id: str) -> Dict:
        """
        Get the status of a processing job
        
        Args:
            processing_id: Processing job ID
            
        Returns:
            Dictionary containing processing status
        """
        # This would typically check a database or job queue
        # For now, return a simple status
        return {
            'processing_id': processing_id,
            'status': 'completed',
            'message': 'Processing completed successfully'
        } 