from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from visitors.models import Visit


class Command(BaseCommand):
    help = "Delete visits older than VISIT_LOG_RETENTION_DAYS (IP addresses are personal data)."

    def handle(self, *args, **options):
        days = settings.VISIT_LOG_RETENTION_DAYS
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = Visit.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(f"Deleted {deleted} visits older than {days} days")
