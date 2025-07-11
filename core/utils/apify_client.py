import os
from apify_client import ApifyClient as OfficialApifyClient

class ApifyClient:
    """Wrapper for Apify YouTube Transcript Scraper actor using Apify Python client"""
    def __init__(self):
        self.api_token = os.environ.get('APIFY_API_KEY')
        if not self.api_token:
            raise ValueError("APIFY_API_KEY environment variable not set")
        self.client = OfficialApifyClient(self.api_token)
        self.actor_id = "faWsVv9VTSNVIhWpR"  # YouTube Transcript Scraper actor

    def fetch_transcript(self, youtube_url: str):
        run_input = {"videoUrl": youtube_url}
        run = self.client.actor(self.actor_id).call(run_input=run_input)
        if not run or "defaultDatasetId" not in run:
            raise ValueError("Apify run did not return a dataset ID")
        transcript_items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
        if not transcript_items:
            raise ValueError("No transcript items returned from Apify")
        # Return a dict matching the previous expected structure
        result = transcript_items[0]
        transcript_data = {
            'video_id': result.get('videoId'),
            'title': result.get('title'),
            'duration': result.get('duration'),
            'transcript': result.get('subtitles', []),
            'raw_data': result
        }
        return transcript_data 