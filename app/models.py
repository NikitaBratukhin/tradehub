from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


# Создание ролей при запуске
def create_roles():
    roles = ["Trader", "Moderator", "Admin"]
    for role in roles:
        Group.objects.get_or_create(name=role)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_("Пользователь"))
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Telegram ID"))
    first_name = models.CharField(max_length=100, blank=True, verbose_name=_("Имя"))
    last_name = models.CharField(max_length=100, blank=True, verbose_name=_("Фамилия"))
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Возраст"))
    is_private = models.BooleanField(default=False, verbose_name=_("Скрытый профиль"))
    rating_score = models.IntegerField(default=0, verbose_name=_("Рейтинг"))
    login_streak = models.IntegerField(default=0, verbose_name=_("Серия входов"))
    last_login_streak_check = models.DateField(null=True, blank=True, verbose_name=_("Последняя проверка серии входов"))
    browser_notifications_enabled = models.BooleanField(default=False, verbose_name=_("Push-уведомления"))
    subscribed_to = models.ManyToManyField(User, related_name='subscribers', blank=True, verbose_name=_("Подписки"))

    def __str__(self):
        return f'Профиль @{self.user.username}'

    class Meta:
        verbose_name = _("Профиль")
        verbose_name_plural = _("Профили")


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        # Присваиваем роль "Trader" по умолчанию
        try:
            trader_group = Group.objects.get(name='Trader')
            instance.groups.add(trader_group)
        except Group.DoesNotExist:
            # Создаем группы если они не существуют
            create_roles()
            trader_group = Group.objects.get(name='Trader')
            instance.groups.add(trader_group)
    else:
        # Обновляем профиль для существующих пользователей
        if hasattr(instance, 'profile'):
            instance.profile.save()


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата публикации"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.ACTIVE,
                              verbose_name=_("Статус"))
    boosts = models.ManyToManyField(User, related_name='boosted_publications', blank=True, verbose_name=_("Бусты"))
    views = models.PositiveIntegerField(default=0, verbose_name=_("Просмотры"))

    def boost_count(self):
        """Возвращает количество бустов"""
        return self.boosts.count()

    def is_boosted_by(self, user):
        """Проверяет, поставил ли пользователь буст"""
        return self.boosts.filter(id=user.id).exists()

    def __str__(self):
        return f'Публикация от @{self.author.username} от {self.created_at.strftime("%d.%m.%Y")}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Публикация")
        verbose_name_plural = _("Публикации")
        permissions = [
            ("can_publish", "Может создавать публикации"),
            ("can_moderate", "Может модерировать публикации"),
        ]


class Achievement(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название"))
    description = models.TextField(verbose_name=_("Описание"))
    icon = models.CharField(max_length=10, default="🏆", verbose_name=_("Иконка"))
    rating_points = models.IntegerField(default=5, help_text=_("Очки рейтинга за получение"),
                                        verbose_name=_("Очки рейтинга"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Достижение")
        verbose_name_plural = _("Достижения")


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements',
                             verbose_name=_("Пользователь"))
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, verbose_name=_("Достижение"))
    awarded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата получения"))

    def __str__(self):
        return f'{self.user.username} - {self.achievement.name}'

    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ['-awarded_at']
        verbose_name = _("Достижение пользователя")
        verbose_name_plural = _("Достижения пользователей")


class Notification(models.Model):
    class NotificationTypes(models.TextChoices):
        BOOST = 'BOOST', _('Буст публикации')
        ACHIEVEMENT = 'ACHIEVEMENT', _('Новое достижение')
        PUBLICATION = 'PUBLICATION', _('Новая публикация')
        SYSTEM = 'SYSTEM', _('Системное уведомление')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications',
                             verbose_name=_("Пользователь"))
    title = models.CharField(max_length=100, verbose_name=_("Заголовок"))
    message = models.CharField(max_length=255, verbose_name=_("Сообщение"))
    notification_type = models.CharField(max_length=20, choices=NotificationTypes.choices,
                                         default=NotificationTypes.SYSTEM, verbose_name=_("Тип"))
    link = models.URLField(blank=True, null=True, verbose_name=_("Ссылка"))
    is_read = models.BooleanField(default=False, verbose_name=_("Прочитано"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))

    def __str__(self):
        return f'{self.user.username}: {self.title}'

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

    def __str__(self):
        return self.title

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

    def __str__(self):
        return self.title

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

    def __str__(self):
        return f'{self.author.username}: {self.content[:50]}...'

    class Meta:
        ordering = ['timestamp']
        verbose_name = _("Сообщение чата")
        verbose_name_plural = _("Сообщения чата")


class UserStatistics(models.Model):
    """Модель для хранения статистики пользователей"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='statistics',
                                verbose_name=_("Пользователь"))
    total_publications = models.PositiveIntegerField(default=0, verbose_name=_("Всего публикаций"))
    successful_predictions = models.PositiveIntegerField(default=0, verbose_name=_("Успешных прогнозов"))
    total_boosts_received = models.PositiveIntegerField(default=0, verbose_name=_("Получено бустов"))
    total_boosts_given = models.PositiveIntegerField(default=0, verbose_name=_("Дано бустов"))
    profile_views = models.PositiveIntegerField(default=0, verbose_name=_("Просмотры профиля"))
    last_activity = models.DateTimeField(auto_now=True, verbose_name=_("Последняя активность"))

    def success_rate(self):
        """Вычисляет процент успешных прогнозов"""
        if self.total_publications == 0:
            return 0
        return round((self.successful_predictions / self.total_publications) * 100, 1)

    def __str__(self):
        return f'Статистика {self.user.username}'

    class Meta:
        verbose_name = _("Статистика пользователя")
        verbose_name_plural = _("Статистика пользователей")


@receiver(post_save, sender=User)
def create_user_statistics(sender, instance, created, **kwargs):
    """Создает статистику для нового пользователя"""
    if created:
        UserStatistics.objects.get_or_create(user=instance)


# Сигналы для обновления статистики
@receiver(post_save, sender=Publication)
def update_publication_stats(sender, instance, created, **kwargs):
    """Обновляет статистику при создании публикации"""
    if created:
        stats, _ = UserStatistics.objects.get_or_create(user=instance.author)
        stats.total_publications += 1
        stats.save()


# Сигнал — уведомление при добавлении буста (m2m)
@receiver(m2m_changed, sender=Publication.boosts.through)
def publication_boosted(sender, instance, action, pk_set, **kwargs):
    """
    Создаем уведомление автору публикации, когда другие пользователи ставят буст.
    action == 'post_add' — после добавления записей в m2m.
    """
    from django.contrib.auth import get_user_model
    from django.shortcuts import reverse
    UserModel = get_user_model()

    if action == 'post_add' and pk_set:
        # pk_set — множество id пользователей, которые поставили буст
        for user_pk in pk_set:
            try:
                boosting_user = UserModel.objects.get(pk=user_pk)
            except UserModel.DoesNotExist:
                continue
            # не уведомляем, если автор сам себя бустит
            if boosting_user == instance.author:
                continue
            Notification.objects.create(
                user=instance.author,
                title="Ваша публикация получила буст",
                message=f"@{boosting_user.username} поддержал(а) вашу публикацию",
                notification_type=Notification.NotificationTypes.BOOST,
                link=f"/publication/{instance.pk}/"
            )


# Функция для создания ролей и начальных данных (вызвать из миграции или shell при необходимости)
def setup_initial_data():
    """Создает начальные данные: роли и достижения"""
    create_roles()

    achievements_data = [
        {"name": "Первые шаги", "description": "Создана первая публикация", "icon": "🎯", "rating_points": 10},
        {"name": "Популярный", "description": "Получено 10 бустов", "icon": "⭐", "rating_points": 25},
        {"name": "Активист", "description": "50 дней подряд в системе", "icon": "🔥", "rating_points": 50},
        {"name": "Эксперт", "description": "80% успешных прогнозов (мин. 10 публикаций)", "icon": "💎",
         "rating_points": 100},
    ]

    for achievement_data in achievements_data:
        Achievement.objects.get_or_create(
            name=achievement_data["name"],
            defaults=achievement_data
        )
