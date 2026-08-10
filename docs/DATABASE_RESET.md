# Обнуление БД на хостинге

Инструкция для полного сброса PostgreSQL и заливки чистой базы: **1 пользователь Rootoss**, **1 admin**, **0 статей** (статьи добавляются через админку).

## Что будет после seed

| Сущность | Значение |
|----------|----------|
| Admin | `admin@mobauniverse.com` / пароль из `ADMIN_PASSWORD` в `.env` |
| Rootoss | `rootoss@mobauniverse.com` / `player123` |
| Статьи | нет (пусто) |
| Категории | ranks, replays, roles, heroes, macro, mental, draft, beginners |

## Локально (Git Bash)

```bash
cd /c/Projects/mobauniverse-backend
source .venv/Scripts/activate

# Убедитесь, что DATABASE_URL в .env указывает на нужную БД
python scripts/reset_db.py
```

Скрипт:
1. Удаляет все таблицы (`DROP` через SQLAlchemy metadata)
2. Создаёт таблицы заново
3. Запускает `scripts/seed.py`

## На хостинге (VPS + Docker)

### Вариант A: Postgres на хосте, backend в Docker

1. Подключитесь к серверу по SSH.
2. **Сделайте бэкап**, если нужны старые данные:
   ```bash
   pg_dump -U moba mobauniverse > backup_$(date +%F).sql
   ```
3. Остановите backend (чтобы не было активных соединений):
   ```bash
   cd /path/to/mobauniverse-backend
   docker compose down
   ```
4. Пересоздайте базу (или очистите схему):
   ```bash
   psql -U moba -d postgres -c "DROP DATABASE IF EXISTS mobauniverse;"
   psql -U moba -d postgres -c "CREATE DATABASE mobauniverse OWNER moba;"
   ```
5. Убедитесь, что в `.env` заданы `DATABASE_URL` и `ADMIN_PASSWORD`.
6. Запустите reset **внутри контейнера** или на хосте с тем же `DATABASE_URL`:
   ```bash
   docker compose run --rm backend python scripts/reset_db.py
   ```
   Или на хосте с активированным venv и тем же `.env`:
   ```bash
   source .venv/Scripts/activate   # или source .venv/bin/activate на Linux
   python scripts/reset_db.py
   ```
7. Поднимите backend:
   ```bash
   docker compose up -d --build
   ```

### Вариант B: только seed без полного drop (если таблицы уже есть)

```bash
python scripts/seed.py
```

Seed **не удаляет** существующие статьи — только upsert пользователей и категорий. Для полной очистки используйте `reset_db.py`.

## Alembic

Если вы используете миграции Alembic вместо `create_all`:

```bash
alembic downgrade base
alembic upgrade head
python scripts/seed.py
```

## Проверка

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/evergreen/articles
# → {"items":[],"total":0,...} или []
```

Войдите в админку `/admin/login`, добавьте статьи — они автоматически появятся в `/sitemap.xml`.

## Sitemap

Sitemap **динамический**: генерируется из PostgreSQL при каждом запросе `/sitemap.xml`. При создании, редактировании или удалении статьи через админку URL добавляется/обновляется/исчезает без ручного редактирования файлов.
