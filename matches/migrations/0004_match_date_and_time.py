"""Split the kick-off moment into a separate date and time (both optional).

The existing `played_at` values are converted to Kyiv local date and time, so
nothing changes for the people looking at the site.
"""

from zoneinfo import ZoneInfo

from django.db import migrations, models
from django.db.models import F, Q

KYIV = ZoneInfo("Europe/Kyiv")


def split_played_at(apps, schema_editor):
    Match = apps.get_model("matches", "Match")
    for match in Match.objects.exclude(played_at__isnull=True):
        local = match.played_at.astimezone(KYIV)
        match.match_date = local.date()
        match.match_time = local.time().replace(second=0, microsecond=0)
        match.save(update_fields=["match_date", "match_time"])


def join_date_and_time(apps, schema_editor):
    from datetime import datetime

    Match = apps.get_model("matches", "Match")
    for match in Match.objects.exclude(match_date__isnull=True).exclude(match_time__isnull=True):
        match.played_at = datetime.combine(match.match_date, match.match_time, tzinfo=KYIV)
        match.save(update_fields=["played_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0003_match_played_at_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="match_date",
            field=models.DateField(
                blank=True, help_text="Leave empty if the date is not known yet.", null=True
            ),
        ),
        migrations.AddField(
            model_name="match",
            name="match_time",
            field=models.TimeField(
                blank=True,
                help_text="Kick-off time (Kyiv). Leave empty if only the date is known so far.",
                null=True,
            ),
        ),
        migrations.RunPython(split_played_at, join_date_and_time),
        migrations.AlterModelOptions(
            name="match",
            options={
                "ordering": [
                    models.OrderBy(F("match_date"), descending=True, nulls_last=True),
                    models.OrderBy(F("match_time"), descending=True, nulls_last=True),
                    "-id",
                ]
            },
        ),
        migrations.RemoveField(model_name="match", name="played_at"),
        migrations.AddConstraint(
            model_name="match",
            constraint=models.CheckConstraint(
                condition=Q(("match_time__isnull", True), ("match_date__isnull", False), _connector="OR"),
                name="time_needs_a_date",
            ),
        ),
    ]
