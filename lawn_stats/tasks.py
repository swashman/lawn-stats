# tasks.py

import csv

from celery import shared_task

from allianceauth.services.hooks import get_extension_logger

from .models import (
    AuthenticationCharacterownership,
    EveonlineEvecharacter,
    EveonlineEvecorporationinfo,
    MonthlyCorpStats,
    MonthlyFleetType,
    MonthlyUserStats,
)

logger = get_extension_logger(__name__)


@shared_task
def process_csv_task(csv_data, column_mapping, month, year):
    reader = csv.DictReader(csv_data)

    unknown_accounts = []

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
            unknown_accounts.append(account_name)
            continue

        for column, fleet_type_name in column_mapping.items():
            if column in row and row[column]:
                total_fats = int(row[column])

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

    if unknown_accounts:
        logger.warning(f"Unknown accounts: {', '.join(unknown_accounts)}")
