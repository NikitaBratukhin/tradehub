# app/serializers.py
from rest_framework import serializers
from .models import Profile, Publication
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    achievements_count = serializers.SerializerMethodField()
    publications_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'age', 'is_private', 'star_rating', 'user', 'achievements_count',
                  'publications_count']

    def get_achievements_count(self, obj):
        return obj.user.achievements.count()

    def get_publications_count(self, obj):
        return obj.user.publications.count()


class PublicationSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Publication
        fields = '__all__'