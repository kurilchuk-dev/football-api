from matches.models import Match
from teams.models import Team


def calculate_standings():
    rows = {
        team.id: {
            "team": {"id": team.id, "name": team.name, "is_our_team": team.is_our_team},
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        for team in Team.objects.all()
    }

    finished = Match.objects.filter(home_score__isnull=False, away_score__isnull=False)
    for match in finished:
        home = rows[match.home_team_id]
        away = rows[match.away_team_id]

        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += match.home_score
        home["goals_against"] += match.away_score
        away["goals_for"] += match.away_score
        away["goals_against"] += match.home_score

        if match.home_score > match.away_score:
            home["won"] += 1
            away["lost"] += 1
        elif match.home_score < match.away_score:
            away["won"] += 1
            home["lost"] += 1
        else:
            home["drawn"] += 1
            away["drawn"] += 1

    table = list(rows.values())
    for row in table:
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        row["points"] = row["won"] * 3 + row["drawn"]

    table.sort(
        key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]["name"])
    )
    for position, row in enumerate(table, start=1):
        row["position"] = position
    return table
