from django.contrib import admin
from .models import (
    Profile, Publication, Achievement, UserAchievement, EducationalMaterial,
    MarketOverview, ChatMessage, Notification, UserStatistics
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_id', 'rating_score', 'login_streak')
    search_fields = ('user__username', 'telegram_id')


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('author', 'created_at', 'status', 'boost_count', 'views')
    search_fields = ('author__username', 'description')
    list_filter = ('status',)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating_points')


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'awarded_at')


@admin.register(EducationalMaterial)
class EducationalMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'material_type', 'created_at')
    search_fields = ('title',)


@admin.register(MarketOverview)
class MarketOverviewAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('author', 'timestamp')
    search_fields = ('author__username', 'content')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title', 'message')


@admin.register(UserStatistics)
class UserStatisticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_publications', 'successful_predictions', 'total_boosts_received')
