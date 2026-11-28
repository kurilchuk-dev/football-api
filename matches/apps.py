from django.apps import AppConfig


class MatchesConfig(AppConfig):
    name = "matches"

    def ready(self):
        from config.rebuild import connect

        connect()

    verbose_name = "Матчі"
