from django import forms
from .models import WorkComment


class WorkCommentForm(forms.ModelForm):
    class Meta:
        model = WorkComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Напишите комментарий к работе..."
            })
        }
        labels = {
            "text": ""
        }