from django.db import models


class Player(models.Model):
    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="players")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    number = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Shirt number; leave empty if not assigned yet."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(fields=["team", "number"], name="unique_number_per_team")
        ]

    def __str__(self):
        prefix = f"{self.number}. " if self.number is not None else ""
        return f"{prefix}{self.first_name} {self.last_name}"


class StaffMember(models.Model):
    class Role(models.TextChoices):
        HEAD_COACH = "head_coach", "Head coach"
        ASSISTANT = "assistant", "Assistant coach"
        MANAGER = "manager", "Team manager"

    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="staff")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
