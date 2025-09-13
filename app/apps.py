# app/apps.py
from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Создание групп после полной инициализации Django
        import django
        if django.VERSION >= (3, 2):
            from django.db import connection
            try:
                # Проверяем, что таблицы существуют
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM auth_group")

                # Если дошли сюда - таблицы есть, можно создавать группы
                from django.contrib.auth.models import Group
                Group.objects.get_or_create(name='Trader')
                Group.objects.get_or_create(name='Moderator')
                Group.objects.get_or_create(name='Admin')
            except:
                # Таблицы еще не созданы, пропускаем
                pass

        # ЗАКОММЕНТИРОВАННЫЙ КОД - раскомментируйте после успешных миграций:
        # from django.contrib.auth.models import Group
        #
        # # Создание групп пользователей при запуске приложения
        # Group.objects.get_or_create(name='Trader')
        # Group.objects.get_or_create(name='Moderator')
        # Group.objects.get_or_create(name='Admin')