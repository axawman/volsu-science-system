from django.urls import path
from .views import (
    all_works,
    create_work,
    download_version_file,
    download_work_archive,
    my_works,
    update_work,
    upload_version,
    work_detail,
)

urlpatterns = [
    path("", all_works, name="all_works"),
    path("create/", create_work, name="create_work"),
    path("my/", my_works, name="my_works"),
    path("<int:work_id>/update/", update_work, name="update_work"),
    path("<int:work_id>/upload-version/", upload_version, name="upload_version"),
    path("<int:work_id>/download-archive/", download_work_archive, name="download_work_archive"),
    path(
        "<int:work_id>/versions/<int:version_id>/files/<int:file_id>/download/",
        download_version_file,
        name="download_version_file",
    ),
    path("<int:work_id>/", work_detail, name="work_detail"),
]
