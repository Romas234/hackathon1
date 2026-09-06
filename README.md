# Квест по новому кампусу УрФУ

QR-квест по 10 точкам кампуса: сканируешь код — читаешь мини-лекцию, отвечаешь на квиз, собираешь прогресс.

## Стек

| Слой | Технология |
|------|------------|
| Бэкенд | Python 3 (stdlib `http.server` + `sqlite3`, без фреймворков) |
| БД | SQLite (`data/campus.db`, пересоздаётся автоматически) |
| Фронтенд | HTML + CSS + JS (без сборки, без CDN) |
| QR-коды | `qrcode` + `pillow` (опционально) |
| Деплой | Firebase Hosting (фронтенд) + локальный сервер (бэкенд) |

## Быстрый старт

```bash
# 1. Зависимости (только для генерации QR-кодов)
pip install -r backend/requirements.txt

# 2. Запуск сервера
python backend/server.py

# 3. Открыть в браузере
# http://localhost:8000/location/1
```

## Структура проекта

```
backend/
  server.py          # API + раздача статики (stdlib)
  db.py              # Схема БД, миграции, CRUD
  generate_qr.py     # Генерация QR-кодов → frontend/qr_codes/
  requirements.txt   # qrcode, pillow (опционально)
frontend/
  index.html         # Игра: 4 экрана (регистрация → лекция → квиз → прогресс)
  admin.html         # Админ-панель: статистика + оценки уверенности
  qrcodes.html       # Страница для печати QR-кодов
  config.js          # URL бэкенда (пусто = локально, или полный URL)
  js/app.js          # Игровая логика
  js/admin.js        # Логика админки
  css/style.css      # Стили (кастомные, ~2 КБ)
  photos/            # SVG-заглушки локаций
  qr_codes/          # PNG QR-коды (генерируются, в .gitignore)
data/
  locations.json     # Контент 10 точек (вопросы, варианты, ответы)
```

## Деплой

### Локально / LAN

```bash
# Один файл — показывает IP и запускает сервер
powershell -ExecutionPolicy Bypass -File .\start-lan.ps1
# Или вручную:
python backend/server.py --host 0.0.0.0 --port 8000
```

Телефоны в той же Wi-Fi-сети: `http://<ваш-IP>:8000/location/1`

### Firebase Hosting (фронтенд) + туннель (бэкенд)

```bash
# 1. Авторизация
npm install -g firebase-tools
firebase login

# 2. Указать URL бэкенда в frontend/config.js:
#    window.API_BASE = "https://<ваш-туннель>";
#    (оставьте "" если бэкенд на том же домене)

# 3. Деплой фронтенда
firebase deploy --only hosting
# Откроется: https://<project-id>.web.app
```

Для туннеля (доступ бэкенда из интернета):
- **localtunnel**: `npx -y localtunnel --port 8000`
- **Cloudflare Tunnel**: `cloudflared tunnel --url http://localhost:8000`

### QR-коды

```bash
# Генерация под локальный IP
python backend/generate_qr.py

# Генерация под публичный URL
python backend/generate_qr.py --base-url https://<URL>

# Печать: http://localhost:8000/qrcodes.html
```

## API

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/user` | Регистрация / вход по имени |
| GET | `/api/location/:id` | Данные локации (без правильного ответа) |
| GET | `/api/location/:id/status?user_id=` | Пройдена ли локация |
| POST | `/api/quiz/check` | Проверка ответа на квиз |
| POST | `/api/confidence` | Оценка уверенности (1–10) на этапах 3/6/10 |
| GET | `/api/locations` | Список всех 10 точек |
| GET | `/api/stats` | Статистика (участники, визиты) |
| GET | `/api/admin/overview` | Админка: обзор |
| GET | `/api/admin/confidence` | Админка: статистика оценок |

## Админ-панель

`http://localhost:8000/admin.html` — статистика участников, прохождение по локациям, оценки уверенности (1–10) после 3/6/10 точек. Автообновление каждые 15 сек.
