from django.urls import path
from .views import (
    data_transfer_view,
    edit_profile_view,
    export_data_view,
    import_data_view,
    profile_view,
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
    path("data-transfer/", data_transfer_view, name="data_transfer"),
    path("data-transfer/export/", export_data_view, name="export_data"),
    path("data-transfer/import/", import_data_view, name="import_data"),
]
