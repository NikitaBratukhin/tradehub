from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Главные страницы
    path('', views.home_view, name='home'),
    path('menu/', views.MenuView.as_view(), name='menu'),

    # Авторизация и регистрация
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Профиль и настройки
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),
    path('settings/', views.profile_settings_view, name='profile_settings'),

    # Публикации
    path('publications/', views.PublicationListView.as_view(), name='publications'),
    path('publication/<int:pk>/', views.PublicationDetailView.as_view(), name='publication_detail'),
    path('publication/create/', views.create_publication_view, name='create_publication'),
    path('publication/<int:pk>/update/', views.update_publication_view, name='update_publication'),
    path('publication/<int:pk>/delete/', views.delete_publication_view, name='delete_publication'),

    # Обучающие материалы
    path('education/', views.education_view, name='education'),  # исправлено
    path('education/<int:pk>/', views.EducationalMaterialDetailView.as_view(), name='education_detail'),
    path('education/create/', views.create_educational_material_view, name='create_education'),
    path('education/<int:pk>/update/', views.update_educational_material_view, name='update_education'),
    path('education/<int:pk>/delete/', views.EducationalMaterialDeleteView.as_view(), name='delete_education'),

    # Обзоры рынка
    path('market-overviews/', views.market_overview_view, name='market_overview'),  # исправлено
    path('market-overviews/<int:pk>/', views.MarketOverviewDetailView.as_view(), name='overview_detail'),
    path('market-overviews/create/', views.create_market_overview_view, name='create_overview'),
    path('market-overviews/<int:pk>/update/', views.update_market_overview_view, name='update_overview'),
    path('market-overviews/<int:pk>/delete/', views.MarketOverviewDeleteView.as_view(), name='delete_overview'),

    # Другие разделы
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('achievements/', views.AchievementsListView.as_view(), name='achievements'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('notifications/', views.notifications_view, name='notifications'),

    # API endpoints
    path('api/publication/<int:pk>/toggle_boost/', views.toggle_boost_view, name='toggle_boost_api'),
    path('api/notifications/', views.get_notifications_api, name='get_notifications_api'),
    path('api/notifications/unread-count/', views.api_unread_notifications_count,
         name='api_unread_notifications_count'),
    path('api/notifications/mark-read/<int:pk>/', views.mark_notification_as_read_api,
         name='mark_notification_read_api'),
    path('api/user/<str:username>/toggle-follow/', views.toggle_follow_view, name='toggle_follow'),
    path('api/daily-checkin/', views.daily_checkin_api, name='daily_checkin_api'),
]
