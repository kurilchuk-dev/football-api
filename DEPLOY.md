# Деплой: інструкція (Render + Neon + Cloudinary + Cloudflare Pages)

Схема:

```
GitHub (main) ─┬─► Cloudflare Pages ── сайт (football-web)
               └─► Render ──────────── API  (football-api-eu, Frankfurt)
                      ├─► Neon        — Postgres
                      └─► Cloudinary  — логотипи й фото гравців
```

**Правило CD: усе деплоїться тільки зі злиття в `main`.** Гілки `develop` і feature-гілки на прод не потрапляють.

> Умови безкоштовних тарифів змінюються: перед стартом перевірте актуальні ліміти на сайтах сервісів.

---

## 0. Що знадобиться

Акаунти (усі можна створити через GitHub): **Neon**, **Cloudinary**, **Render**, **Cloudflare**.

---

## 1. База даних: Neon (Postgres)

1. На neon.tech створіть проєкт (регіон ближчий до Render, напр. Frankfurt).
2. Скопіюйте **Connection string** (формат `postgresql://user:pass@host/db?sslmode=require`). Це значення `DATABASE_URL`.

> Чому не Postgres від Render: безкоштовна база там обмежена в часі життя. Neon безкоштовний без терміну.

## 2. Фото: Cloudinary

1. Створіть акаунт, на Dashboard скопіюйте **API Environment variable**:
   `cloudinary://<api_key>:<api_secret>@<cloud_name>`. Це значення `CLOUDINARY_URL`.
2. Нічого більше налаштовувати не треба: усі завантаження з адмінки підуть туди автоматично.

## 3. API: Render

1. Render → **New → Blueprint** → оберіть репозиторій `football-api` (файл `render.yaml` підхопиться сам).
2. Render попросить значення змінних із `sync: false`:

| Змінна                                               | Значення                                                                                                |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                                       | рядок із Neon (крок 1)                                                                                  |
| `CLOUDINARY_URL`                                     | рядок із Cloudinary (крок 2)                                                                            |
| `CORS_ALLOWED_ORIGINS`                               | адреса сайту, напр. `https://football-web.pages.dev` (з кроку 4; спершу можна порожнє й додати пізніше) |
| `CSRF_TRUSTED_ORIGINS`                               | адреса API, напр. `https://football-api.onrender.com`                                                   |
| `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | вхід в адмінку (створюється при першому деплої)                                                         |

3. Після деплою перевірте: `https://<сервіс>.onrender.com/health/` → `{"status": "ok"}`, а `/api/docs/` показує Swagger.
   `/health/` не чіпає базу (його пінгує UptimeRobot і Render, тому не можна будити Neon щоразу); перевірити базу вручну: `/health/db/`.
4. У Settings сервісу залиште **Auto-Deploy: After CI checks pass** і **Branch: main** (так уже вказано в `render.yaml`).

Що відбувається на кожному деплої (див. `buildCommand` у `render.yaml`): встановлення залежностей → `collectstatic` → `migrate` → (повторно) створення суперкористувача, якщо його ще немає.

> **Безкоштовний тариф Render засинає** після ~15 хв без запитів, перший запит після цього триває від хвилини і довше. Щоб API не засинало, `/health/` пінгує **UptimeRobot** (HTTP(s)-монітор, інтервал 5 хв, акаунт власника).
>
> Заплановані запуски GitHub Actions для цього **не підходять**: на безкоштовних репозиторіях GitHub затримує й пропускає `schedule`-запуски (на практиці раз на кілька годин замість кожних 10 хв), тому API все одно засинало. Workflow `.github/workflows/keep-alive.yml` лишився лише як запасний варіант.
>
> Якщо сайт знову довго вантажиться, перевірте монітор в UptimeRobot (статус Up, час відповіді) і що `/health/` відповідає `200`.

## 4. Сайт: Cloudflare Pages

1. Cloudflare → **Workers & Pages → Create → Pages → Connect to Git** → `football-web`.
2. Налаштування збірки:
    - **Production branch: `main`**
    - Build command: `npm run build`
    - Build output directory: `dist`
    - Змінні середовища: `VITE_API_URL` = `https://<сервіс>.onrender.com/api`, `NODE_VERSION` = `22`
3. **Branch deployments → None** (Settings → Builds), щоб preview-збірки з інших гілок не створювались: деплой лише з `main`.
4. Скопіюйте адресу сайту (`https://….pages.dev`) і впишіть у `CORS_ALLOWED_ORIGINS` на Render (крок 3). Render перезапуститься.

Маршрути React Router (`/team`, `/matches` …) працюють після оновлення сторінки: Cloudflare Pages сам віддає `index.html` для невідомих шляхів.

---

## 5. Перший запуск: дані

Прод-база порожня. Два способи:

- **Через адмінку** (`https://<сервіс>.onrender.com/admin/`): додати команди (з логотипами), гравців (з фото), матчі.
- **Перенести локальні дані** (з вашого комп'ютера, проти Neon):
    ```bash
    # 1. вивантажити локальні дані
    python manage.py dumpdata teams matches players --indent 2 --output data.json
    # 2. завантажити у прод-базу (підставте рядок із Neon)
    DATABASE_URL="postgresql://..." CLOUDINARY_URL="cloudinary://..." SECRET_KEY=x python manage.py migrate
    DATABASE_URL="postgresql://..." SECRET_KEY=x python manage.py loaddata data.json
    ```
    Файли логотипів/фото при цьому **не переносяться**: завантажте їх заново в адмінці (вони підуть у Cloudinary).
    `data.json` містить персональні дані гравців: не комітьте його.

---

## 6. Як відбувається реліз

1. Працюєте в feature-гілках → PR у `develop` (CI перевіряє).
2. Реліз: PR `develop` → `main` (звичайне злиття, без squash).
3. Після злиття:
    - Cloudflare Pages сам збирає й публікує сайт;
    - Render чекає, поки CI на цьому коміті буде зеленим, і розгортає API.
4. Відкат: у Render → Deploys → **Rollback**; у Cloudflare Pages → Deployments → **Rollback** до попереднього.

## 7. Змінні середовища (довідник)

| Змінна                        | Призначення                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------- |
| `SECRET_KEY`                  | секретний ключ Django (на Render генерується автоматично)                        |
| `DEBUG`                       | `False` на проді                                                                 |
| `HTTPS_ONLY`                  | `True` на проді: редірект на HTTPS, захищені куки, довіра до проксі Render       |
| `ALLOWED_HOSTS`               | додатково до хоста Render (він додається автоматично)                            |
| `DATABASE_URL`                | Postgres                                                                         |
| `CLOUDINARY_URL`              | якщо задано, медіа зберігаються в Cloudinary; якщо ні, у локальній теці `media/` |
| `CORS_ALLOWED_ORIGINS`        | дозволені адреси фронтенду                                                       |
| `CORS_ALLOWED_ORIGIN_REGEXES` | необов'язково, напр. `https://.*\.pages\.dev` для preview-збірок                 |
| `CSRF_TRUSTED_ORIGINS`        | адреса API для входу в адмінку по HTTPS                                          |
| `SECURE_HSTS_SECONDS`         | необов'язково, HSTS (вмикайте, коли впевнені, що HTTPS працює стабільно)         |
