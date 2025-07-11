from django.contrib import admin
from .models import VideoProcessing, ViralClip

@admin.register(VideoProcessing)
class VideoProcessingAdmin(admin.ModelAdmin):
    list_display = ('id', 'youtube_url', 'clip_duration', 'status', 'created_at', 'total_clips')
    list_filter = ('status', 'created_at', 'clip_duration')
    search_fields = ('youtube_url', 'error_message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def total_clips(self, obj):
        return obj.clips.count()
    total_clips.short_description = 'Total Clips'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('youtube_url', 'clip_duration', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ViralClip)
class ViralClipAdmin(admin.ModelAdmin):
    list_display = ('id', 'video_processing', 'start_timestamp', 'end_timestamp', 
                   'virality_score', 'created_at', 'has_clip_url')
    list_filter = ('virality_score', 'created_at', 'video_processing__status')
    search_fields = ('justification', 'video_processing__youtube_url')
    readonly_fields = ('created_at',)
    ordering = ('-virality_score', '-created_at')
    
    def has_clip_url(self, obj):
        return bool(obj.clip_url)
    has_clip_url.boolean = True
    has_clip_url.short_description = 'Has Clip URL'
    
    fieldsets = (
        ('Clip Information', {
            'fields': ('video_processing', 'start_timestamp', 'end_timestamp', 'virality_score')
        }),
        ('Content Analysis', {
            'fields': ('justification', 'emotional_keywords', 'urgency_indicators')
        }),
        ('Media URLs', {
            'fields': ('clip_url', 'preview_url'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('video_processing')
