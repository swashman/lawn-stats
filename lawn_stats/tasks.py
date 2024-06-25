# tasks.py

import csv

from celery import shared_task

from allianceauth.services.hooks import get_extension_logger

from .models import (
    AuthenticationCharacterownership,
    AuthUser,
    EveonlineEvecharacter,
    EveonlineEvecorporationinfo,
    MonthlyCorpStats,
    MonthlyFleetType,
    MonthlyUserStats,
    UnknownAccount,
)

logger = get_extension_logger(__name__)


@shared_task
def process_csv_task(csv_data, column_mapping, month, year):
    # Check for existing data for the given month and year
    if (
        MonthlyUserStats.objects.filter(month=month, year=year).exists()
        or MonthlyCorpStats.objects.filter(month=month, year=year).exists()
    ):
        logger.warning(f"Data for {month}/{year} already exists. Skipping processing.")
        return

    reader = csv.DictReader(csv_data)

    for row in reader:
        try:
            account_name = row["Account"]
        except KeyError:
            continue

        try:
            character = EveonlineEvecharacter.objects.get(character_name=account_name)
            ownership = AuthenticationCharacterownership.objects.get(
                character=character
            )
            user = ownership.user
            corporation = character.corporation
        except (
            EveonlineEvecharacter.DoesNotExist,
            AuthenticationCharacterownership.DoesNotExist,
            EveonlineEvecorporationinfo.DoesNotExist,
        ):
            # Handle unknown account
            unknown_account, created = UnknownAccount.objects.get_or_create(
                account_name=account_name
            )
            if unknown_account.user_id:
                user = AuthUser.objects.get(id=unknown_account.user_id)
                corporation = user.profile.main_character.corporation
            else:
                continue

        for column, fleet_type_name in column_mapping.items():
            if column in row and row[column]:
                total_fats = int(row[column])

                if total_fats == 0:
                    continue

                fleet_type, created = MonthlyFleetType.objects.get_or_create(
                    name=fleet_type_name,
                    source="imp",  # Set the source to 'imp'
                    month=month,
                    year=year,
                )

                user_stats, created = MonthlyUserStats.objects.get_or_create(
                    user_id=user.id,
                    corporation_id=corporation.corporation_id,
                    month=month,
                    year=year,
                    fleet_type=fleet_type,
                    defaults={"total_fats": total_fats},
                )

                if not created:
                    user_stats.total_fats += total_fats
                    user_stats.save()

                corp_stats, created = MonthlyCorpStats.objects.get_or_create(
                    corporation_id=corporation.corporation_id,
                    month=month,
                    year=year,
                    fleet_type=fleet_type,
                    defaults={"total_fats": total_fats},
                )

                if not created:
                    corp_stats.total_fats += total_fats
                    corp_stats.save()
