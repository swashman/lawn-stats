from django.urls import path

from .views import (
    fats_by_type_chart,
    index,
    individual_fats_by_type_chart,
    monthly_totals_chart,
    relative_participation_chart,
    total_fats_chart,
    upload_csv,
)

app_name = "lawn_stats"

urlpatterns = [
    path("", index, name="index"),
    path("total-fats/", total_fats_chart, name="total_fats_chart"),
    path(
        "relative-participation/",
        relative_participation_chart,
        name="relative_participation_chart",
    ),
    path("monthly-totals/", monthly_totals_chart, name="monthly_totals_chart"),
    path("fats-by-type/", fats_by_type_chart, name="fats_by_type_chart"),
    path(
        "individual-fats-by-type/",
        individual_fats_by_type_chart,
        name="individual_fats_by_type_chart",
    ),
    path("upload-csv/", upload_csv, name="upload_csv"),
]
