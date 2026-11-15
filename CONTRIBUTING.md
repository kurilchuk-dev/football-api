# Contributing

## Branches

- `main` — production only. Updated only by releases (`develop` → `main`). No direct commits.
- `develop` — integration branch. All work branches start from it and merge back into it.
- Work branches: `<type>/<short-kebab-description>`

| Type           | Use for                             |
| -------------- | ----------------------------------- |
| `feat`         | new feature                         |
| `fix`          | bug fix                             |
| `hotfix`       | urgent production fix               |
| `refactor`     | code change without behavior change |
| `perf`         | performance improvement             |
| `docs`         | documentation only                  |
| `style`        | formatting, no logic change         |
| `test`         | adding or fixing tests              |
| `chore`        | tooling, deps, config               |
| `ci` / `build` | CI and build system                 |

Rules: lowercase, digits and hyphens only; 2–5 words; one task per branch;
branch from an up-to-date `develop`; delete after merge.
Examples: `feat/match-list`, `fix/header-overflow`, `chore/update-deps`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org): `type(scope): subject`
— imperative, lowercase, no trailing period. Example: `feat(matches): add live score badge`.

## Pull requests

- Title follows the commit format; keep PRs small and focused.
- `npm run check` and `pytest` must pass.
- Target branch is `develop` (never `main`), squash-merge.
- Release: open a PR `develop` → `main` (regular merge, no squash), then tag the version.
- Hotfix: branch `hotfix/...` from `main`, PR into `main`, then merge `main` back into `develop`.

## Automated checks (Husky)

- pre-commit: branch name, lint-staged (ruff + prettier)
- commit-msg: commitlint
- pre-push: branch name, ruff lint

## Setup

```bash
npm install                          # installs husky and the git hooks
pip install -r requirements.txt -r requirements-dev.txt  # ruff, pytest (inside .venv)
```

The hooks and npm scripts run Python through `scripts/py.js`, which uses `.venv` (or `venv`) automatically, so you do not need to activate it.

## Scripts

- `npm run lint` — ruff check
- `npm run format` / `npm run format:check` — ruff format + prettier
- `npm run check` — lint and format check together
