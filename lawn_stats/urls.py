from django.urls import path

from . import views

app_name = "lawn_stats"

urlpatterns = [
    path("upload_csv/", views.upload_csv, name="upload_csv"),
    path("map_columns/", views.map_columns, name="map_columns"),
    path("upload_afat_data/", views.upload_afat_data, name="upload_afat_data"),
    path("creator_charts/", views.creator_charts, name="creator_charts"),
]
