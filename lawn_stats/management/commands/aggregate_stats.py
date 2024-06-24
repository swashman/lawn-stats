from django.core.management.base import BaseCommand

from lawn_stats.tasks import aggregate_monthly_stats


class Command(BaseCommand):
    help = "Aggregate monthly stats"

    def add_arguments(self, parser):
        parser.add_argument(
            "--month", type=int, help="Month for which to aggregate stats"
        )
        parser.add_argument(
            "--year", type=int, help="Year for which to aggregate stats"
        )

    def handle(self, *args, **options):
        month = options["month"]
        year = options["year"]
        aggregate_monthly_stats.delay(month, year)
        self.stdout.write(
            self.style.SUCCESS("Successfully started task to aggregate monthly stats")
        )
