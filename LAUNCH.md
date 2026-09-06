# План запуска квеста

## 0. Предусловия

| Что | Зачем | Как установить |
|-----|-------|----------------|
| Python 3.10+ | Бэкенд | `winget install Python.Python.3.12` |
| Node.js 18+ | Firebase CLI | `winget install OpenJS.NodeJS.LTS` |
| Git | Клонирование | `winget install Git.Git` |

## 1. Клонирование и запуск (локально)

```bash
git clone https://github.com/Romas234/ha-kat-on1.git
cd ha-kat-on1

# QR-коды (опционально, PNG уже есть в репозитории)
pip install -r backend/requirements.txt
python backend/generate_qr.py

# Запуск сервера
python backend/server.py
```

Открыть: http://localhost:8000/location/1

## 2. Запуск в локальной сети (телефоны по Wi-Fi)

```bash
# PowerShell
powershell -ExecutionPolicy Bypass -File .\start-lan.ps1
```

Скрипт покажет IP-адрес. Телефоны открывают:
`http://<IP>:8000/location/1`

Если не открывается с телефона — разрешить Python в брандмауэре Windows.

## 3. Деплой фронтенда на Firebase Hosting

```bash
# Установка Firebase CLI
npm install -g firebase-tools

# Авторизация
firebase login

# Деплой (проект уже настроен в .firebaserc)
firebase deploy --only hosting
```

Результат: https://hackathon1-63946.web.app

## 4. Бэкенд из интернета (туннель)

Фронтенд на Firebase, а бэкенд — на ноутбуке. Нужен туннель, чтобы Firebase-фронтенд достучался до бэкенда.

### Вариант A: localtunnel (работает стабильно)

```bash
# В одном терминале — сервер
python backend/server.py

# В другом — туннель
npx -y localtunnel --port 8000
# Выведет: https://xxx.loca.lt
```

### Вариант B: Cloudflare Tunnel (может не работать в некоторых сетях)

```bash
# Скачать: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
# Положить cloudflared.exe в PATH или tools/

cloudflared tunnel --url http://localhost:8000
# Выведет: https://xxx.trycloudflare.com
```

### После запуска туннеля

1. Скопировать URL туннеля
2. Вписать в `frontend/config.js`:
   ```javascript
   window.API_BASE = "https://xxx.loca.lt";
   ```
3. Задеплоить фронтенд заново:
   ```bash
   firebase deploy --only hosting
   ```
4. Перегенерировать QR-коды под Firebase-домен:
   ```bash
   python backend/generate_qr.py --base-url https://hackathon1-63946.web.app
   ```

## 5. Печать QR-кодов

Открыть http://localhost:8000/qrcodes.html и распечатать.
Или напрямую PNG из `frontend/qr_codes/loc01.png` ... `loc10.png`.

## Чек-лист перед демо

- [ ] Сервер запущен (`python backend/server.py`)
- [ ] Туннель запущен (localtunnel / Cloudflare)
- [ ] `config.js` содержит URL туннеля
- [ ] `firebase deploy --only hosting` выполнен
- [ ] Открывается http://localhost:8000/location/1
- [ ] Открывается https://hackathon1-63946.web.app/location/1
- [ ] QR-коды распечатаны
- [ ] Админка: http://localhost:8000/admin.html
