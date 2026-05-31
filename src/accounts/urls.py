from django.urls import path
from .views import (
    data_transfer_view,
    delete_group_chat_message_view,
    edit_profile_view,
    edit_group_chat_message_view,
    export_data_view,
    group_chat_message_readers_view,
    group_chat_updates_view,
    group_chat_view,
    import_data_view,
    profile_view,
    public_profile_view,
    register_view,
    send_registration_code,
    verify_registration_code,
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("register/send-code/", send_registration_code, name="send_registration_code"),
    path("register/verify-code/", verify_registration_code, name="verify_registration_code"),
    path("profile/", profile_view, name="profile"),
    path("profile/edit/", edit_profile_view, name="edit_profile"),
    path("group-chat/", group_chat_view, name="group_chat"),
    path("group-chat/updates/", group_chat_updates_view, name="group_chat_updates"),
    path("group-chat/messages/<int:message_id>/readers/", group_chat_message_readers_view, name="group_chat_readers"),
    path("group-chat/messages/<int:message_id>/edit/", edit_group_chat_message_view, name="edit_group_chat_message"),
    path(
        "group-chat/messages/<int:message_id>/delete/",
        delete_group_chat_message_view,
        name="delete_group_chat_message",
    ),
    path("users/<str:username>/", public_profile_view, name="public_profile"),
    path("data-transfer/", data_transfer_view, name="data_transfer"),
    path("data-transfer/export/", export_data_view, name="export_data"),
    path("data-transfer/import/", import_data_view, name="import_data"),
]
