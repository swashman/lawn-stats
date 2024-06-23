# data_processing.py
from datetime import datetime, timedelta

import pandas as pd

from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear

from .models import AfatFat, MonthlyStats

ALLIANCE_ID = 150097440


def get_previous_month_year():
    now = datetime.now()
    first = now.replace(day=1)
    last_month = first - timedelta(days=1)
    return last_month.month, last_month.year


def get_total_fats_by_corporation(month, year):
    print(f"Fetching data for month: {month}, year: {year}")
    fats = AfatFat.objects.filter(
        character__alliance_id=ALLIANCE_ID,
        fatlink__created__month=month,
        fatlink__created__year=year,
    )
    print(f"Total fats found: {fats.count()}")
    corp_totals = (
        fats.values("character__corporation_name")
        .annotate(total_fats=Count("id"))
        .order_by("character__corporation_name")
    )
    print(f"Corporation totals: {corp_totals}")
    return corp_totals


def get_relative_participation(month, year, total_mains=3):
    corp_totals = get_total_fats_by_corporation(month, year)
    relative_participation = {
        corp["character__corporation_name"]: corp["total_fats"] / total_mains
        for corp in corp_totals
    }
    return relative_participation


def get_monthly_totals_by_corporation():
    fats = (
        AfatFat.objects.filter(character__alliance_id=ALLIANCE_ID)
        .annotate(
            month=ExtractMonth("fatlink__created"), year=ExtractYear("fatlink__created")
        )
        .values("character__corporation_name", "month", "year")
        .annotate(total_fats=Count("id"))
        .order_by("character__corporation_name")
    )
    return fats


def get_fats_by_type_for_members(month, year):
    print(f"Fetching fats by type for month: {month}, year: {year}")
    fats = (
        AfatFat.objects.filter(
            character__alliance_id=ALLIANCE_ID,
            fatlink__created__month=month,
            fatlink__created__year=year,
        )
        .values(
            "character__character_name",
            "character__corporation_name",
            "fatlink__link_type__name",
        )
        .annotate(total_fats=Count("id"))
    )
    print(f"Fats by type found: {fats}")
    return fats


def import_csv_to_model(file_path):
    df = pd.read_csv(file_path)
    df["month"], df["year"] = get_previous_month_year()
    for _, row in df.iterrows():
        MonthlyStats.objects.create(
            account=row["Account"],
            beehive=row["Beehive"],
            corp=row["Corp"],
            cricket=row["Cricket"],
            gsol=row["GSOL"],
            incursion_hq=row["Incursion-HQ"],
            incursion_vg=row["Incursion-VG"],
            locust=row["Locust"],
            peacetime=row["PEACETIME"],
            scouts=row["SCOUTS"],
            sig_squad=row["SIG/SQUAD"],
            strategic=row["STRATEGIC"],
            month=row["month"],
            year=row["year"],
        )
