from django.urls import path

from .views import (
    create_personal_event,
    delete_personal_event,
    dismiss_personal_reminder,
    update_personal_event,
)

urlpatterns = [
    path("", create_personal_event, name="create_personal_event"),
    path("<int:event_id>/", update_personal_event, name="update_personal_event"),
    path("<int:event_id>/delete/", delete_personal_event, name="delete_personal_event"),
    path("<int:event_id>/dismiss-reminder/", dismiss_personal_reminder, name="dismiss_personal_reminder"),
]
