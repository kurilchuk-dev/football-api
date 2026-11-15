from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    city = models.CharField(max_length=100, blank=True)
    is_our_team = models.BooleanField(default=False)
    logo = models.ImageField(upload_to="team_logos/", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
