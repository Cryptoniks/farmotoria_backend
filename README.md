# Farmotoria — бэкенд

Django 6 + DRF + SimpleJWT. База — **Neon** (PostgreSQL), хостинг — **Render**. Фронтенд — отдельный репозиторий `farmotoria_frontend` (Vercel).

## Структура

```
farmotoria_backend/
├── farmotoria_backend/settings/   # base · dev · prod · test
├── game/
│   ├── models.py
│   ├── services/                  # вся игровая логика: player, skills, inventory, field, extraction, processing
│   ├── views/                     # auth · shop · field · production (приём запроса → сервис → ответ)
│   ├── serializers/
│   ├── management/commands/       # seed_game_data, game_report
│   ├── migrations/0001_initial.py # единственная миграция
│   └── tests/                     # pytest
├── Dockerfile.render              # образ для Render
├── render.yaml                    # Blueprint (необязательно)
└── requirements.txt / requirements-dev.txt
```

## Локальный запуск

Без `DATABASE_URL` используется SQLite — ставить PostgreSQL не нужно.

```bash
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env             # при желании впишите DATABASE_URL от dev-ветки Neon
python manage.py migrate
python manage.py seed_game_data    # культуры, здания, рецепты, навыки
python manage.py createsuperuser
python manage.py runserver
```

Админка: http://127.0.0.1:8000/admin/ · Swagger: http://127.0.0.1:8000/api/docs/ · Тесты: `pytest`

## Деплой

**Neon:** Dashboard → Connect → строка **Pooled connection** (`…-pooler…/neondb?sslmode=require`).

**Render** (сервис `farmotoria-backend`):
- Settings → **Runtime: Docker**, **Dockerfile Path:** `./Dockerfile.render`, **Health Check Path:** `/api/farmotoria/ping/`.
- Environment:
  - `SECRET_KEY` — длинная случайная строка (`python -c "import secrets; print(secrets.token_urlsafe(50))"`);
  - `DATABASE_URL` — строка Neon;
  - `CORS_ALLOWED_ORIGINS` — адрес фронтенда, например `https://farmotoria.vercel.app`;
  - (необязательно) `CORS_ALLOWED_ORIGIN_REGEXES` — `^https://farmotoria-.*\.vercel\.app$` для превью Vercel.
- `ALLOWED_HOSTS` указывать не нужно — адрес `*.onrender.com` подставляется автоматически.
- При каждом старте выполняются `migrate` и `seed_game_data` (обе безопасно запускать повторно).
- Суперпользователь: сервис → **Shell** → `python manage.py createsuperuser`.

> Бесплатный Render засыпает после ~15 минут простоя. Добыча ресурсов не теряется — она начисляется при следующем заходе игрока.

## Игровые данные

Стартовый баланс задан в `game/management/commands/seed_game_data.py`.
- `python manage.py seed_game_data` — добавить недостающее (правки из админки не перезаписываются);
- `python manage.py seed_game_data --update` — перезаписать значениями из файла;
- `python manage.py game_report` — сводка и проверка целостности.
