from django import forms
from .models import Work, WorkVersion


class WorkCreateForm(forms.ModelForm):
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4})
    )

    class Meta:
        model = Work
        fields = ["title", "description", "content", "visibility"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
            "visibility": forms.Select(attrs={"class": "form-select"}),
        }


class WorkEditForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = ["title", "description", "content", "visibility"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
            "visibility": forms.Select(attrs={"class": "form-select"}),
        }


class WorkVersionForm(forms.ModelForm):
    class Meta:
        model = WorkVersion
        fields = ["file", "comment"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }