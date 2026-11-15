from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Match(models.Model):
    home_team = models.ForeignKey(
        "teams.Team",
        on_delete=models.PROTECT,
        related_name="home_matches",
        verbose_name="господарі",
    )
    away_team = models.ForeignKey(
        "teams.Team", on_delete=models.PROTECT, related_name="away_matches", verbose_name="гості"
    )
    home_score = models.PositiveSmallIntegerField("голи господарів", null=True, blank=True)
    away_score = models.PositiveSmallIntegerField("голи гостей", null=True, blank=True)
    match_date = models.DateField(
        "дата", null=True, blank=True, help_text="Залиште порожнім, якщо дата ще невідома."
    )
    match_time = models.TimeField(
        "час",
        null=True,
        blank=True,
        help_text="Початок матчу (за Києвом). Залиште порожнім, якщо відома лише дата.",
    )
    round = models.PositiveSmallIntegerField(
        "тур", null=True, blank=True, help_text="Номер туру, наприклад 5."
    )

    class Meta:
        # Newest first; matches without a date (or time) go last, on every database.
        verbose_name = "матч"
        verbose_name_plural = "матчі"
        ordering = [
            F("match_date").desc(nulls_last=True),
            F("match_time").desc(nulls_last=True),
            "-id",
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(home_team=F("away_team")),
                name="home_and_away_teams_differ",
            ),
            models.CheckConstraint(
                condition=Q(match_time__isnull=True) | Q(match_date__isnull=False),
                name="time_needs_a_date",
            ),
        ]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

    def clean(self):
        # Plain (non-field) errors: this runs in forms that only show some of the fields
        # (the round page, the editable list), where a per-field error would not fit.
        super().clean()
        problems = []
        if self.home_team_id and self.home_team_id == self.away_team_id:
            problems.append("Команда не може грати сама з собою.")
        if self.match_time is not None and self.match_date is None:
            problems.append("Вкажіть і дату, або очистіть час.")
        if (self.home_score is None) != (self.away_score is None):
            problems.append("Вкажіть рахунок обох команд або залиште обидва поля порожніми.")
        if self.round is not None and self.home_team_id and self.away_team_id:
            same_round = Match.objects.filter(round=self.round).exclude(pk=self.pk)
            for team_id in {self.home_team_id, self.away_team_id}:
                if same_round.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id)).exists():
                    team = self.home_team if team_id == self.home_team_id else self.away_team
                    problems.append(f"{team} уже грає в турі {self.round}.")
        if problems:
            raise ValidationError(problems)

    @property
    def played_at(self):
        """Kick-off as an aware datetime (Kyiv time); None until both date and time are set."""
        if self.match_date is None or self.match_time is None:
            return None
        return timezone.make_aware(datetime.combine(self.match_date, self.match_time))
