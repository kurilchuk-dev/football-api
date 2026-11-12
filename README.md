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
