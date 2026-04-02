from django.urls import path
from .views import create_work, update_work, upload_version, my_works, work_detail, all_works

urlpatterns = [
    path("", all_works, name="all_works"),
    path("create/", create_work, name="create_work"),
    path("my/", my_works, name="my_works"),
    path("<int:work_id>/update/", update_work, name="update_work"),
    path("<int:work_id>/upload-version/", upload_version, name="upload_version"),
    path("<int:work_id>/", work_detail, name="work_detail"),
]