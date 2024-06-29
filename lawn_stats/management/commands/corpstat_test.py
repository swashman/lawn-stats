from django.core.management.base import BaseCommand

from lawn_stats.models import CorputilsCorpstats as CorpStats
from lawn_stats.models import MonthlyCorpStats


class Command(BaseCommand):

    def handle(self, *args, **options):
        for corp2 in MonthlyCorpStats.objects.all():
            self.stdout.write(
                self.style.SUCCESS(f"Corp: {corp2.get_corporation().corporation_name}")
            )
            input_corp = corp2.get_corporation().pk
            corp = CorpStats.objects.get(corp=input_corp)
            total_mains = corp.main_count
            self.stdout.write(
                self.style.SUCCESS(f"Corp: {input_corp} - Mains: {total_mains}")
            )
