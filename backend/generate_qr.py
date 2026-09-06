#!/usr/bin/env python3
"""Этап 4 (задача 4.1): генерация QR-кодов для 10 локаций.

Требует: python -m pip install -r backend/requirements.txt (qrcode, pillow).

Использование:
    python backend/generate_qr.py                 # IP определится сам
    python backend/generate_qr.py --host 10.5.56.12 --port 8000
    python backend/generate_qr.py --out frontend/qr_codes
    python backend/generate_qr.py --base-url https://kvest-urfu.trycloudflare.com
        # QR для доступа ИЗ ИНТЕРНЕТА (туннель cloudflared/ngrok, см. README)

Каждый QR ведёт на <base>/location/<id> (формат из ТЗ).
PNG сохраняются в /frontend/qr_codes/ (loc01.png … loc10.png) и раздаются
сервером как статика. Печать: http://<IP>:8000/qrcodes.html
"""
import argparse
import socket
from pathlib import Path

BASE = Path(__file__).parent  # /backend
ROOT = BASE.parent  # корень проекта
DATA_PATH = ROOT / "data" / "locations.json"
DEFAULT_OUT = ROOT / "frontend" / "qr_codes"


def local_ip() -> str:
    """IP машины в локальной сети (для телефонов, сканирующих QR)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # пакетов не шлёт, только выбирает интерфейс
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main():
    ap = argparse.ArgumentParser(description="Генерация QR-кодов 10 локаций")
    ap.add_argument("--host", default=local_ip(), help="IP сервера (по умолчанию авто)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--base-url", default=None,
                    help="полный публичный адрес, напр. https://xxx.trycloudflare.com "
                         "(имеет приоритет над --host/--port, схема обязательна)")
    args = ap.parse_args()

    try:
        import qrcode
    except ImportError:
        print("Нужно установить: python -m pip install -r backend/requirements.txt")
        raise SystemExit(1)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    import json

    locs = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert len(locs) == 10, "ожидалось 10 локаций, получено %d" % len(locs)
    if args.base_url:
        base = args.base_url.rstrip("/")
        assert base.startswith(("http://", "https://")), "в --base-url нужна схема http(s)://"
    else:
        base = f"http://{args.host}:{args.port}"
    for l in locs:
        url = f"{base}/location/{l['id']}"
        img = qrcode.make(url, border=2)
        p = out / ("loc%02d.png" % l["id"])
        img.save(p)
        print(f"{l['id']}. {l['title']}: {url} -> {p}")
    print("Готово. Распечатайте PNG (или страницу /qrcodes.html) и расклейте по точкам.")


if __name__ == "__main__":
    main()
