import requests
import json
from django.conf import settings
from typing import Dict, List, Optional

class GrokAnalyzer:
    """Client for analyzing transcripts and extracting viral moments using Grok API"""
    
    def __init__(self):
        self.api_key = settings.GROK_API_KEY
        self.api_url = settings.GROK_API_URL
    
    def extract_viral_moments(self, transcript_data: Dict, clip_duration: int) -> List[Dict]:
        """
        Extract viral moments from transcript using Grok API
        
        Args:
            transcript_data: Transcript data from Apify
            clip_duration: Desired clip duration in seconds
            
        Returns:
            List of viral moments with timestamps and justifications
        """
        if not self.api_key:
            raise ValueError("Grok API key not configured")
        
        # Prepare transcript text for analysis
        transcript_text = self._format_transcript_for_analysis(transcript_data)
        
        # Create prompt for viral moment extraction
        prompt = self._create_extraction_prompt(transcript_text, clip_duration)
        
        # Call Grok API
        response = self._call_grok_api(prompt)
        
        # Parse the response
        viral_moments = self._parse_viral_moments(response)
        
        return viral_moments
    
    def score_virality(self, clip_data: Dict) -> int:
        """
        Assign a virality score (0-100) to a clip using Grok
        
        Args:
            clip_data: Clip data including justification and context
            
        Returns:
            Virality score from 0-100
        """
        if not self.api_key:
            raise ValueError("Grok API key not configured")
        
        prompt = self._create_scoring_prompt(clip_data)
        
        response = self._call_grok_api(prompt)
        
        # Extract score from response
        score = self._parse_virality_score(response)
        
        return score
    
    def _format_transcript_for_analysis(self, transcript_data: Dict) -> str:
        """Format transcript data into a readable text format"""
        transcript = transcript_data.get('transcript', [])
        
        if not transcript:
            return ""
        
        formatted_text = ""
        for entry in transcript:
            if isinstance(entry, dict):
                # Handle structured transcript format
                start_time = entry.get('start', 0)
                text = entry.get('text', '')
                formatted_text += f"[{start_time:.2f}s] {text}\n"
            elif isinstance(entry, str):
                # Handle plain text format
                formatted_text += f"{entry}\n"
        
        return formatted_text
    
    def _create_extraction_prompt(self, transcript_text: str, clip_duration: int) -> str:
        """Create prompt for viral moment extraction"""
        return f"""Analyze this YouTube video transcript and identify the top 5-10 most viral moments that would make engaging short clips of {clip_duration} seconds each.

Transcript:
{transcript_text}

For each viral moment, provide:
1. Start timestamp (in seconds)
2. End timestamp (in seconds) - should be {clip_duration} seconds from start
3. Justification for why this moment is viral
4. Emotional keywords (e.g., "shocking", "hilarious", "inspiring")
5. Urgency indicators (e.g., "breaking news", "exclusive", "must-see")

Format your response as a JSON array of objects with these fields:
- start_timestamp (float)
- end_timestamp (float)
- justification (string)
- emotional_keywords (array of strings)
- urgency_indicators (array of strings)

Focus on moments that are:
- Emotionally engaging
- Shareable on social media
- Have clear narrative hooks
- Include surprising or unexpected content
- Feature strong reactions or dramatic moments

Return only valid JSON without any additional text."""
    
    def _create_scoring_prompt(self, clip_data: Dict) -> str:
        """Create prompt for virality scoring"""
        justification = clip_data.get('justification', '')
        emotional_keywords = clip_data.get('emotional_keywords', [])
        urgency_indicators = clip_data.get('urgency_indicators', [])
        
        return f"""Rate the virality potential of this video clip on a scale of 0-100.

Clip Details:
- Justification: {justification}
- Emotional Keywords: {', '.join(emotional_keywords)}
- Urgency Indicators: {', '.join(urgency_indicators)}

Scoring Criteria:
- 90-100: Extremely viral, likely to go viral across all platforms
- 80-89: Highly viral, strong potential for widespread sharing
- 70-79: Very viral, good potential for significant reach
- 60-69: Moderately viral, decent sharing potential
- 50-59: Somewhat viral, limited but possible reach
- 40-49: Low viral potential, niche appeal
- 30-39: Minimal viral potential
- 0-29: Not viral, unlikely to gain traction

Consider factors like:
- Emotional impact
- Surprise factor
- Relatability
- Shareability
- Current trends relevance
- Platform optimization

Return only a single integer between 0 and 100, nothing else."""
    
    def _call_grok_api(self, prompt: str) -> str:
        """Make API call to Grok"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "grok-1",  # Use the cheapest model
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{self.api_url}/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _parse_viral_moments(self, response: str) -> List[Dict]:
        """Parse Grok response into structured viral moments"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                moments = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                moments = json.loads(response)
            
            # Validate and clean the data
            validated_moments = []
            for moment in moments:
                if isinstance(moment, dict):
                    validated_moment = {
                        'start_timestamp': float(moment.get('start_timestamp', 0)),
                        'end_timestamp': float(moment.get('end_timestamp', 0)),
                        'justification': str(moment.get('justification', '')),
                        'emotional_keywords': list(moment.get('emotional_keywords', [])),
                        'urgency_indicators': list(moment.get('urgency_indicators', []))
                    }
                    validated_moments.append(validated_moment)
            
            return validated_moments
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Failed to parse Grok response: {e}. Response: {response}")
    
    def _parse_virality_score(self, response: str) -> int:
        """Parse virality score from Grok response"""
        try:
            # Extract numeric score from response
            import re
            score_match = re.search(r'\b(\d{1,2}|100)\b', response.strip())
            if score_match:
                score = int(score_match.group(1))
                return max(0, min(100, score))  # Ensure score is between 0-100
            else:
                raise ValueError("No score found in response")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Failed to parse virality score: {e}. Response: {response}") 