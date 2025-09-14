# app/serializers.py
from rest_framework import serializers
from .models import Profile, Publication, User, RatingChange, RatingSnapshot
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    achievements_count = serializers.SerializerMethodField()
    publications_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['user', 'first_name', 'last_name', 'age', 'is_private', 'rating_score',
                  'achievements_count', 'publications_count']

    def get_achievements_count(self, obj):
        return obj.user.achievements.count()

    def get_publications_count(self, obj):
        return obj.user.publications.count()


class PublicationSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    is_boosted = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = '__all__'
        read_only_fields = ('author', 'created_at', 'updated_at', 'boosts')

    def get_is_boosted(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return obj.is_boosted_by(user)
        return False


class BoostToggleSerializer(serializers.Serializer):
    """
    Сериализатор для валидации запроса на буст.
    Проверяет, что пользователь не бустит сам себя и не превышает лимит (2 в день).
    """

    def validate(self, attrs):
        user = self.context['request'].user
        publication = self.context['publication']

        if publication.author == user:
            raise serializers.ValidationError("Вы не можете бустить свою публикацию.")

        # Ограничение: 2 буста в день
        today_min = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_max = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        boost_count_today = user.boosted_publications.filter(created_at__range=(today_min, today_max)).count()

        if not publication.is_boosted_by(user) and boost_count_today >= 2:
            raise serializers.ValidationError("Лимит бустов на сегодня (2) исчерпан.")

        return attrs


class RatingChangeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = RatingChange
        fields = ('id', 'username', 'delta', 'reason', 'created_at')


class RatingSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingSnapshot
        fields = ('id', 'period', 'created_at', 'top_n', 'data')