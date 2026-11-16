# football-api

Backend (REST API) for the football team website: news, matches and the tournament table.

Frontend repository: `football-web`

## Tech stack

- Python 3.12+
- Django + Django REST Framework
- PostgreSQL (SQLite for local development)
- drf-spectacular (OpenAPI / Swagger docs)
- pytest

## Getting started

```bash
git clone <repo-url> football-api
cd football-api

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # fill in the values
python manage.py migrate
python manage.py runserver
```

API: http://localhost:8000/api/
Docs: http://localhost:8000/api/docs/

## Environment variables

| Variable               | Description                                |
| ---------------------- | ------------------------------------------ |
| `SECRET_KEY`           | Django secret key                          |
| `DEBUG`                | `True` for local development               |
| `DATABASE_URL`         | Database connection string                 |
| `CORS_ALLOWED_ORIGINS` | Frontend URL, e.g. `http://localhost:5173` |

## Visitor log (IP and location)

Every request to `/api/` (except the docs) is saved as a `Visit` (admin: «Відвідувачі»): IP, path,
status and the approximate location (country, region, city, coordinates). An IP never reveals a
street; the point is usually the city, sometimes off by kilometres.

1. Create a free account at maxmind.com, copy the **Account ID** and generate a **License key**.
2. Put them into `.env` (and into the Render environment): `MAXMIND_ACCOUNT_ID`, `MAXMIND_LICENSE_KEY`.
3. `python manage.py update_geoip` downloads `geoip/GeoLite2-City.mmdb` (git-ignored; Render does
   it on every deploy). Without the file visits are still saved, just without a location.
4. `python manage.py purge_visits` deletes visits older than `VISIT_LOG_RETENTION_DAYS` (90 by
   default); it also runs on every deploy. IP addresses are personal data, so keep it short.

Set `VISIT_LOG_ENABLED=False` to switch the log off. Requests answered by the Cloudflare cache do
not reach the API and are not logged.

## Tests

```bash
pytest
```

## Workflow

See [CONTRIBUTING.md](CONTRIBUTING.md) for branches, commits, pull requests and git hooks.

## Roadmap

- [ ] Project setup and CI
- [ ] News API
- [ ] Teams and matches API
- [ ] Tournament table
- [ ] Authentication (admin)
