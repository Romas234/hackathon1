# Квест по новому кампусу УрФУ 🎓

Учебный проект: человек ходит по 10 точкам кампуса, сканирует QR-код на каждой —
открывается веб-страница с описанием места и игровой механикой (мини-лекция + квиз + прогресс).

## Этап 6: итоговый список технологий

| Слой | Технология | Как используется |
|------|------------|------------------|
| Бэкенд — язык | **Python 3** (разработано на 3.14) | вся серверная логика |
| Бэкенд — фреймворк | **без фреймворка** (stdlib `http.server`: `ThreadingHTTPServer` + `SimpleHTTPRequestHandler`) | API-эндпоинты и раздача статики в одном процессе; Flask/Express сознательно не брали — ноль установки для учебного проекта |
| Бэкенд — СУБД | **SQLite** (файл `data/campus.db`) | лёгкая файловая БД; схема переносима на PostgreSQL (задел на прод) |
| Бэкенд — ORM/драйвер | **без ORM**, драйвер `sqlite3` из stdlib + свой слой `backend/db.py` | `init_db()`, `register_user()`, `check_quiz_answer()`, `save_confidence()`; `PRAGMA foreign_keys = ON`, CHECK-ограничения |
| Фронтенд | **HTML + CSS + JavaScript** (ванильный, без сборки) | открывается с телефона по QR, ничего устанавливать не надо |
| Фронтенд — CSS-фреймворк | **без фреймворка**, кастомный `style.css` (~2 КБ) | Bootstrap/Tailwind отклонены: странице нельзя зависеть от CDN — в кампусе может не быть быстрого интернета |
| Фронтенд — роутинг | **SPA без библиотек**: 4 `<section class="screen">`, показ/скрытие через JS `show()` + класс `.active`; QR-ссылки `/location/N` (алиас `/l/N`) | — |
| QR-коды | **Python + `qrcode` + `pillow`** (`backend/requirements.txt`) | `backend/generate_qr.py` → `frontend/qr_codes/locNN.png` |
| Фото-заглушки | **Python** (stdlib) | `backend/make_placeholders.py` → `frontend/photos/locNN.svg` |
| Сервер / деплой | **встроенный сервер** (`0.0.0.0:8000`, `start-lan.ps1`); опционально **Nginx** (`backend/nginx.conf.example`: статика напрямую, `/api/` → прокси) | локальная сеть, телефоны в том же Wi-Fi |

Версии по факту: Python 3.14, `qrcode>=7.4`, `pillow>=10.0`.

## Этап 0: структура проекта

Выбран стек (простейший для хакатона, без сборки):

- **Backend:** Python 3 + стандартная библиотека (`http.server` + `sqlite3`), ноль обязательных зависимостей
- **Frontend:** чистый HTML/CSS/JS (открывается с телефона по QR, ничего устанавливать не надо)
- **Данные:** `data/locations.json` — 10 точек (название, эмодзи, цвет, текст, вопрос, варианты, правильный ответ)

```
хакатон1/
├── backend/
│   ├── server.py          # API + раздача frontend (тонкий HTTP-слой)
│   ├── db.py              # Этап 1: подключение, схема, init_db(), операции модели
│   ├── generate_qr.py     # Этап 4: QR-коды → frontend/qr_codes/
│   ├── make_placeholders.py # Этап 3: SVG-заглушки фото → frontend/photos/
│   ├── nginx.conf.example # Этап 5: пример reverse-proxy (статика + /api/)
│   └── requirements.txt   # только qrcode+pillow (опционально, для QR)
├── frontend/
│   ├── index.html         # 4 экрана: регистрация → лекция → квиз → прогресс
│   ├── admin.html         # админка: статистика уверенности 3/6/10 + срез
│   ├── qrcodes.html       # страница для печати всех QR-кодов (+ ссылка на админку)
│   ├── css/style.css      # кастомный CSS (~2 КБ, без CDN — работает без интернета)
│   ├── js/app.js          # игра (4 экрана)
│   ├── js/admin.js        # админка (автообновление каждые 15 сек)
│   ├── photos/            # locNN.jpg (реальные фото) + locNN.svg (заглушки)
│   └── qr_codes/          # Этап 4: locNN.png → http://<IP>:8000/location/N
├── data/
│   ├── locations.json     # контент 10 точек (источник правды, задача 1.5)
│   └── campus.db          # создаётся автоматически (в .gitignore)
├── start-lan.ps1          # Этап 5: запуск в локальной сети одной командой
├── start-public.ps1       # доступ из интернета (Cloudflare Tunnel)
├── .gitignore
└── README.md
```

## Этап 1: база данных и пользователи

**Задача 1.1 — СУБД:** SQLite. Легковесная файловая БД, ноль настройки,
драйвер `sqlite3` в стандартной библиотеке Python. Схема переносима на
PostgreSQL (задел на прод). Подключение: `backend/db.py → connect()`
(`PRAGMA foreign_keys = ON`). Инициализация таблиц при первом запуске:
`init_db()` — вызывается из `server.py` при старте и напрямую
`python backend/db.py`. Старые таблицы этапа 0 (`users(name)/visits/confidence`)
автоматически мигрируются в новую схему.

**Задача 1.2 — `users`:**

```sql
CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    completed_locations INTEGER NOT NULL DEFAULT 0,
    name_key TEXT NOT NULL UNIQUE,          -- служебное: вход по имени без дублей
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Задача 1.3 — `quiz_progress`** (проходил ли пользователь конкретную точку):

```sql
CREATE TABLE quiz_progress(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL CHECK(location_id BETWEEN 1 AND 10),
    is_passed INTEGER NOT NULL DEFAULT 1 CHECK(is_passed IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, location_id)
);
```

**Задача 1.4 — `confidence_answers`** (уверенность на этапах 3/6/10):

```sql
CREATE TABLE confidence_answers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_number INTEGER NOT NULL CHECK(location_number IN (3, 6, 10)),
    confidence_score INTEGER NOT NULL CHECK(confidence_score BETWEEN 1 AND 10),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, location_number)
);
```

`users.completed_locations` поддерживается триггероподобно: пересчитывается из
`quiz_progress` при каждом засчитывании (`_recompute_counters()`, вызывается из
`complete_location()` и `check_quiz_answer()`),
поэтому счётчик не может разъехаться с фактами.

**Задача 1.5 — данные локаций:** `data/locations.json` — 10 объектов, у каждого:
`id`, `title` (название), `info` (описание), `photo` (`/photos/locNN.jpg`),
`question`, `options` (ровно 4), `correct` (индекс 0–3). Плюс существующие
UI-поля `emoji`/`color` для заглушек, пока нет реальных фото.

## Этап 2: API-эндпоинты

Ключевое изменение: правильный ответ (`correct`) больше НЕ отдаётся клиенту —
ни в `/api/location/:id`, ни в `/api/locations`. Ответ проверяет только сервер
(задача 2.4), подсмотреть его в DevTools нельзя. Фронтенд переведён на новые
эндпоинты, legacy (`/api/register`, `/api/complete`, `/api/status`,
`/api/confidence{milestone,value}`) удалены.

| Задача | Метод | Путь | Запрос | Ответ |
|--------|-------|------|--------|-------|
| 2.1 | POST | `/api/user` | `{"full_name": "..."}` | `{"id", "full_name", "completed_locations"}` (+`created`) |
| 2.2 | GET | `/api/location/:id` | — | локация **без** `correct` |
| 2.3 | GET | `/api/location/:id/status?user_id=` | — | `{"isPassed": true/false}` |
| 2.4 | POST | `/api/quiz/check` | `{"user_id", "location_id", "selected_option"}` | `{"isCorrect", "newCompletedCount"}` (+`already`) |
| 2.5 | POST | `/api/confidence` | `{"user_id", "location_number" (3/6/10), "score" (1–10)}` | `{"success": true}` |
| — | GET | `/api/locations` | — | список 10 точек, без `correct` |
| — | GET | `/api/stats` | — | `{"users", "visits", "total"}` (отладка) |
| — | GET | `/api/admin/overview` | — | админка: счётчики, прохождения по локациям, таблица игроков |
| — | GET | `/api/admin/confidence` | — | админка: статистика оценок 1–10 по этапам 3/6/10 |
| — | GET | `/location/1 … /location/10` | — | ссылка из QR (ТЗ этапа 4) → `index.html` |
| — | GET | `/l/1 … /l/10` | — | короткий алиас (уже распечатанные коды) → `index.html` |

Поля `created` (2.1) и `already` (2.4) — расширения сверх ТЗ-минимума для фронта.
Ошибки: `400 {"error": ...}` (плохие параметры), `404` (неизвестный user/location).
Логика 2.4: неверный ответ — счётчик не растёт; верный + первый раз — запись в
`quiz_progress` и пересчёт `completed_locations`; верный повторно — без дубля.

## Этап 5: деплой в локальной сети

**5.1 — сервер и маршрутизация.** Отдельный Nginx/Apache не обязателен:
встроенный сервер (`python backend/server.py`, только stdlib) уже слушает
`0.0.0.0` и сам разводит маршруты — все `/api/...` уходят на бэкенд
(обработчики `do_GET`/`do_POST`), всё остальное отдаётся как статика
фронтенда из `frontend/`, а `/location/N` и `/l/N` ведут на SPA (`index.html`).
Для «взрослой» схемы есть пример `backend/nginx.conf.example`: Nginx отдаёт
статику напрямую, `/api/...` проксирует на `127.0.0.1:8000`
(скопировать в `conf.d`, поправить `root`, `nginx -s reload`).

**5.2 — запуск.** Одной командой (показывает LAN-IP и URL для телефонов):

```powershell
powershell -ExecutionPolicy Bypass -File .\start-lan.ps1
# или вручную:
python backend/server.py --host 0.0.0.0 --port 8000
```

Узнать свой IP: `ipconfig` (строка «IPv4-адрес») — телефоны в той же Wi-Fi-сети
открывают `http://<ваш-IP>:8000/location/1`. После смены IP перегенерируйте QR:
`python backend/generate_qr.py` (IP подставится сам). Если страница не
открывается с телефона — разрешите Python в брандмауэре Windows
(«Разрешить приложение через брандмауэр»).

Проверка эндпоинтов (пример, подставьте свой IP):

```powershell
Invoke-WebRequest http://<ваш-IP>:8000/api/location/3 | Select-Object StatusCode
Invoke-WebRequest http://<ваш-IP>:8000/api/stats | Select-Object -Expand Content
Invoke-WebRequest http://<ваш-IP>:8000/location/3 | Select-Object StatusCode
Invoke-WebRequest http://<ваш-IP>:8000/qr_codes/loc01.png | Select-Object StatusCode
```

## Доступ из внешней сети (интернет)

Быстрый путь — Cloudflare Tunnel (бесплатно, без настройки роутера):

```powershell
# 1. Скачайте cloudflared-windows-amd64.exe:
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
# положите как tools\cloudflared.exe или добавьте в PATH.
# 2. Запуск сервера + туннеля одной командой:
powershell -ExecutionPolicy Bypass -File .\start-public.ps1
# 3. В выводе найдите строку https://xxx.trycloudflare.com — сайт уже снаружи.
# 4. QR для интернета (LAN-коды при этом НЕ трогайте):
python backend/generate_qr.py --base-url https://xxx.trycloudflare.com --out frontend/qr_codes_public
```

Проверено: страница, `/api/stats`, `/api/location/N` отвечают через публичный URL.

Важно:
- Quick-tunnel URL случаен и живёт, пока запущен `start-public.ps1`. Постоянный адрес — именованный туннель (`cloudflared tunnel create/login`) или ngrok с reserved-доменом.
- Альтернатива без туннеля: проброс порта 8000 на роутере + DDNS — дольше, нужен доступ к роутеру.
- Безопасность: админка и API без авторизации — это демо-режим для хакатона. Надолго без присмотра наружу не выставлять.

## Запуск (кратко)

```powershell
# 1. Запуск сервера (раздаёт frontend + API)
powershell -ExecutionPolicy Bypass -File .\start-lan.ps1
# 2. Открыть локально: http://localhost:8000/location/1
# 3. С телефона в той же сети: http://<ваш-IP>:8000/location/1
```

## Этап 4: QR-коды (задача 4.1)

Скрипт `backend/generate_qr.py` (Python + `qrcode`): для каждой из 10 локаций
генерирует QR на `http://<IP>:<port>/location/<id>` (формат из ТЗ) и кладёт PNG
в `/frontend/qr_codes/` (`loc01.png … loc10.png`). IP определяется автоматически,
можно задать вручную `--host`. Сервер раздаёт PNG как статику.

```powershell
python -m pip install -r backend/requirements.txt
python backend/generate_qr.py                      # IP сам, порт 8000
python backend/generate_qr.py --host <ваш-IP> --port 8000
python backend/generate_qr.py --base-url https://xxx.trycloudflare.com
# PNG → frontend/qr_codes/loc01.png … loc10.png
# Печать: http://localhost:8000/qrcodes.html
```

Старые коды формата `/l/N` продолжают работать (алиас на сервере), но все новые
печатайте из `/qrcodes.html` после перегенерации.

## Этап 3: фронтенд (4 экрана, SPA)

**3.1 — структура:** один `frontend/index.html`, 4 `<section class="screen">`,
роутинг — показ/скрытие через JS (`show()` + класс `.active`). Вместо
Bootstrap/Tailwind — кастомный CSS (~2 КБ): страница должна открываться с
телефона по QR даже без быстрого интернета, CDN-зависимости недопустимы.
Вёрстка mobile-first (`max-width: 560px`, `viewport`).

**3.2 — Экран 1 (регистрация):** поле «Введите имя и фамилию» + «Продолжить»
→ `POST /api/user {full_name}` → `user_id` в `localStorage` → Экран 2.
Локация берётся из URL QR-кода (`/location/N`, алиас `/l/N`), а не «первая» — каждый QR ведёт на
свою точку.

**3.3 — Экран 2 (локация):** фотография, название, текст. Сначала `GET
/api/location/:id/status?user_id=` (2.3): если пройдена — «Ты уже был(а) на
этой локации. Квиз недоступен.» и «Продолжить» → Экран 4; иначе данные из 2.2
и «Продолжить» → Экран 3. Фото: `renderPhoto()` грузит `photo` (`.jpg`);
если файла нет — одноимённый `.svg`; если и его нет — эмодзи на градиенте.
Заглушки: `python backend/make_placeholders.py`. Реальные фото достаточно
положить рядом как `locNN.jpg` — они подхватятся автоматически.

**3.5 — Экран 3 (квиз):** вопрос + 4 кнопки сеткой 2×2. Клик → `POST
/api/quiz/check` (2.4): неверно — кнопка краснеет, остальные варианты остаются
активными (можно пробовать дальше); верно — кнопка зеленеет, появляется
«Продолжить» → Экран 4. Защита от дабл-кликов и сетевых ошибок.

**3.6 — Экран 4 (прогресс):** «Молодец, [имя]», текст из `newCompletedCount`
(ответ 2.4). Если count равен 3, 6 или 10 — 10 кнопок 1–10 → `POST
/api/confidence {user_id, location_number: count, score}` (2.5, передаётся
именно счётчик, не location_id) → кнопки скрываются, «Спасибо за ответ!».

## Админка: статистика уверенности

Страница `http://<ваш-IP>:8000/admin.html` (ссылка есть на `/qrcodes.html` —
странице организаторов; из игрового интерфейса игроков ссылки нет).

Что показывает:
- **Обзор:** число участников, визитов, средний прогресс; автообновление каждые 15 сек + кнопка «Обновить».
- **Прохождение по локациям:** сколько человек прошло каждую из 10 точек (бары).
- **Уверенность (1–10) после 3, 6 и 10 локаций:** средний/мин/макс балл, число ответов, гистограмма распределения оценок 1–10 и таблица «кто — сколько — когда».
- **Участники:** имя, пройдено X из 10, оценки после 3/6/10 (прочерк — ещё не отвечал).

API админки (без авторизации — только для локальной сети хакатона):
`GET /api/admin/overview`, `GET /api/admin/confidence`.

## Игровая механика (сейчас)

1. Регистрация по имени + фамилии (прогресс подтягивается при повторном входе).
2. Экран лекции: фото (с fallback), название, текст про место.
3. Квиз: 4 варианта, неверные клики красят в красное, верный — в зелёное и открывает «Продолжить».
4. Прогресс: `X из 10`, прогресс-бар, на 3/6/10 точках — вопрос про уверенность (1–10).
5. Повторный скан той же точки: «Ты уже был(а)» — квиз пропускается, баллы не дублируются.

## Firebase Hosting (фронтенд в интернете)

Фронтенд деплоится на Firebase Hosting (CDN, HTTPS, домен `*.web.app`).
Бэкенд работает отдельно на вашем ноутбуке (через Cloudflare Tunnel).

### Настройка

```powershell
# 1. Установите Firebase CLI (нужен Node.js):
npm install -g firebase-tools

# 2. Авторизация в Google:
firebase login

# 3. Создайте проект в Firebase Console:
#    https://console.firebase.google.com → Add project → скопируйте Project ID

# 4. Укажите Project ID в .firebaserc (замените "" на ваш ID):
#    "projects": { "default": "ваш-project-id" }

# 5. Укажите URL бэкенда в frontend/config.js:
#    window.API_BASE = "https://xxx.trycloudflare.com";

# 6. Задеплойте фронтенд:
firebase deploy

# 7. Откройте: https://<ваш-project-id>.web.app/location/1
```

### Конфигурация API

`frontend/config.js` — переменная `window.API_BASE`:

| Значение | Когда использовать |
|----------|-------------------|
| `""` (пусто) | Локально / LAN (фронтенд и бэкенд на одном домене) |
| `"https://xxx.trycloudflare.com"` | Фронтенд на Firebase, бэкенд через Cloudflare Tunnel |

### QR-коды для Firebase

```powershell
python backend/generate_qr.py --base-url https://<ваш-project-id>.web.app
```

### Важно

- Бэкенд **обязан** быть запущен (`python backend/server.py` + Cloudflare Tunnel).
- Если ноутбук выключится — фронтенд загрузится, но API не будет отвечать.
- Бесплатно: Firebase Hosting (10 ГБ/мес) + Cloudflare Tunnel.

## Git

```powershell
# Установите Git с https://git-scm.com/download/win, затем:
git init
git add .
git commit -m "Админка: статистика уверенности 3/6/10 + срез по игрокам"
```
