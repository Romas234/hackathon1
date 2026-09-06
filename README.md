# Квест по новому кампусу УрФУ

QR-квест по 10 точкам кампуса: сканируешь код — читаешь мини-лекцию, отвечаешь на квиз, собираешь прогресс.

## Запуск

### Windows

Двойной клик по `start.bat` или:

```
python backend\server.py
```

### Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

### Открыть в браузере

- **Квест**: http://localhost:8000/location/1
- **Админка**: http://localhost:8000/admin.html
- **QR-коды (печать)**: http://localhost:8000/qrcodes.html

Для работы в локальной сети (телефоны по Wi-Fi) — `http://<ваш-IP>:8000/location/1`.

## Структура

```
backend/
  server.py          # API + раздача статики
  db.py              # Схема БД, миграции, CRUD
  generate_qr.py     # Генерация QR-кодов
  requirements.txt   # qrcode, pillow (опционально)
frontend/
  index.html         # Игра: 4 экрана
  admin.html         # Админ-панель
  qrcodes.html       # Печать QR-кодов
  js/app.js          # Игровая логика
  js/admin.js        # Логика админки
  css/style.css      # Стили
  photos/            # SVG-заглушки локаций
  qr_codes/          # PNG QR-коды (генерируются)
data/
  locations.json     # Контент 10 точек
```

## Стек

| Слой | Технология |
|------|------------|
| Бэкенд | Python 3 (stdlib `http.server` + `sqlite3`) |
| БД | SQLite (`data/campus.db`) |
| Фронтенд | HTML + CSS + JS (без сборки) |
| QR | `qrcode` + `pillow` |

## QR-коды

Двойной клик по 'setup_and_generate.bat'

## API

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/user` | Регистрация / вход |
| GET | `/api/location/:id` | Данные локации |
| GET | `/api/location/:id/status?user_id=` | Пройдена ли локация |
| POST | `/api/quiz/check` | Проверка ответа |
| POST | `/api/confidence` | Оценка уверенности (1-10) |
| GET | `/api/locations` | Все 10 точек |
| GET | `/api/stats` | Статистика |
| GET | `/api/admin/overview` | Админка: обзор |
| GET | `/api/admin/confidence` | Админка: оценки |
