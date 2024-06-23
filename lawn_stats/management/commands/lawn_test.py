# myapp/management/commands/ssh_tunnel.py
from django.core.management.base import BaseCommand

from lawn_stats.models import AfatFleettype


class Command(BaseCommand):
    help = "Set up SSH tunnel for MySQL"

    def handle(self, *args, **kwargs):
        try:
            # Check if the table exists
            objects = AfatFleettype.objects.all()
            for obj in objects:
                self.stdout.write(self.style.SUCCESS(obj.name))
        except Exception:
            self.stdout.write("Table does not exist")
