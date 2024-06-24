# data_processing.py
import csv
from datetime import datetime, timedelta

from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear

from .models import (
    AfatFat,
    EveonlineEvecharacter,
    EveonlineEvecorporationinfo,
    MonthlyStats,
)

ALLIANCE_ID = 150097440


def get_previous_month_year():
    now = datetime.now()
    first = now.replace(day=1)
    last_month = first - timedelta(days=1)
    return last_month.month, last_month.year


def get_all_corporations():
    return EveonlineEvecorporationinfo.objects.filter(alliance_id=ALLIANCE_ID)


def get_total_fats_by_corporation(month, year):
    fats = AfatFat.objects.filter(
        character__alliance_id=ALLIANCE_ID,
        fatlink__created__month=month,
        fatlink__created__year=year,
    )
    corp_totals = (
        fats.values("character__corporation_name")
        .annotate(total_fats=Count("id"))
        .order_by("character__corporation_name")
    )

    # Include all corporations, even those with 0 fats
    all_corporations = get_all_corporations()
    corp_totals_dict = {
        corp["character__corporation_name"]: corp["total_fats"] for corp in corp_totals
    }
    for corp in all_corporations:
        if corp.corporation_name not in corp_totals_dict:
            corp_totals_dict[corp.corporation_name] = 0

    sorted_corp_totals = sorted(corp_totals_dict.items())
    return sorted_corp_totals


def get_relative_participation(month, year, total_mains=3):
    corp_totals = get_total_fats_by_corporation(month, year)
    relative_participation = {
        corp_name: total_fats / total_mains for corp_name, total_fats in corp_totals
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
    fats = (
        AfatFat.objects.filter(
            fatlink__created__year=year, fatlink__created__month=month
        )
        .values(
            "character__character_name",
            "character__corporation_name",
            "fatlink__link_type__name",
        )
        .annotate(total_fats=Count("id"))
    )

    result = {}
    for fat in fats:
        corp_name = fat["character__corporation_name"]
        char_name = fat["character__character_name"]
        fat_type = fat["fatlink__link_type__name"]
        total_fats = fat["total_fats"]

        character = EveonlineEvecharacter.objects.get(character_name=char_name)
        try:
            main_character = character.character_ownership.user.profile.main_character
        except EveonlineEvecharacter.character_ownership.RelatedObjectDoesNotExist:
            main_character = character  # Fallback to character itself if no ownership

        main_char_name = (
            main_character.character_name
            if main_character
            else character.character_name
        )

        if corp_name not in result:
            result[corp_name] = {}
        if main_char_name not in result[corp_name]:
            result[corp_name][main_char_name] = {}
        if fat_type not in result[corp_name][main_char_name]:
            result[corp_name][main_char_name][fat_type] = 0

        result[corp_name][main_char_name][fat_type] += total_fats

    return result


def import_csv_to_model(file_path):
    with open(file_path) as file:
        reader = csv.DictReader(file)
        for row in reader:
            account = row["Account"]
            beehive = int(row["Beehive"]) if row["Beehive"] else 0
            locust = (int(row["Cricket "]) if row["Cricket "] else 0) + (
                int(row["Locust"]) if row["Locust"] else 0
            )
            incursion = (int(row["Incursion-HQ"]) if row["Incursion-HQ"] else 0) + (
                int(row["Incursion-VG"]) if row["Incursion-VG"] else 0
            )
            peacetime = int(row["PEACETIME"]) if row["PEACETIME"] else 0
            scouts = int(row["SCOUTS"]) if row["SCOUTS"] else 0
            sig_squad = int(row["SIG/SQUAD"]) if row["SIG/SQUAD"] else 0
            strategic = int(row["STRATEGIC"]) if row["STRATEGIC"] else 0

            # Assuming month and year are passed as part of the function or available from context
            year = 2024  # Example year
            month = 6  # Example month

            MonthlyStats.objects.update_or_create(
                account=account,
                year=year,
                month=month,
                defaults={
                    "beehive": beehive,
                    "locust": locust,
                    "incursion": incursion,
                    "peacetime": peacetime,
                    "scouts": scouts,
                    "sig_squad": sig_squad,
                    "strategic": strategic,
                },
            )
