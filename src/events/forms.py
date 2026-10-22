from datetime import datetime, time, timedelta

from django import forms
from django.utils import timezone

from .models import PersonalEvent


class PersonalEventForm(forms.ModelForm):
    date = forms.DateField(
        label="Дата",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
    )
    time = forms.TimeField(
        label="Время",
        initial=time(9, 0),
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
    )
    remind_before = forms.TypedChoiceField(
        label="Напоминание",
        choices=[("", "Без напоминания"), *PersonalEvent.REMIND_CHOICES],
        coerce=int,
        empty_value=None,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = PersonalEvent
        fields = ["title", "description", "remind_before"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": 255}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            local_start = timezone.localtime(self.instance.starts_at)
            self.initial.setdefault("date", local_start.date())
            self.initial.setdefault("time", local_start.time().replace(second=0, microsecond=0))

    def reminder_changed(self):
        return not self.instance.pk or bool({"date", "time", "remind_before"} & set(self.changed_data))

    def clean(self):
        cleaned_data = super().clean()
        event_date = cleaned_data.get("date")
        event_time = cleaned_data.get("time")

        if event_date is None or event_time is None:
            return cleaned_data

        starts_at = timezone.make_aware(datetime.combine(event_date, event_time))
        cleaned_data["starts_at"] = starts_at

        remind_before = cleaned_data.get("remind_before")
        if remind_before is not None and self.reminder_changed():
            remind_at = starts_at - timedelta(minutes=remind_before)
            if remind_at <= timezone.now():
                self.add_error("remind_before", "Это время напоминания уже прошло. Выберите другое или уберите напоминание.")

        return cleaned_data

    def save(self, commit=True):
        event = super().save(commit=False)
        event.starts_at = self.cleaned_data["starts_at"]

        if self.reminder_changed():
            event.reminder_dismissed_at = None

        if commit:
            event.save()
        return event
