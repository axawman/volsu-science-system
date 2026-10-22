from django.urls import path

from .views import guide_file_download, guide_index, guide_section

urlpatterns = [
    path("", guide_index, name="guide_index"),
    path("files/<int:file_id>/", guide_file_download, name="guide_file_download"),
    path("<slug:slug>/", guide_section, name="guide_section"),
]
