"""Fill an empty database with the futsal championship calendar 2026-2027.

Source: the approved calendar of the Cherkasy district championship (13 teams,
13 rounds, 78 matches). Only round 1 has kick-off times in the calendar; for the
other rounds the times are PLACEHOLDERS (10:00, 11:00, 12:00 for the matches of a
day) and should be corrected in the admin.

Matches without a result are "upcoming"; results are entered later in the admin.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db import transaction

from matches.models import Match
from teams.models import Team

KYIV = ZoneInfo("Europe/Kyiv")

OUR_TEAM = "Черкаси ФАМ"
OUR_TEAM_CITY = "Черкаси"

# Placeholder kick-off times for days without times in the calendar.
DEFAULT_TIMES = ("10:00", "11:00", "12:00")

FAM = OUR_TEAM
MOLOD = "Молодь"
BARS = "Барс"
TEMP = "Темп"
NGU = "31 п НГУ"
SV = "FC SV"
BAKERY = "Бейкері"
KOZAKY = "Черкаські Козаки"
ROSAVA = "Росава"
GARANT = "Гарант бут 2020"
OLIMP = "Олімп"
SIZO = "СІЗО"
AUTODOC = "Autodoc"

# (round, [(date, [(home, away) or (time, home, away), ...]), ...])
CALENDAR = [
    (
        1,
        [
            (
                "2026-11-15",
                [
                    ("10:00", MOLOD, BARS),
                    ("11:00", TEMP, NGU),
                    ("12:00", SV, BAKERY),
                    ("13:00", KOZAKY, ROSAVA),
                    ("14:00", GARANT, FAM),
                    ("15:00", OLIMP, SIZO),
                ],
            )
        ],
    ),
    (
        2,
        [
            ("2026-11-21", [(ROSAVA, GARANT), (BARS, OLIMP), (FAM, TEMP)]),
            ("2026-11-22", [(SIZO, SV), (AUTODOC, KOZAKY), (NGU, MOLOD)]),
        ],
    ),
    (
        3,
        [
            ("2026-11-28", [(GARANT, AUTODOC), (TEMP, ROSAVA), (MOLOD, FAM)]),
            ("2026-11-29", [(OLIMP, NGU), (SV, BARS), (BAKERY, SIZO)]),
        ],
    ),
    (
        4,
        [
            ("2026-12-12", [(BARS, BAKERY), (NGU, SV), (FAM, OLIMP)]),
            ("2026-12-13", [(ROSAVA, MOLOD), (AUTODOC, TEMP), (KOZAKY, GARANT)]),
        ],
    ),
    (
        5,
        [
            ("2026-12-19", [(TEMP, KOZAKY), (MOLOD, AUTODOC), (OLIMP, ROSAVA)]),
            ("2026-12-20", [(SV, FAM), (BAKERY, NGU), (SIZO, BARS)]),
        ],
    ),
    (
        6,
        [
            ("2026-12-26", [(NGU, SIZO), (FAM, BAKERY), (ROSAVA, SV)]),
            ("2026-12-27", [(AUTODOC, OLIMP), (KOZAKY, MOLOD), (GARANT, TEMP)]),
        ],
    ),
    (
        7,
        [
            ("2027-01-09", [(MOLOD, GARANT), (BAKERY, ROSAVA), (SV, AUTODOC)]),
            ("2027-01-10", [(BARS, NGU), (OLIMP, KOZAKY), (SIZO, FAM)]),
        ],
    ),
    (
        8,
        [
            ("2027-01-16", [(TEMP, MOLOD), (GARANT, OLIMP), (FAM, BARS)]),
            ("2027-01-17", [(KOZAKY, SV), (ROSAVA, SIZO), (AUTODOC, BAKERY)]),
        ],
    ),
    (
        9,
        [
            ("2027-01-23", [(OLIMP, TEMP), (BAKERY, KOZAKY), (SIZO, AUTODOC)]),
            ("2027-01-24", [(SV, GARANT), (BARS, ROSAVA), (NGU, FAM)]),
        ],
    ),
    (
        10,
        [
            ("2027-01-30", [(ROSAVA, NGU), (AUTODOC, BARS), (KOZAKY, SIZO)]),
            ("2027-01-31", [(GARANT, BAKERY), (TEMP, SV), (MOLOD, OLIMP)]),
        ],
    ),
    (
        11,
        [
            ("2027-02-06", [(FAM, ROSAVA), (NGU, AUTODOC), (BARS, KOZAKY)]),
            ("2027-02-07", [(SV, MOLOD), (BAKERY, TEMP), (SIZO, GARANT)]),
        ],
    ),
    (
        12,
        [
            ("2027-02-20", [(GARANT, BARS), (KOZAKY, NGU), (AUTODOC, FAM)]),
            ("2027-02-21", [(OLIMP, SV), (MOLOD, BAKERY), (TEMP, SIZO)]),
        ],
    ),
    (
        13,
        [
            ("2027-02-27", [(BAKERY, OLIMP), (SIZO, MOLOD), (BARS, TEMP)]),
            ("2027-02-28", [(NGU, GARANT), (FAM, KOZAKY), (ROSAVA, AUTODOC)]),
        ],
    ),
]


def iter_matches():
    """Yield (round, kick-off datetime in Kyiv time, home, away) for every match."""
    for round_number, days in CALENDAR:
        for date, day_matches in days:
            for index, entry in enumerate(day_matches):
                if len(entry) == 3:
                    time, home, away = entry
                else:
                    home, away = entry
                    time = DEFAULT_TIMES[index]
                played_at = datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=KYIV)
                yield round_number, played_at, home, away


class Command(BaseCommand):
    help = (
        "Create the teams and the 78 matches of the 2026-2027 championship calendar. "
        "Does nothing if matches already exist (so admin edits are never undone) "
        "unless --force is given; with --force only missing teams/matches are added."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true", help="Add missing teams/matches even if matches exist"
        )

    @transaction.atomic
    def handle(self, *args, force, **options):
        if Match.objects.exists() and not force:
            self.stdout.write("Matches already exist, nothing to seed.")
            return

        teams = {}
        created_teams = created_matches = 0
        for round_number, played_at, home, away in iter_matches():
            for name in (home, away):
                if name not in teams:
                    is_ours = name == OUR_TEAM
                    teams[name], created = Team.objects.get_or_create(
                        name=name,
                        defaults={"is_our_team": is_ours, "city": OUR_TEAM_CITY if is_ours else ""},
                    )
                    created_teams += created
            _, created = Match.objects.get_or_create(
                home_team=teams[home],
                away_team=teams[away],
                round=round_number,
                defaults={"match_date": played_at.date(), "match_time": played_at.time()},
            )
            created_matches += created

        self.stdout.write(f"Added {created_teams} team(s) and {created_matches} match(es).")
