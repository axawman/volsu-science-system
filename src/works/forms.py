from django import forms
from .models import Work, WorkVersion


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if not data:
            if self.required:
                raise forms.ValidationError("Загрузите хотя бы один файл")
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        return [single_file_clean(item, initial) for item in data]


class WorkCreateForm(forms.ModelForm):
    files = MultipleFileField(
        required=True,
        widget=MultipleFileInput(attrs={"class": "form-control", "multiple": True}),
        label="Файлы первой версии",
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
    files = MultipleFileField(
        required=True,
        widget=MultipleFileInput(attrs={"class": "form-control", "multiple": True}),
        label="Файлы версии",
    )

    class Meta:
        model = WorkVersion
        fields = ["comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
