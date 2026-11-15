from django.db import models
from django.db.models import F, Q


class Match(models.Model):
    home_team = models.ForeignKey(
        "teams.Team", on_delete=models.PROTECT, related_name="home_matches"
    )
    away_team = models.ForeignKey(
        "teams.Team", on_delete=models.PROTECT, related_name="away_matches"
    )
    home_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(null=True, blank=True)
    played_at = models.DateTimeField(
        null=True, blank=True, help_text="Leave empty if the date is not known yet."
    )
    round = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Round (matchday) number, e.g. 5 for round 5."
    )

    class Meta:
        # Matches without a date go last, on every database.
        ordering = [F("played_at").desc(nulls_last=True), "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(home_team=F("away_team")),
                name="home_and_away_teams_differ",
            )
        ]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"
