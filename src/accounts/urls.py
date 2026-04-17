from django.urls import path
from .views import register_view, profile_view, edit_profile_view, data_transfer_view, import_data_view, export_data_view

urlpatterns = [
    path("register/", register_view, name="register"),
    path("profile/", profile_view, name="profile"),
    path("profile/edit/", edit_profile_view, name="edit_profile"),
    path("data-transfer/", data_transfer_view, name="data_transfer"),
    path("data-transfer/export/", export_data_view, name="export_data"),
    path("data-transfer/import/", import_data_view, name="import_data"),
]
