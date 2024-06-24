from django.core.management.base import BaseCommand

from lawn_stats.models import (
    MonthlyCorpStats,
    MonthlyCreatorStats,
    MonthlyFleetType,
    MonthlyUserStats,
)


class Command(BaseCommand):
    help = "Clear monthly data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--month", type=int, help="Month to clear data for", required=True
        )
        parser.add_argument(
            "--year", type=int, help="Year to clear data for", required=True
        )

    def handle(self, *args, **options):
        month = options["month"]
        year = options["year"]

        MonthlyCorpStats.objects.filter(month=month, year=year).delete()
        MonthlyUserStats.objects.filter(month=month, year=year).delete()
        MonthlyCreatorStats.objects.filter(month=month, year=year).delete()
        MonthlyFleetType.objects.filter(month=month, year=year).delete()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully cleared data for {month}-{year}")
        )
