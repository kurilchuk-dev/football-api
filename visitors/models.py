from django.db import models


class Visit(models.Model):
    ip = models.GenericIPAddressField("IP", null=True, blank=True, db_index=True)
    visitor_id = models.CharField(
        "ID відвідувача",
        max_length=36,
        blank=True,
        db_index=True,
        help_text="Випадковий анонімний ID браузера (з пінгу сайту); порожній у звичайних запитів.",
    )
    country = models.CharField("країна", max_length=100, blank=True)
    country_code = models.CharField("код країни", max_length=2, blank=True)
    region = models.CharField("область", max_length=100, blank=True)
    city = models.CharField("місто", max_length=100, blank=True)
    latitude = models.FloatField("широта", null=True, blank=True)
    longitude = models.FloatField("довгота", null=True, blank=True)
    path = models.CharField("шлях", max_length=255)
    method = models.CharField("метод", max_length=10)
    status_code = models.PositiveSmallIntegerField("статус")
    user_agent = models.CharField("браузер", max_length=255, blank=True)
    created_at = models.DateTimeField("час", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "візит"
        verbose_name_plural = "візити"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ip} {self.path}"
