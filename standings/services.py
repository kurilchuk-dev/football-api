from django.db.models import F

from matches.models import Match
from teams.models import Team

FORM_LENGTH = 5


def _head_to_head(matches, table):
    """Return {team_id: (points, goal_diff, goals_for)} counting only matches
    between teams that are tied on points with each other."""
    groups = {}
    for row in table:
        groups.setdefault(row["points"], set()).add(row["team"]["id"])

    stats = {row["team"]["id"]: [0, 0, 0] for row in table}
    for match in matches:
        home_id, away_id = match.home_team_id, match.away_team_id
        if not any(home_id in g and away_id in g for g in groups.values()):
            continue
        hs, as_ = match.home_score, match.away_score
        stats[home_id][1] += hs - as_
        stats[home_id][2] += hs
        stats[away_id][1] += as_ - hs
        stats[away_id][2] += as_
        if hs > as_:
            stats[home_id][0] += 3
        elif hs < as_:
            stats[away_id][0] += 3
        else:
            stats[home_id][0] += 1
            stats[away_id][0] += 1
    return {team_id: tuple(values) for team_id, values in stats.items()}


def calculate_standings():
    rows = {
        team.id: {
            "team": {
                "id": team.id,
                "name": team.name,
                "is_our_team": team.is_our_team,
                "logo": team.logo,
                "photo": team.photo,
            },
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "form": [],
        }
        for team in Team.objects.all()
    }

    finished = Match.objects.filter(home_score__isnull=False, away_score__isnull=False).order_by(
        F("match_date").desc(nulls_last=True), F("match_time").desc(nulls_last=True), "-id"
    )
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
            home_result, away_result = "W", "L"
        elif match.home_score < match.away_score:
            away["won"] += 1
            home["lost"] += 1
            home_result, away_result = "L", "W"
        else:
            home["drawn"] += 1
            away["drawn"] += 1
            home_result = away_result = "D"

        # Matches arrive newest first, so the first FORM_LENGTH are the latest.
        if len(home["form"]) < FORM_LENGTH:
            home["form"].append(home_result)
        if len(away["form"]) < FORM_LENGTH:
            away["form"].append(away_result)

    table = list(rows.values())
    for row in table:
        row["form"].reverse()  # oldest -> newest, so the latest match is last
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        row["points"] = row["won"] * 3 + row["drawn"]

    # Teams level on points are ranked first by a mini-table of the matches
    # played between them (points, goal difference, goals scored), then by
    # overall goal difference, overall goals scored and finally by name.
    h2h = _head_to_head(finished, table)
    table.sort(
        key=lambda r: (
            -r["points"],
            *(-v for v in h2h[r["team"]["id"]]),
            -r["goal_difference"],
            -r["goals_for"],
            r["team"]["name"],
        )
    )
    for position, row in enumerate(table, start=1):
        row["position"] = position
    return table
