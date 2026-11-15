from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from players.models import Player
from teams.models import Team


def split_name(full_name):
    """'Surname Name Patronymic' -> ('Name Patronymic', 'Surname')."""
    last_name, _, first_name = full_name.strip().partition(" ")
    return first_name.strip(), last_name


class Command(BaseCommand):
    help = (
        "Add players to a team from a text file with one full name per line "
        "('Surname Name [Patronymic]'). Players that already exist are skipped, "
        "so the command is safe to run again."
    )

    def add_arguments(self, parser):
        parser.add_argument("file", type=Path, help="UTF-8 text file, one player per line")
        parser.add_argument("--team", required=True, help="Exact name of the team")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be added")

    def handle(self, *args, file, team, dry_run, **options):
        try:
            team_obj = Team.objects.get(name=team)
        except Team.DoesNotExist:
            raise CommandError(f'Team "{team}" does not exist.') from None
        if not file.is_file():
            raise CommandError(f"File not found: {file}")

        added = skipped = 0
        for line in file.read_text(encoding="utf-8").splitlines():
            line = " ".join(line.split())
            if not line or line.startswith("#"):
                continue
            first_name, last_name = split_name(line)
            if not first_name:
                raise CommandError(f'Expected "Surname Name", got "{line}".')
            exists = Player.objects.filter(
                team=team_obj, first_name=first_name, last_name=last_name
            ).exists()
            if exists:
                skipped += 1
                continue
            if not dry_run:
                Player.objects.create(team=team_obj, first_name=first_name, last_name=last_name)
            added += 1

        verb = "Would add" if dry_run else "Added"
        self.stdout.write(f"{verb} {added} player(s), skipped {skipped} existing.")
