# app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic import ListView, DetailView, TemplateView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import F, Count, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import (
    CustomUserCreationForm, PublicationForm, ProfileSettingsForm,
    MarketOverviewForm, EducationalMaterialForm
)
from .models import (
    Publication, Profile, ChatMessage, Achievement, UserAchievement,
    EducationalMaterial, MarketOverview, Notification, RatingChange, DailyRatingAggregate
)
from .serializers import BoostToggleSerializer


# === Хелперы для проверки ролей ===
def is_trader(user):
    return user.groups.filter(name='Trader').exists()


def is_moderator(user):
    return user.groups.filter(name='Moderator').exists()


def is_admin(user):
    return user.is_staff or user.groups.filter(name='Admin').exists()


def is_privileged_user(user):
    return user.is_authenticated and (is_moderator(user) or is_admin(user))


# === Основные представления ===

def home_view(request):
    if request.user.is_authenticated:
        # Логика для дашборда
        last_overview = MarketOverview.objects.order_by('-created_at').first()
        context = {
            'last_overview': last_overview,
            'publications_count': Publication.objects.filter(author=request.user).count(),
        }
        return render(request, 'app/dashboard.html', context)
    else:
        # Логика для главной страницы
        publications = Publication.objects.filter(status='ACTIVE').select_related('author')[:3]
        total_users = User.objects.count()
        total_publications = Publication.objects.count()
        context = {
            'publications': publications,
            'total_users': total_users,
            'total_publications': total_publications,
        }
        return render(request, 'app/home.html', context)


class MenuView(LoginRequiredMixin, TemplateView):
    template_name = 'app/menu.html'


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            telegram_id = form.cleaned_data.get('telegram_id')
            if telegram_id:
                user.profile.telegram_id = telegram_id
                user.profile.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать в TradeHub, @{user.username}!', extra_tags='welcome')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'app/register.html', {'form': form})


# === Публикации ===

class PublicationListView(ListView):
    model = Publication
    template_name = 'app/publications.html'
    context_object_name = 'publications'
    paginate_by = 10

    def get_queryset(self):
        filter_type = self.request.GET.get('filter', 'recent')
        queryset = Publication.objects.filter(status='ACTIVE').select_related('author')

        if filter_type == 'trending':
            last_week = timezone.now() - timezone.timedelta(days=7)
            queryset = queryset.filter(created_at__gte=last_week).annotate(boost_count=Count('boosts')).order_by(
                '-boost_count', '-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset


class PublicationDetailView(DetailView):
    model = Publication
    template_name = 'app/publication_detail.html'
    context_object_name = 'publication'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        Publication.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        return obj


@login_required
@permission_required('app.can_publish', raise_exception=True)
def create_publication_view(request):
    if request.method == 'POST':
        form = PublicationForm(request.POST)
        if form.is_valid():
            publication = form.save(commit=False)
            publication.author = request.user
            publication.save()
            # Создаём уведомление автору (опционально, можно убрать)
            Notification.objects.create(
                user=request.user,
                title="Публикация создана",
                message="Ваша публикация успешно создана.",
                notification_type=Notification.NotificationTypes.PUBLICATION,
                link=f"/publication/{publication.pk}/"
            )
            messages.success(request, 'Ваша торговая идея успешно опубликована!')
            return redirect('publication_detail', pk=publication.pk)
    else:
        form = PublicationForm()
    return render(request, 'app/create_publication.html', {'form': form})


@login_required
def update_publication_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if not (request.user == publication.author or is_moderator(request.user) or is_admin(request.user)):
        messages.error(request, 'У вас нет прав для редактирования этой публикации.')
        return redirect('publication_detail', pk=pk)

    if request.method == 'POST':
        form = PublicationForm(request.POST, instance=publication)
        if form.is_valid():
            form.save()
            messages.success(request, 'Публикация успешно обновлена.')
            return redirect('publication_detail', pk=publication.pk)
    else:
        form = PublicationForm(instance=publication)

    return render(request, 'app/update_publication.html', {'form': form, 'publication': publication})


@login_required
def delete_publication_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if not (request.user == publication.author or is_moderator(request.user) or is_admin(request.user)):
        messages.error(request, 'У вас нет прав для удаления этой публикации.')
        return redirect('publication_detail', pk=pk)

    if request.method == 'POST':
        publication.delete()
        messages.success(request, 'Публикация была успешно удалена.')
        return redirect('publications')

    return render(request, 'app/delete_publication_confirm.html', {'publication': publication})


# === API для Бустов, Подписок и Рейтинга ===
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_boost_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    user = request.user

    serializer = BoostToggleSerializer(data=request.data, context={'request': request, 'publication': publication})
    serializer.is_valid(raise_exception=True)

    if publication.is_boosted_by(user):
        publication.boosts.remove(user)
        boosted = False
    else:
        publication.boosts.add(user)
        boosted = True

    return Response({
        'status': 'ok',
        'boost_count': publication.boost_count(),
        'boosted': boosted
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_follow_view(request, username):
    if request.method == 'POST':
        target_user = get_object_or_404(User, username=username)
        if target_user == request.user:
            return JsonResponse({'status': 'error', 'message': 'You cannot follow yourself'}, status=400)
        profile = request.user.profile
        if target_user in profile.subscribed_to.all():
            profile.subscribed_to.remove(target_user)
            following = False
        else:
            profile.subscribed_to.add(target_user)
            following = True
            Notification.objects.create(
                user=target_user,
                title="Новый подписчик",
                message=f"Пользователь @{request.user.username} подписался на вас.",
                notification_type=Notification.NotificationTypes.FOLLOW,
                link=f"/profile/{request.user.username}/"
            )
        return JsonResponse({'status': 'ok', 'following': following})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def daily_checkin_api(request):
    profile = request.user.profile
    result = profile.handle_daily_checkin()
    return Response(result)


@api_view(['GET'])
def leaderboard_api(request):
    period = request.query_params.get('period', 'all')
    limit = int(request.query_params.get('limit', 50))

    if period == 'all':
        qs = Profile.objects.select_related('user').order_by('-rating_score')[:limit]
        data = [{'username': p.user.username, 'rating': int(p.rating_score)} for p in qs]
        return Response({'period': 'all', 'data': data})

    now = timezone.now()
    if period == 'week':
        since = now.date() - timezone.timedelta(days=7)
    elif period == 'month':
        since = now.date() - timezone.timedelta(days=30)
    else:
        return Response({'detail': 'unsupported period'}, status=400)

    # Используем агрегированные данные для скорости
    aggregates = DailyRatingAggregate.objects.filter(date__gte=since) \
                     .values('user__username').annotate(points=Sum('points')).order_by('-points')[:limit]

    data = [{'username': a['user__username'], 'points': int(a['points'])} for a in aggregates]

    return Response({'period': period, 'data': data})


# === Профиль ===

@login_required
def profile_view(request, username=None):
    if username:
        user_profile = get_object_or_404(User, username=username)
    else:
        user_profile = request.user

    is_following = False
    if request.user.is_authenticated and request.user != user_profile:
        is_following = request.user.profile.subscribed_to.filter(pk=user_profile.pk).exists()

    context = {
        'user_profile': user_profile,
        'user_publications': Publication.objects.filter(author=user_profile),
        'user_achievements': UserAchievement.objects.filter(user=user_profile).select_related('achievement'),
        'is_following': is_following,
    }
    return render(request, 'app/profile.html', context)


@login_required
def profile_settings_view(request):
    if request.method == 'POST':
        form = ProfileSettingsForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки профиля успешно обновлены.')
            return redirect('profile_settings')
    else:
        form = ProfileSettingsForm(instance=request.user.profile)
    return render(request, 'app/profile_settings.html', {'form': form})


# === Достижения ===

class AchievementsListView(ListView):
    model = Achievement
    template_name = 'app/achievements.html'
    context_object_name = 'achievements'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            user_achievements = UserAchievement.objects.filter(
                user=self.request.user
            ).values_list('achievement_id', flat=True)
            context['user_achievements'] = list(user_achievements)
        return context


# === Обучающие материалы ===

def education_view(request):
    materials = EducationalMaterial.objects.filter().order_by('-created_at')
    categories = EducationalMaterial.objects.values_list('material_type', flat=True).distinct()

    category_filter = request.GET.get('category')
    if category_filter:
        materials = materials.filter(material_type=category_filter)

    context = {
        'materials': materials,
        'categories': categories,
        'current_category': category_filter,
    }
    return render(request, 'app/educational_list.html', context)


class EducationalMaterialDetailView(DetailView):
    model = EducationalMaterial
    template_name = 'app/educational_detail.html'
    context_object_name = 'material'


# === Обзоры рынка ===

def market_overview_view(request):
    overviews = MarketOverview.objects.filter(is_featured=True).order_by('-created_at')[:10]
    context = {
        'overviews': overviews,
    }
    return render(request, 'app/overview_list.html', context)


class MarketOverviewDetailView(DetailView):
    model = MarketOverview
    template_name = 'app/market_overview_detail.html'
    context_object_name = 'overview'


# === Лидерборд ===

class LeaderboardView(ListView):
    """
    Показывает страницы профилей, отсортированные по рейтингу (rating_score).
    Контекст: 'profiles' — список объектов Profile (совместимо с вашим шаблоном).
    """
    model = Profile
    template_name = 'app/leaderboard.html'
    context_object_name = 'profiles'
    paginate_by = 25

    def get_queryset(self):
        # выбираем профили с присоединёнными пользователями, сортируем по рейтингу
        return Profile.objects.select_related('user').order_by('-rating_score')


# === НОВЫЕ ПРЕДСТАВЛЕНИЯ ДЛЯ УПРАВЛЕНИЯ КОНТЕНТОМ ===

class PrivilegedUserMixin(UserPassesTestMixin):
    """Миксин для проверки, является ли пользователь модератором или админом."""
    def test_func(self):
        return is_privileged_user(self.request.user)


@login_required
@user_passes_test(is_privileged_user)
def create_educational_material_view(request):
    if request.method == 'POST':
        form = EducationalMaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            material.author = request.user
            material.save()
            messages.success(request, 'Обучающий материал успешно создан.')
            return redirect('education_detail', pk=material.pk)
    else:
        form = EducationalMaterialForm()
    return render(request, 'app/content_form.html', {'form': form, 'title': 'Создать обучающий материал'})


@login_required
@user_passes_test(is_privileged_user)
def update_educational_material_view(request, pk):
    material = get_object_or_404(EducationalMaterial, pk=pk)
    if request.method == 'POST':
        form = EducationalMaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, 'Материал успешно обновлен.')
            return redirect('education_detail', pk=material.pk)
    else:
        form = EducationalMaterialForm(instance=material)
    return render(request, 'app/content_form.html', {'form': form, 'title': 'Редактировать обучающий материал'})


class EducationalMaterialDeleteView(LoginRequiredMixin, PrivilegedUserMixin, DeleteView):
    model = EducationalMaterial
    template_name = 'app/delete_confirm.html'
    success_url = reverse_lazy('education_list')
    extra_context = {'title': 'Удалить обучающий материал'}


@login_required
@user_passes_test(is_privileged_user)
def create_market_overview_view(request):
    if request.method == 'POST':
        form = MarketOverviewForm(request.POST)
        if form.is_valid():
            overview = form.save(commit=False)
            overview.author = request.user
            overview.save()
            messages.success(request, 'Обзор рынка успешно создан.')
            return redirect('overview_detail', pk=overview.pk)
    else:
        form = MarketOverviewForm()
    return render(request, 'app/content_form.html', {'form': form, 'title': 'Создать обзор рынка'})


@login_required
@user_passes_test(is_privileged_user)
def update_market_overview_view(request, pk):
    overview = get_object_or_404(MarketOverview, pk=pk)
    if request.method == 'POST':
        form = MarketOverviewForm(request.POST, instance=overview)
        if form.is_valid():
            form.save()
            messages.success(request, 'Обзор успешно обновлен.')
            return redirect('overview_detail', pk=overview.pk)
    else:
        form = MarketOverviewForm(instance=overview)
    return render(request, 'app/content_form.html', {'form': form, 'title': 'Редактировать обзор рынка'})


class MarketOverviewDeleteView(LoginRequiredMixin, PrivilegedUserMixin, DeleteView):
    model = MarketOverview
    template_name = 'app/delete_confirm.html'
    success_url = reverse_lazy('market_overview_list')
    extra_context = {'title': 'Удалить обзор рынка'}


# === Чат ===

class ChatView(TemplateView):
    template_name = 'app/chat.html'

    def dispatch(self, request, *args, **kwargs):
        # TemplateView не защищён автоматически — делаем проверку
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['messages'] = ChatMessage.objects.select_related('author').order_by('-timestamp')[:50]
        return context


# === Уведомления ===

@login_required
def notifications_view(request):
    """Страница со всеми уведомлениями"""
    notifications = request.user.notifications.all()
    return render(request, 'app/notifications.html', {"notifications": notifications})


@login_required
def get_notifications_api(request):
    """API для получения непрочитанных уведомлений"""
    notifications_qs = request.user.notifications.filter(is_read=False)
    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "link": n.link,
            "type": n.notification_type,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for n in notifications_qs
    ]
    return JsonResponse({"notifications": data, "unread_count": notifications_qs.count()})


@login_required
def api_unread_notifications_count(request):
    """API для количества непрочитанных уведомлений"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"unread_count": count})


@login_required
def mark_notification_as_read_api(request, pk):
    if request.method == 'POST':
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


# === Статистика ===

@login_required
def statistics_view(request):
    if not (is_moderator(request.user) or is_admin(request.user)):
        messages.error(request, 'У вас нет прав для просмотра статистики.')
        return redirect('home')

    stats = {
        'total_users': User.objects.count(),
        'total_publications': Publication.objects.count(),
        'active_publications': Publication.objects.filter(status='ACTIVE').count(),
        'total_achievements': Achievement.objects.count(),
        'total_educational_materials': EducationalMaterial.objects.count(),
    }

    context = {'stats': stats}
    return render(request, 'app/statistics.html', context)