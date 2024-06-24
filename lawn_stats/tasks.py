# tasks.py

import csv
import logging

from celery import shared_task

from .models import (
    AuthUser,
    EveonlineEvecharacter,
    MonthlyCorpStats,
    MonthlyFleetType,
    MonthlyUserStats,
)

logger = logging.getLogger(__name__)


@shared_task
def process_csv_task(csv_data, column_mapping, month, year):
    reader = csv.DictReader(csv_data[1:], fieldnames=csv_data[0])
    unknown_accounts = []

    for row in reader:
        account_name = row["Account"]

        try:
            character = EveonlineEvecharacter.objects.get(character_name=account_name)
            user = AuthUser.objects.get(profile__main_character=character)
        except EveonlineEvecharacter.DoesNotExist:
            unknown_accounts.append(account_name)
            continue
        except AuthUser.DoesNotExist:
            unknown_accounts.append(account_name)
            continue

        corporation = character.corporation

        for column, fleet_type_name in column_mapping.items():
            if column in row:
                total_fats = int(row[column])

                fleet_type, created = MonthlyFleetType.objects.get_or_create(
                    name=fleet_type_name, source="afat", month=month, year=year
                )

                MonthlyUserStats.objects.create(
                    user_id=user.id,
                    corporation_id=corporation.corporation_id,
                    month=month,
                    year=year,
                    fleet_type=fleet_type,
                    total_fats=total_fats,
                )

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
