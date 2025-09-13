from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic import ListView, DetailView, TemplateView
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import F, Count
from django.utils import timezone

from .forms import CustomUserCreationForm, PublicationForm, ProfileSettingsForm
from .models import (
    Publication, Profile, ChatMessage, Achievement, UserAchievement,
    EducationalMaterial, MarketOverview, Notification
)


# === Хелперы для проверки ролей ===
def is_trader(user):
    return user.groups.filter(name='Trader').exists()


def is_moderator(user):
    return user.groups.filter(name='Moderator').exists()


def is_admin(user):
    return user.is_staff or user.groups.filter(name='Admin').exists()


# === Основные представления ===

def home_view(request):
    publications = Publication.objects.filter(status='ACTIVE').select_related('author')[:3]
    total_users = User.objects.count()
    total_publications = Publication.objects.count()
    context = {
        'publications': publications,
        'total_users': total_users,
        'total_publications': total_publications,
    }
    return render(request, 'app/home.html', context)


class MenuView(TemplateView):
    template_name = 'app/menu.html'


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            telegram_id = form.cleaned_data.get('telegram_id')
            if telegram_id:
                # профиль уже создаётся сигналом post_save
                user.profile.telegram_id = telegram_id
                user.profile.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать в TradeHub, @{user.username}!', tags='welcome')
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
@user_passes_test(is_trader, login_url='home')
def create_publication_view(request):
    if not request.user.has_perm('app.can_publish'):
        messages.error(request, 'У вас нет прав для создания публикации.')
        return redirect('publications')

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


@login_required
def toggle_boost_view(request, pk):
    """
    Ожидает POST. Переключает буст текущего пользователя для публикации pk.
    Возвращает JSON с новым количеством бустов и состоянием.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

    publication = get_object_or_404(Publication, pk=pk)
    user = request.user

    if user in publication.boosts.all():
        publication.boosts.remove(user)
        boosted = False
    else:
        publication.boosts.add(user)
        boosted = True
        # уведомление автору создаётся через m2m_changed сигнал в models.py
    return JsonResponse({'status': 'ok', 'boost_count': publication.boosts.count(), 'boosted': boosted})


# === Профиль ===

@login_required
def profile_view(request, username=None):
    if username:
        user = get_object_or_404(User, username=username)
    else:
        user = request.user

    profile = user.profile
    user_publications = Publication.objects.filter(author=user)
    user_achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
    context = {
        'user_profile': user,
        'profile': profile,
        'user_publications': user_publications,
        'user_achievements': user_achievements,
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
    paginate_by = 50

    def get_queryset(self):
        # выбираем профили с присоединёнными пользователями, сортируем по рейтингу
        return Profile.objects.select_related('user').order_by('-rating_score')


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


# === API функции для AJAX (другие) ===

@login_required
def toggle_follow_view(request, username):
    if request.method == 'POST':
        target_user = get_object_or_404(User, username=username)
        # логика подписки
        profile = request.user.profile
        if target_user in profile.subscribed_to.all():
            profile.subscribed_to.remove(target_user)
            following = False
        else:
            profile.subscribed_to.add(target_user)
            following = True
        return JsonResponse({'status': 'ok', 'following': following})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
