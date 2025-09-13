# app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Publication, Profile

class CustomUserCreationForm(UserCreationForm):
    # ... (код остается как у вас, он хороший)
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
        self.fields['telegram_id'] = forms.IntegerField(required=False, label="Telegram ID")
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-input'})


class PublicationForm(forms.ModelForm):
    # ... (код остается как у вас)
     class Meta:
        model = Publication
        fields = ["description", "screenshot_id", "target_1", "target_2", "target_3", "stop_loss"]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 4, "placeholder": "Описание вашей торговой идеи..."}),
            "screenshot_id": forms.TextInput(attrs={"class": "form-input", "placeholder": "URL изображения или ID из Telegram"}),
            "target_1": forms.TextInput(attrs={"class": "form-input", "placeholder": "Обязательная цель"}),
            "target_2": forms.TextInput(attrs={"class": "form-input", "placeholder": "Необязательно"}),
            "target_3": forms.TextInput(attrs={"class": "form-input", "placeholder": "Необязательно"}),
            "stop_loss": forms.TextInput(attrs={"class": "form-input", "placeholder": "Обязательный стоп-лосс"}),
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