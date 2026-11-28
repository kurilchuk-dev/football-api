# football-api

Backend (REST API) for the «Черкаси ФАМ» team website: teams, matches, the tournament table and the
squad. The data is edited in the Django admin; the API is public and read-only.

Frontend repository: `football-web`

## Tech stack

- Python 3.12+
- Django + Django REST Framework, django-unfold (admin theme)
- PostgreSQL in production (Neon), SQLite for local development
- Cloudinary for uploaded images in production
- drf-spectacular (OpenAPI / Swagger docs)
- pytest, ruff

## Getting started

```bash
git clone <repo-url> football-api
cd football-api

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env             # fill in the values
python manage.py migrate
python manage.py createsuperuser # for the admin
python manage.py seed_calendar   # optional: teams and the championship calendar
python manage.py runserver
```

API: http://localhost:8000/api/
Docs: http://localhost:8000/api/docs/
Admin: http://localhost:8000/admin/

## Endpoints

| Endpoint                                              | Returns                                     |
| ----------------------------------------------------- | ------------------------------------------- |
| `GET /api/teams/`, `/api/teams/{id}/`                 | teams with logo and team photo              |
| `GET /api/matches/`, `/api/matches/{id}/`             | all matches; `?team=<id>`                   |
| `GET /api/matches/results/`, `/api/matches/upcoming/` | played / not yet played matches; `?team=`   |
| `GET /api/standings/`                                 | the table, calculated from the matches      |
| `GET /api/players/`                                   | active players; `?team=<id>`, `?our_team=1` |
| `GET /api/staff/`                                     | coaching staff                              |
| `POST /api/visitors/ping/`                            | counts a browser, see below                 |
| `GET /health/`, `/health/db/`                         | the app is up / the database answers        |

The rules of the table live in `standings/services.py`. The site repeats them for its simulator
(`src/features/standings/calculate.ts` in `football-web`): change both together.

## Commands

| Command                   | What it does                                          |
| ------------------------- | ----------------------------------------------------- |
| `manage.py seed_calendar` | creates the teams and matches of the 2026-2027 season |
| `manage.py import_roster` | adds players from a text file                         |
| `manage.py update_geoip`  | downloads the GeoLite2 database                       |
| `manage.py purge_visits`  | deletes old visit records                             |

## Environment variables

| Variable               | Description                                |
| ---------------------- | ------------------------------------------ |
| `SECRET_KEY`           | Django secret key                          |
| `DEBUG`                | `True` for local development               |
| `DATABASE_URL`         | Database connection string                 |
| `CORS_ALLOWED_ORIGINS` | Frontend URL, e.g. `http://localhost:5173` |

The full list, including production, is in `.env.example` and [DEPLOY.md](DEPLOY.md).

## Visitor log (IP and location)

Every request to `/api/` (except the docs) is saved as a `Visit` (admin: «Відвідувачі»): IP, path,
status and the approximate location (country, region, city, coordinates). An IP never reveals a
street; the point is usually the city, sometimes off by kilometres. The site also sends one ping per
browser session with a random id, so that visitors can be counted, not only requests.

1. Create a free account at maxmind.com, copy the **Account ID** and generate a **License key**.
2. Put them into `.env` (and into the Render environment): `MAXMIND_ACCOUNT_ID`, `MAXMIND_LICENSE_KEY`.
3. `python manage.py update_geoip` downloads `geoip/GeoLite2-City.mmdb` (git-ignored; Render does
   it on every deploy). Without the file visits are still saved, just without a location.
4. `python manage.py purge_visits` deletes visits older than `VISIT_LOG_RETENTION_DAYS` (90 by
   default); it also runs on every deploy. IP addresses are personal data, so keep it short.

Set `VISIT_LOG_ENABLED=False` to switch the log off. Requests answered by the Cloudflare cache do
not reach the API and are not logged.

### Flood limits

The log has hourly limits (0 switches one off). Over a limit, requests for data are still answered
but no longer saved; a ping is answered with `429`.

| Variable                  | Default | Limits                          |
| ------------------------- | ------- | ------------------------------- |
| `VISIT_PING_LIMIT_PER_IP` | 30      | pings of one address            |
| `VISIT_PING_LIMIT_TOTAL`  | 600     | pings of all addresses          |
| `VISIT_LOG_LIMIT_PER_IP`  | 600     | saved requests of one address   |
| `VISIT_LOG_LIMIT_TOTAL`   | 5000    | saved requests of all addresses |

The counters are kept in memory, so they start over after a restart.

## Tests

```bash
pytest
```

## Workflow

See [CONTRIBUTING.md](CONTRIBUTING.md) for branches, commits, pull requests and git hooks.
