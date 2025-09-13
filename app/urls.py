from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # === Основные страницы ===
    path('', views.home_view, name='home'),
    path('menu/', views.MenuView.as_view(), name='menu'),
    path('achievements/', views.AchievementsListView.as_view(), name='achievements'),

    # === Авторизация ===
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # === Профиль ===
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),
    path('settings/', views.profile_settings_view, name='profile_settings'),

    # === Публикации ===
    path('publications/', views.PublicationListView.as_view(), name='publications'),
    path('publication/create/', views.create_publication_view, name='create_publication'),
    path('publication/<int:pk>/', views.PublicationDetailView.as_view(), name='publication_detail'),
    path('publication/<int:pk>/update/', views.update_publication_view, name='update_publication'),
    path('publication/<int:pk>/delete/', views.delete_publication_view, name='delete_publication'),

    # === Обучающие материалы ===
    path('education/', views.education_view, name='education'),
    path('education/<int:pk>/', views.EducationalMaterialDetailView.as_view(), name='education_detail'),

    # === Обзоры рынка ===
    path('market-overview/', views.market_overview_view, name='market_overview'),
    path('market-overview/<int:pk>/', views.MarketOverviewDetailView.as_view(), name='overview_detail'),

    # === Уведомления ===
    path('notifications/', views.notifications_view, name='notifications'),

    # === Социальные функции ===
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('chat/', views.ChatView.as_view(), name='chat'),

    # === Статистика ===
    path('statistics/', views.statistics_view, name='statistics'),

    # === API endpoints ===

    # Публикации API
    path('api/publication/<int:pk>/toggle_boost/', views.toggle_boost_view, name='toggle_boost'),

    # Подписки API
    path('api/follow/<str:username>/', views.toggle_follow_view, name='toggle_follow'),

    # Уведомления API
    path('api/notifications/', views.get_notifications_api, name='get_notifications_api'),
    path('api/notifications/unread-count/', views.api_unread_notifications_count, name='api_unread_notifications_count'),
    path('api/notifications/mark-read/<int:pk>/', views.mark_notification_as_read_api, name='mark_notification_read_api'),

    # Альтернативные URL для совместимости
    path('api/toggle-boost/<int:pk>/', views.toggle_boost_view, name='toggle_boost_api'),
]
