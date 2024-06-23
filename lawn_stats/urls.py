"""App URLs"""

# Django
# AA Example App
from django.urls import path

from lawn_stats import views

app_name: str = "lawn_stats"

urlpatterns = [
    path("", views.index, name="index"),
]
