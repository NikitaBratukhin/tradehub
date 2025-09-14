# app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Publication, Profile, MarketOverview, EducationalMaterial

class CustomUserCreationForm(UserCreationForm):
    telegram_id = forms.IntegerField(
        required=False,
        label="Telegram ID",
        help_text="Введите ваш Telegram ID (число). Необязательно.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-input'})
        self.fields['telegram_id'].widget.attrs.update({'class': 'form-input'})


class PublicationForm(forms.ModelForm):
     class Meta:
        model = Publication
        fields = ["description", "screenshot_id", "target_1", "target_2", "target_3", "stop_loss"]
        labels = {
            "description": "Описание идеи",
            "screenshot_id": "URL скриншота",
            "target_1": "Цель 1",
            "target_2": "Цель 2",
            "target_3": "Цель 3",
            "stop_loss": "Стоп-лосс",
        }
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 4, "placeholder": "Опишите свой анализ, обоснование входа и общую стратегию..."}),
            "screenshot_id": forms.TextInput(attrs={"class": "form-input", "placeholder": "https://..."}),
            "target_1": forms.TextInput(attrs={"class": "form-input", "placeholder": "Обязательный уровень"}),
            "target_2": forms.TextInput(attrs={"class": "form-input", "placeholder": "Необязательно"}),
            "target_3": forms.TextInput(attrs={"class": "form-input", "placeholder": "Необязательно"}),
            "stop_loss": forms.TextInput(attrs={"class": "form-input", "placeholder": "Обязательный уровень"}),
        }

class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'age', 'is_private', 'browser_notifications_enabled']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'age': forms.NumberInput(attrs={'class': 'form-input'}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'browser_notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# НОВАЯ ФОРМА: Для создания/редактирования обзоров рынка
class MarketOverviewForm(forms.ModelForm):
    class Meta:
        model = MarketOverview
        fields = ['title', 'content', 'video_url', 'is_featured']
        labels = {
            "title": "Заголовок обзора",
            "content": "Текстовое содержание",
            "video_url": "Ссылка на видео (необязательно)",
            "is_featured": "Рекомендуемый обзор",
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 10}),
            'video_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# НОВАЯ ФОРМА: Для создания/редактирования обучающих материалов
class EducationalMaterialForm(forms.ModelForm):
    class Meta:
        model = EducationalMaterial
        fields = ['title', 'content', 'material_type', 'is_featured']
        labels = {
            "title": "Заголовок материала",
            "content": "Содержание (поддерживает Markdown)",
            "material_type": "Тип материала",
            "is_featured": "Рекомендуемый материал",
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 10}),
            'material_type': forms.Select(attrs={'class': 'form-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }