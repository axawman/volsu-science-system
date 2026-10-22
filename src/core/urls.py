from django.urls import path
from .views import calendar_items, calendar_page, home

urlpatterns = [
    path("", home, name="home"),
    path("calendar/", calendar_page, name="calendar"),
    path("calendar/items/", calendar_items, name="calendar_items"),
]
