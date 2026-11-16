import io
import tarfile

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from visitors.geo import reset_reader

URL = "https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz"


class Command(BaseCommand):
    help = "Download GeoLite2-City from MaxMind (needs MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY)."

    def handle(self, *args, **options):
        account, key = settings.MAXMIND_ACCOUNT_ID, settings.MAXMIND_LICENSE_KEY
        if not (account and key):
            self.stdout.write("MAXMIND_ACCOUNT_ID / MAXMIND_LICENSE_KEY are not set, skipping")
            return
        response = requests.get(URL, auth=(account, key), timeout=120)
        if response.status_code != 200:
            raise CommandError(f"MaxMind answered {response.status_code}")
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
            member = next((m for m in archive.getmembers() if m.name.endswith(".mmdb")), None)
            if member is None:
                raise CommandError("No .mmdb file in the downloaded archive")
            settings.GEOIP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            settings.GEOIP_DB_PATH.write_bytes(archive.extractfile(member).read())
        reset_reader()
        self.stdout.write(f"GeoIP database saved to {settings.GEOIP_DB_PATH}")
