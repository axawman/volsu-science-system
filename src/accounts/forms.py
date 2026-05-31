from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import GroupChatMessage, Profile


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
            "placeholder": "name@volsu.ru",
        }),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "current-password",
        }),
    )

    def clean(self):
        login_value = self.cleaned_data.get("username", "").strip()

        if "@" in login_value:
            user = User.objects.filter(email__iexact=login_value).first()

            if user:
                self.cleaned_data["username"] = user.get_username()

        return super().clean()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "password1", "password2"]

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if not email.endswith("@volsu.ru"):
            raise forms.ValidationError("Для регистрации нужна почта в домене @volsu.ru.")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")

        return email


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "bio", "photo"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class DataImportForm(forms.Form):
    archive = forms.FileField(
        label="Архив с данными",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".zip"})
    )


class GroupChatMessageForm(forms.ModelForm):
    class Meta:
        model = GroupChatMessage
        fields = ["text", "reply_to"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "maxlength": 2000,
                "placeholder": "Написать сообщение",
            }),
            "reply_to": forms.HiddenInput(),
        }

    def __init__(self, *args, study_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = GroupChatMessage.objects.none()

        if study_group is not None:
            queryset = GroupChatMessage.objects.filter(
                study_group=study_group,
                is_deleted=False,
            )

        self.fields["reply_to"].queryset = queryset
        self.fields["reply_to"].required = False

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if not text:
            raise forms.ValidationError("Сообщение не может быть пустым.")
        return text[:2000]
