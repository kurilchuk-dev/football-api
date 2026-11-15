from django.db import models


class Team(models.Model):
    name = models.CharField("назва", max_length=100, unique=True)
    city = models.CharField("місто", max_length=100, blank=True)
    is_our_team = models.BooleanField("наша команда", default=False)
    logo = models.ImageField("логотип", upload_to="team_logos/", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "команда"
        verbose_name_plural = "команди"

    def __str__(self):
        return self.name
