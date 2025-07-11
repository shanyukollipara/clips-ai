from django.db import models
from django.utils import timezone

class VideoProcessing(models.Model):
    """Model to store video processing requests and results"""
    youtube_url = models.URLField(max_length=500)
    clip_duration = models.IntegerField(help_text="Duration in seconds")
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Video Processing: {self.youtube_url} - {self.status}"

class ViralClip(models.Model):
    """Model to store individual viral clips"""
    video_processing = models.ForeignKey(VideoProcessing, on_delete=models.CASCADE, related_name='clips')
    start_timestamp = models.FloatField(help_text="Start time in seconds")
    end_timestamp = models.FloatField(help_text="End time in seconds")
    justification = models.TextField(help_text="Why this moment is viral")
    emotional_keywords = models.JSONField(default=list, blank=True)
    urgency_indicators = models.JSONField(default=list, blank=True)
    virality_score = models.IntegerField(help_text="Score from 0-100", null=True, blank=True)
    clip_url = models.URLField(max_length=500, blank=True, null=True)
    preview_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-virality_score', '-created_at']
    
    def __str__(self):
        return f"Clip {self.start_timestamp}s-{self.end_timestamp}s (Score: {self.virality_score})"
