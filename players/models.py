from django.db import models


class Player(models.Model):
    team = models.ForeignKey(
        "teams.Team", on_delete=models.CASCADE, related_name="players", verbose_name="команда"
    )
    first_name = models.CharField("ім'я", max_length=50)
    last_name = models.CharField("прізвище", max_length=50)
    number = models.PositiveSmallIntegerField(
        "номер",
        null=True,
        blank=True,
        help_text="Номер на футболці; залиште порожнім, якщо ще не призначено.",
    )
    photo = models.ImageField(
        "фото", upload_to="player_photos/", blank=True, help_text="Портрет для сторінки команди."
    )
    is_active = models.BooleanField("грає", default=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "гравець"
        verbose_name_plural = "гравці"
        constraints = [
            models.UniqueConstraint(fields=["team", "number"], name="unique_number_per_team")
        ]

    def __str__(self):
        prefix = f"{self.number}. " if self.number is not None else ""
        return f"{prefix}{self.first_name} {self.last_name}"


class StaffMember(models.Model):
    class Role(models.TextChoices):
        HEAD_COACH = "head_coach", "Головний тренер"
        ASSISTANT = "assistant", "Помічник тренера"
        MANAGER = "manager", "Менеджер команди"

    team = models.ForeignKey(
        "teams.Team", on_delete=models.CASCADE, related_name="staff", verbose_name="команда"
    )
    first_name = models.CharField("ім'я", max_length=50)
    last_name = models.CharField("прізвище", max_length=50)
    role = models.CharField("посада", max_length=20, choices=Role.choices)

    class Meta:
        verbose_name = "тренерський штаб"
        verbose_name_plural = "тренерський штаб"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
