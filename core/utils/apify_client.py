import requests
import json
from django.conf import settings
from typing import Dict, List, Optional

class ApifyClient:
    """Client for fetching YouTube video transcripts using Apify"""
    
    def __init__(self):
        self.api_key = settings.APIFY_API_KEY
        self.actor_id = settings.APIFY_ACTOR_ID
        self.base_url = "https://api.apify.com/v2"
    
    def extract_video_id(self, youtube_url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        import re
        
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
        return None
    
    def fetch_transcript(self, youtube_url: str) -> Dict:
        """
        Fetch transcript from YouTube video using Apify
        
        Returns:
            Dict containing transcript data
        """
        if not self.api_key:
            raise ValueError("Apify API key not configured")
        
        video_id = self.extract_video_id(youtube_url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # Prepare the input for Apify actor
        input_data = {
            "videoUrls": [youtube_url],
            "language": "en",
            "subtitlesFormat": "srt"
        }
        
        # Start the Apify run
        run_url = f"{self.base_url}/acts/{self.actor_id}/runs"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(run_url, json=input_data, headers=headers)
        response.raise_for_status()
        
        run_data = response.json()
        run_id = run_data['data']['id']
        
        # Wait for the run to complete and get results
        return self._wait_for_results(run_id)
    
    def _wait_for_results(self, run_id: str, max_wait_time: int = 300) -> Dict:
        """Wait for Apify run to complete and return results"""
        import time
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            # Check run status
            status_url = f"{self.base_url}/acts/{self.actor_id}/runs/{run_id}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            
            run_status = response.json()
            
            if run_status['data']['status'] == 'SUCCEEDED':
                # Get results
                results_url = f"{self.base_url}/acts/{self.actor_id}/runs/{run_id}/dataset/items"
                results_response = requests.get(results_url, headers=headers)
                results_response.raise_for_status()
                
                results = results_response.json()
                return self._parse_transcript_results(results)
            
            elif run_status['data']['status'] == 'FAILED':
                raise Exception(f"Apify run failed: {run_status.get('data', {}).get('meta', {}).get('error', 'Unknown error')}")
            
            time.sleep(5)  # Wait 5 seconds before checking again
        
        raise TimeoutError("Apify run timed out")
    
    def _parse_transcript_results(self, results: List[Dict]) -> Dict:
        """Parse Apify transcript results into a structured format"""
        if not results:
            raise ValueError("No transcript results found")
        
        # Extract transcript data from the first result
        result = results[0]
        
        transcript_data = {
            'video_id': result.get('videoId'),
            'title': result.get('title'),
            'duration': result.get('duration'),
            'transcript': result.get('subtitles', []),
            'raw_data': result
        }
        
        return transcript_data 