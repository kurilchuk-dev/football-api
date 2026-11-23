from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Team(models.Model):
    name = models.CharField("назва", max_length=100, unique=True)
    city = models.CharField("місто", max_length=100, blank=True)
    is_our_team = models.BooleanField("наша команда", default=False)
    logo = models.ImageField("логотип", upload_to="team_logos/", blank=True)
    photo = models.ImageField(
        "фото команди",
        upload_to="team_photos/",
        blank=True,
        help_text="Загальне фото команди: відкривається на сайті, коли натиснути на команду.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "команда"
        verbose_name_plural = "команди"
        constraints = [
            models.UniqueConstraint(
                fields=["is_our_team"],
                condition=Q(is_our_team=True),
                name="only_one_our_team",
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.is_our_team and Team.objects.filter(is_our_team=True).exclude(pk=self.pk).exists():
            raise ValidationError({"is_our_team": "«Наша команда» вже вибрана для іншої команди."})
