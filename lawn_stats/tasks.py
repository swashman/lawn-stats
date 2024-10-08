# tasks.py

import csv
from datetime import datetime

from celery import shared_task

from django.conf import settings
from django.db import IntegrityError, transaction

from allianceauth.services.hooks import get_extension_logger

from .models import (
    AfatFat,
    AfatFatlink,
    AfatFleettype,
    AuthenticationCharacterownership,
    AuthenticationUserprofile,
    AuthUser,
    EveonlineEvecharacter,
    EveonlineEvecorporationinfo,
    MonthlyCorpStats,
    MonthlyCreatorStats,
    MonthlyFleetType,
    MonthlyUserStats,
    UnknownAccount,
)

logger = get_extension_logger(__name__)


@shared_task
def process_csv_task(csv_data, column_mapping, month, year):
    user_stats_exists = MonthlyUserStats.objects.filter(
        month=month, year=year, fleet_type__source="imp"
    ).exists()
    corp_stats_exists = MonthlyCorpStats.objects.filter(
        month=month, year=year, fleet_type__source="imp"
    ).exists()

    if user_stats_exists or corp_stats_exists:
        logger.warning(f"Data for {month}/{year} already exists. Skipping processing.")
        logger.debug(
            f"User stats exist: {user_stats_exists}, Corp stats exist: {corp_stats_exists}"
        )
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
                logger.warning(f"Unknown account {account_name} not found.")
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


@shared_task
def process_afat_data_task(month, year):
    # Check for existing data for the given month and year
    user_stats_exists = MonthlyUserStats.objects.filter(
        month=month, year=year, fleet_type__source="afat"
    ).exists()
    corp_stats_exists = MonthlyCorpStats.objects.filter(
        month=month, year=year, fleet_type__source="afat"
    ).exists()

    if user_stats_exists or corp_stats_exists:
        logger.warning(f"Data for {month}/{year} already exists. Skipping processing.")
        logger.debug(
            f"User stats exist: {user_stats_exists}, Corp stats exist: {corp_stats_exists}"
        )
        return

    start_date = datetime(year, month, 1)
    end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

    # Create necessary fleet types
    afat_fleet_types = AfatFleettype.objects.all()
    for afat_fleet_type in afat_fleet_types:
        MonthlyFleetType.objects.get_or_create(
            name=afat_fleet_type.name,
            source="afat",
            month=month,
            year=year,
        )

    # Create the "unknown" fleet type
    unknown_fleet_type, _ = MonthlyFleetType.objects.get_or_create(
        name="Unknown",
        source="afat",
        month=month,
        year=year,
    )

    afat_fats = AfatFat.objects.filter(
        fatlink__created__gte=start_date, fatlink__created__lt=end_date
    )

    for afat_fat in afat_fats:
        try:
            character = afat_fat.character
            logger.debug(
                f"Processing character: {character.character_name} (ID: {character.character_id})"
            )

            ownership = AuthenticationCharacterownership.objects.get(
                character=character
            )
            user = ownership.user
            main_character = user.profile.main_character

            if not main_character or not main_character.alliance:
                logger.debug(
                    f"Skipping character: {character.character_name} - No main character or alliance."
                )
                continue

            if main_character.alliance.alliance_id != settings.STATS_ALLIANCE_ID:
                logger.debug(
                    f"Skipping character: {character.character_name} - Not in the specified alliance."
                )
                continue

            corporation = main_character.corporation
            logger.debug(
                f"Character {character.character_name} belongs to corporation: {corporation.corporation_name}"
            )

        except EveonlineEvecharacter.DoesNotExist:
            logger.error(
                f"EveonlineEvecharacter.DoesNotExist: Character {character.character_name} not found."
            )
            continue
        except AuthenticationCharacterownership.DoesNotExist:
            logger.error(
                f"AuthenticationCharacterownership.DoesNotExist: Ownership not found for character {character.character_name}."
            )
            continue
        except EveonlineEvecorporationinfo.DoesNotExist:
            logger.error(
                f"EveonlineEvecorporationinfo.DoesNotExist: Corporation not found for main character {main_character.character_name}."
            )
            continue
        except AuthenticationUserprofile.DoesNotExist:
            logger.error(
                f"AuthenticationUserprofile.DoesNotExist: User profile not found for user {user.username}."
            )
            continue

        fatlink = afat_fat.fatlink
        fleet_type_name = fatlink.link_type.name if fatlink.link_type else "Unknown"

        fleet_type = MonthlyFleetType.objects.get(
            name=fleet_type_name,
            source="afat",
            month=month,
            year=year,
        )

        try:
            with transaction.atomic():
                # Check for existing user stats entry before attempting to create or update
                existing_user_stats = MonthlyUserStats.objects.filter(
                    user_id=user.id,
                    corporation_id=corporation.corporation_id,
                    month=month,
                    year=year,
                    fleet_type=fleet_type,
                ).first()

                if existing_user_stats:
                    existing_user_stats.total_fats += 1
                    existing_user_stats.save()
                else:
                    MonthlyUserStats.objects.create(
                        user_id=user.id,
                        corporation_id=corporation.corporation_id,
                        month=month,
                        year=year,
                        fleet_type=fleet_type,
                        total_fats=1,
                    )

                # Check for existing corp stats entry before attempting to create or update
                existing_corp_stats = MonthlyCorpStats.objects.filter(
                    corporation_id=corporation.corporation_id,
                    month=month,
                    year=year,
                    fleet_type=fleet_type,
                ).first()

                if existing_corp_stats:
                    existing_corp_stats.total_fats += 1
                    existing_corp_stats.save()
                else:
                    MonthlyCorpStats.objects.create(
                        corporation_id=corporation.corporation_id,
                        month=month,
                        year=year,
                        fleet_type=fleet_type,
                        total_fats=1,
                    )
        except IntegrityError as e:
            logger.error(
                f"IntegrityError: user ID {user.id}, corp ID {corporation.corporation_id}, and {fleet_type_name}: {e}"
            )
            continue

    # Process creator stats
    process_creator_stats(month, year)


@shared_task
def process_creator_stats(month, year):
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

    afat_fatlinks = AfatFatlink.objects.filter(
        created__gte=start_date, created__lt=end_date
    )

    for fatlink in afat_fatlinks:
        creator = fatlink.creator
        fleet_type_name = fatlink.link_type.name if fatlink.link_type else "Unknown"

        fleet_type = MonthlyFleetType.objects.get(
            name=fleet_type_name,
            source="afat",
            month=month,
            year=year,
        )

        try:
            with transaction.atomic():
                # Check for existing creator stats entry before attempting to create or update
                existing_creator_stats = MonthlyCreatorStats.objects.filter(
                    creator_id=creator.id, month=month, year=year, fleet_type=fleet_type
                ).first()

                if existing_creator_stats:
                    existing_creator_stats.total_created += 1
                    existing_creator_stats.save()
                else:
                    MonthlyCreatorStats.objects.create(
                        creator_id=creator.id,
                        month=month,
                        year=year,
                        fleet_type=fleet_type,
                        total_created=1,
                    )
        except IntegrityError as e:
            logger.error(
                f"IntegrityError processing creator ID {creator.id}, and fleet type {fleet_type_name}: {e}"
            )
            continue
