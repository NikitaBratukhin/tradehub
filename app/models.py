# app/models.py
import json
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.db.models import F, Index
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


# ---------------------------------------
# Хелпер для создания ролей
# ---------------------------------------
def create_roles():
    roles = ["Trader", "Moderator", "Admin"]
    for role in roles:
        Group.objects.get_or_create(name=role)


# ---------------------------------------
# Профиль пользователя и управление рейтингом
# ---------------------------------------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_("Пользователь"))
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Telegram ID"))
    first_name = models.CharField(max_length=150, blank=True, verbose_name=_("Имя"))
    last_name = models.CharField(max_length=150, blank=True, verbose_name=_("Фамилия"))
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Возраст"))
    is_private = models.BooleanField(default=False, verbose_name=_("Скрытый профиль"))

    # Система рейтинга
    rating_score = models.BigIntegerField(default=0, db_index=True, verbose_name=_("Рейтинг"))
    season_number = models.PositiveIntegerField(default=1, db_index=True, verbose_name=_("Номер сезона"))

    # Серии входов
    last_login_streak_check = models.DateField(null=True, blank=True, verbose_name=_("Последняя проверка серии входов"))
    login_streak = models.PositiveIntegerField(default=0, verbose_name=_("Серия входов"))

    browser_notifications_enabled = models.BooleanField(default=False, verbose_name=_("Push-уведомления"))
    subscribed_to = models.ManyToManyField(User, related_name='subscribers', blank=True, verbose_name=_("Подписки"))

    def __str__(self):
        return f'Профиль @{self.user.username}'

    @transaction.atomic
    def add_rating(self, points: int, reason: str = ''):
        """
        Атомарно изменяет рейтинг и создает запись в логе RatingChange.
        """
        self.rating_score = F('rating_score') + points
        self.save(update_fields=['rating_score'])
        RatingChange.objects.create(user=self.user, delta=points, reason=reason)
        self.refresh_from_db(fields=['rating_score'])
        return int(self.rating_score)

    @transaction.atomic
    def handle_daily_checkin(self):
        """
        Обрабатывает ежедневный вход:
        - +1 очко рейтинга за вход.
        - Если серия входов кратна 7, то бонус +5 очков.
        Возвращает словарь со статусом операции.
        """
        today = timezone.localdate()
        if self.last_login_streak_check == today:
            return {'ok': False, 'reason': 'already_checked_today', 'rating': int(self.rating_score)}

        yesterday = today - timezone.timedelta(days=1)

        if self.last_login_streak_check == yesterday:
            self.login_streak = F('login_streak') + 1
        else:
            self.login_streak = 1

        self.last_login_streak_check = today
        self.save(update_fields=['last_login_streak_check', 'login_streak'])
        self.refresh_from_db(fields=['login_streak'])

        self.add_rating(1, reason='daily_login')

        if self.login_streak > 0 and self.login_streak % 7 == 0:
            self.add_rating(5, reason=f'streak_bonus_{self.login_streak}')

        return {'ok': True, 'login_streak': int(self.login_streak), 'rating': int(self.rating_score)}

    class Meta:
        verbose_name = _("Профиль")
        verbose_name_plural = _("Профили")


# ... (Все остальные модели остаются без изменений) ...
class Publication(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Активна')
        TARGET_HIT = 'TARGET_HIT', _('Цель достигнута (TP)')
        STOP_HIT = 'STOP_HIT', _('Стоп сработал (SL)')
        CANCELED = 'CANCELED', _('Отменена')

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='publications', verbose_name=_("Автор"))
    description = models.TextField(verbose_name=_("Описание идеи"))
    screenshot_id = models.CharField(max_length=255, verbose_name=_("ID скриншота или URL"), blank=True)
    target_1 = models.CharField(max_length=100, verbose_name=_("Цель 1"))
    target_2 = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Цель 2"))
    target_3 = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Цель 3"))
    stop_loss = models.CharField(max_length=100, verbose_name=_("Стоп-лосс"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Дата публикации"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.ACTIVE,
                              verbose_name=_("Статус"))
    boosts = models.ManyToManyField(User, related_name='boosted_publications', blank=True, verbose_name=_("Бусты"))
    views = models.PositiveIntegerField(default=0, verbose_name=_("Просмотры"))

    def boost_count(self):
        return self.boosts.count()

    def is_boosted_by(self, user):
        return self.boosts.filter(id=user.id).exists()

    def __str__(self):
        return f'Публикация от @{self.author.username} от {self.created_at.strftime("%d.%m.%Y")}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Публикация")
        verbose_name_plural = _("Публикации")
        permissions = [("can_publish", "Может создавать публикации"), ("can_moderate", "Может модерировать публикации")]
        indexes = [Index(fields=['-created_at'])]


class Achievement(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название"))
    description = models.TextField(verbose_name=_("Описание"))
    icon = models.CharField(max_length=10, default="🏆", verbose_name=_("Иконка"))
    rating_points = models.IntegerField(default=5, help_text=_("Очки рейтинга за получение"),
                                        verbose_name=_("Очки рейтинга"))

    def __str__(self): return self.name

    class Meta:
        verbose_name = _("Достижение")
        verbose_name_plural = _("Достижения")


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements',
                             verbose_name=_("Пользователь"))
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, verbose_name=_("Достижение"))
    awarded_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Дата получения"))

    def __str__(self): return f'{self.user.username} - {self.achievement.name}'

    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ['-awarded_at']
        verbose_name = _("Достижение пользователя")
        verbose_name_plural = _("Достижения пользователей")
        indexes = [Index(fields=['-awarded_at'])]


class RatingChange(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rating_changes',
                             verbose_name=_("Пользователь"))
    delta = models.IntegerField(verbose_name=_("Изменение"))
    reason = models.CharField(max_length=200, blank=True, verbose_name=_("Причина"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Дата"))

    def __str__(self): return f'{self.user.username}: {self.delta} ({self.reason})'

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Изменение рейтинга")
        verbose_name_plural = _("Изменения рейтинга")
        indexes = [Index(fields=['created_at', 'user'])]


class DailyRatingAggregate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Пользователь"))
    date = models.DateField(db_index=True, verbose_name=_("Дата"))
    points = models.IntegerField(default=0, verbose_name=_("Очки"))

    class Meta:
        unique_together = ('user', 'date')
        verbose_name = _("Дневной агрегат рейтинга")
        verbose_name_plural = _("Дневные агрегаты рейтинга")
        indexes = [Index(fields=['date', 'user'])]


class RatingSnapshot(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Дата создания"))
    period = models.CharField(max_length=50, help_text='Например: "week", "month", "season"', verbose_name=_("Период"))
    top_n = models.PositiveIntegerField(default=0, verbose_name=_("Кол-во в топе"))
    data_raw = models.TextField(default='[]', verbose_name=_("Данные (JSON как текст)"))

    @property
    def data(self):
        try:
            return json.loads(self.data_raw) if self.data_raw else []
        except json.JSONDecodeError:
            return []

    @data.setter
    def data(self, value):
        self.data_raw = json.dumps(value, ensure_ascii=False, indent=2)

    def __str__(self):
        return f'Снимок {self.period} от {self.created_at.strftime("%d.%m.%Y")}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Снимок рейтинга")
        verbose_name_plural = _("Снимки рейтинга")


class Notification(models.Model):
    class NotificationTypes(models.TextChoices):
        BOOST = 'BOOST', _('Буст публикации')
        ACHIEVEMENT = 'ACHIEVEMENT', _('Новое достижение')
        PUBLICATION = 'PUBLICATION', _('Новая публикация')
        SYSTEM = 'SYSTEM', _('Системное уведомление')
        MARKET_OVERVIEW = 'MARKET_OVERVIEW', _('Новый обзор рынка')  # Новый тип
        FOLLOW = 'FOLLOW', _('Новая подписка')  # Новый тип

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications',
                             verbose_name=_("Пользователь"))
    title = models.CharField(max_length=100, verbose_name=_("Заголовок"))
    message = models.CharField(max_length=255, verbose_name=_("Сообщение"))
    notification_type = models.CharField(max_length=20, choices=NotificationTypes.choices,
                                         default=NotificationTypes.SYSTEM, verbose_name=_("Тип"))
    link = models.URLField(blank=True, null=True, verbose_name=_("Ссылка"))
    is_read = models.BooleanField(default=False, verbose_name=_("Прочитано"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))

    def __str__(self): return f'{self.user.username}: {self.title}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Уведомление")
        verbose_name_plural = _("Уведомления")


class EducationalMaterial(models.Model):
    class MaterialTypes(models.TextChoices):
        ARTICLE = 'ARTICLE', _('Статья')
        VIDEO = 'VIDEO', _('Видео')
        GUIDE = 'GUIDE', _('Руководство')
        TUTORIAL = 'TUTORIAL', _('Урок')

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='educational_materials',
                               verbose_name=_("Автор"))
    title = models.CharField(max_length=200, verbose_name=_("Заголовок"))
    content = models.TextField(help_text=_("Можно использовать Markdown для форматирования"),
                               verbose_name=_("Содержание"))
    material_type = models.CharField(max_length=20, choices=MaterialTypes.choices, default=MaterialTypes.ARTICLE,
                                     verbose_name=_("Тип материала"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Рекомендуемый"))
    views = models.PositiveIntegerField(default=0, verbose_name=_("Просмотры"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    def __str__(self): return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Обучающий материал")
        verbose_name_plural = _("Обучающие материалы")


class MarketOverview(models.Model):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='market_overviews',
                               verbose_name=_("Автор"))
    title = models.CharField(max_length=200, verbose_name=_("Заголовок"))
    video_url = models.URLField(blank=True, null=True, verbose_name=_("Ссылка на видео"))
    content = models.TextField(verbose_name=_("Содержание"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Рекомендуемый"))
    views = models.PositiveIntegerField(default=0, verbose_name=_("Просмотры"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    def __str__(self): return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Обзор рынка")
        verbose_name_plural = _("Обзоры рынка")


class ChatMessage(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages', verbose_name=_("Автор"))
    content = models.TextField(verbose_name=_("Содержание"))
    is_edited = models.BooleanField(default=False, verbose_name=_("Отредактировано"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Время отправки"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Время обновления"))

    def __str__(self): return f'{self.author.username}: {self.content[:50]}...'

    class Meta:
        ordering = ['timestamp']
        verbose_name = _("Сообщение чата")
        verbose_name_plural = _("Сообщения чата")


class UserStatistics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='statistics',
                                verbose_name=_("Пользователь"))
    total_publications = models.PositiveIntegerField(default=0, verbose_name=_("Всего публикаций"))
    successful_predictions = models.PositiveIntegerField(default=0, verbose_name=_("Успешных прогнозов"))
    total_boosts_received = models.PositiveIntegerField(default=0, verbose_name=_("Получено бустов"))
    total_boosts_given = models.PositiveIntegerField(default=0, verbose_name=_("Дано бустов"))
    profile_views = models.PositiveIntegerField(default=0, verbose_name=_("Просмотры профиля"))
    last_activity = models.DateTimeField(auto_now=True, verbose_name=_("Последняя активность"))

    def success_rate(self):
        if self.total_publications == 0: return 0
        return round((self.successful_predictions / self.total_publications) * 100, 1)

    def __str__(self): return f'Статистика {self.user.username}'

    class Meta:
        verbose_name = _("Статистика пользователя")
        verbose_name_plural = _("Статистика пользователей")


# ---------------------------------------
# Сигналы
# ---------------------------------------
@receiver(post_save, sender=User)
def create_or_update_user_profile_and_stats(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        UserStatistics.objects.create(user=instance)
        try:
            trader_group = Group.objects.get(name='Trader')
            instance.groups.add(trader_group)
        except Group.DoesNotExist:
            create_roles()
            trader_group = Group.objects.get(name='Trader')
            instance.groups.add(trader_group)
    else:
        instance.profile.save()
        instance.statistics.save()


@receiver(post_save, sender=Publication)
def update_publication_stats_on_create(sender, instance, created, **kwargs):
    if created:
        stats, _ = UserStatistics.objects.get_or_create(user=instance.author)
        stats.total_publications = F('total_publications') + 1
        stats.save()


# НОВЫЙ СИГНАЛ: Уведомление о новом обзоре рынка
@receiver(post_save, sender=MarketOverview)
def notify_on_new_market_overview(sender, instance, created, **kwargs):
    if created:
        author = instance.author
        if not author: return

        # Получаем всех подписчиков автора
        subscribers = User.objects.filter(profile__in=author.subscribers.all())

        for subscriber in subscribers:
            Notification.objects.create(
                user=subscriber,
                title="Новый обзор рынка",
                message=f"Эксперт @{author.username} опубликовал новый обзор: '{instance.title}'",
                notification_type=Notification.NotificationTypes.MARKET_OVERVIEW,
                link=f"/market-overviews/{instance.pk}/"
            )


@receiver(m2m_changed, sender=Publication.boosts.through)
def publication_boosted_handler(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        author_profile = instance.author.profile
        points_to_add = 3 * len(pk_set)
        author_profile.add_rating(points_to_add, reason=f'boost_publication_{instance.pk}')

        for user_pk in pk_set:
            try:
                boosting_user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                continue

            if boosting_user != instance.author:
                Notification.objects.create(
                    user=instance.author,
                    title="Ваша публикация получила буст",
                    message=f"@{boosting_user.username} поддержал(а) вашу публикацию",
                    notification_type=Notification.NotificationTypes.BOOST,
                    link=f"/publication/{instance.pk}/"
                )