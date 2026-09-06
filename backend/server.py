#!/usr/bin/env python3
"""Учебный проект: квест по кампусу УрФУ. Сервер на stdlib + SQLite. Запуск в локальной сети: python server.py --host 0.0.0.0 --port 8000"""
import argparse
import json
import os
import re
import sys
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE = Path(__file__).parent  # /backend
ROOT = BASE.parent  # корень проекта
FRONTEND_DIR = ROOT / "frontend"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "campus.db"
LOCATIONS_PATH = DATA_DIR / "locations.json"

sys.path.insert(0, str(BASE))
from db import (  # noqa: E402
    check_quiz_answer,
    get_confidence_stats,
    get_overview,
    get_stats,
    get_status,
    init_db,
    register_user,
    save_confidence,
)


def get_db():
    """Совместимость: инициализирует БД (схема + миграция) и возвращает соединение."""
    return init_db()


def load_locations():
    with open(LOCATIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def find_location(location_id: int):
    for loc in load_locations():
        if loc["id"] == location_id:
            return loc
    return None


# Поля, разрешённые клиенту. Правильный ответ (correct) НЕ отдаём —
# иначе ответ можно подсмотреть в DevTools; проверяет только сервер (2.4).
PUBLIC_FIELDS = ("id", "title", "emoji", "color", "info", "photo", "question", "options")


def public_location(loc: dict) -> dict:
    return {k: loc[k] for k in PUBLIC_FIELDS if k in loc}


class Handler(SimpleHTTPRequestHandler):
    server_version = "CampusQuest/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        ln = int(self.headers.get("Content-Length", 0) or 0)
        if ln <= 0:
            return {}
        raw = self.rfile.read(ln)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/api/locations":
            # Публичный список: без правильных ответов (см. PUBLIC_FIELDS)
            return self._send_json([public_location(l) for l in load_locations()])

        # Совместимость: старые прямые запросы JSON тоже без correct
        if path in ("/locations.json", "/data/locations.json"):
            return self._send_json([public_location(l) for l in load_locations()])

        # Задача 2.2: GET /api/location/:id — локация без правильного ответа
        m = re.fullmatch(r"/api/location/(\d+)", path)
        if m:
            loc = find_location(int(m.group(1)))
            if loc is None:
                return self._send_json({"error": "unknown location"}, 404)
            return self._send_json(public_location(loc))

        # Задача 2.3: GET /api/location/:id/status — проходил ли пользователь
        m = re.fullmatch(r"/api/location/(\d+)/status", path)
        if m:
            location_id = int(m.group(1))
            if find_location(location_id) is None:
                return self._send_json({"error": "unknown location"}, 404)
            try:
                user_id = int(qs.get("user_id", ["0"])[0])
            except ValueError:
                return self._send_json({"error": "bad params"}, 400)
            con = get_db()
            try:
                if not con.execute(
                    "SELECT 1 FROM users WHERE id=?", (user_id,)
                ).fetchone():
                    return self._send_json({"error": "unknown user"}, 404)
                st = get_status(con, user_id, location_id)
            finally:
                con.close()
            return self._send_json({"isPassed": st["already"]})

        if path == "/api/stats":
            con = get_db()
            try:
                stats = get_stats(con)
            finally:
                con.close()
            return self._send_json(stats)

        # Админка (без авторизации — только для локальной сети хакатона)
        if path == "/api/admin/confidence":
            con = get_db()
            try:
                res = get_confidence_stats(con)
            finally:
                con.close()
            return self._send_json(res)

        if path == "/api/admin/overview":
            con = get_db()
            try:
                res = get_overview(con)
            finally:
                con.close()
            return self._send_json(res)

        # /location/1 ... /location/10 (формат QR из ТЗ этапа 4)
        # и короткий алиас /l/1 ... /l/10 (уже распечатанные коды) -> index.html
        if path.startswith("/location/") or path.startswith("/l/"):
            self.path = "/index.html"
            return super().do_GET()

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        data = self._read_json()
        con = get_db()

        if path == "/api/user":
            # Задача 2.1: регистрация / получение пользователя
            con = get_db()
            try:
                u = register_user(con, str(data.get("full_name", "")))
            except ValueError as e:
                con.close()
                return self._send_json({"error": str(e)}, 400)
            con.close()
            return self._send_json(
                {
                    "id": u["user_id"],
                    "full_name": u["full_name"],
                    "completed_locations": u["count"],
                    "created": u["created"],  # расширение: новый ли пользователь
                }
            )

        if path == "/api/quiz/check":
            # Задача 2.4: серверная проверка ответа на квиз
            if not all(k in data for k in ("user_id", "location_id", "selected_option")):
                con.close()
                return self._send_json({"error": "bad params"}, 400)
            try:
                user_id = int(data.get("user_id", 0))
                location_id = int(data.get("location_id", 0))
                selected = int(data.get("selected_option", -1))
            except (ValueError, TypeError):
                con.close()
                return self._send_json({"error": "bad params"}, 400)
            loc = find_location(location_id)
            if loc is None:
                con.close()
                return self._send_json({"error": "unknown location"}, 404)
            if not 0 <= selected < len(loc["options"]):
                con.close()
                return self._send_json({"error": "bad selected_option"}, 400)
            try:
                res = check_quiz_answer(
                    con, user_id, location_id, selected, loc["correct"]
                )
            except LookupError as e:
                con.close()
                return self._send_json({"error": str(e)}, 404)
            con.close()
            return self._send_json(res)

        if path == "/api/confidence":
            # Задача 2.5: сохранение оценки уверенности
            try:
                user_id = int(data.get("user_id", 0))
                number = int(data.get("location_number", 0))
                score = int(data.get("score", 0))
            except (ValueError, TypeError):
                con.close()
                return self._send_json({"error": "bad params"}, 400)
            try:
                save_confidence(con, user_id, number, score)
            except ValueError as e:
                con.close()
                return self._send_json({"error": str(e)}, 400)
            except LookupError as e:
                con.close()
                return self._send_json({"error": str(e)}, 404)
            con.close()
            return self._send_json({"success": True})

        con.close()
        return self._send_json({"error": "not found"}, 404)


def main():
    ap = argparse.ArgumentParser(description="Campus Quest server (LAN)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    os.chdir(FRONTEND_DIR)
    get_db().close()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Откройте в локальной сети: http://<ваш-IP>:{args.port}/l/1")
    print(f"Локально: http://localhost:{args.port}/l/1")
    print(f"QR-коды: http://localhost:{args.port}/qrcodes.html")
    print("Остановка: Ctrl+C")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено")


if __name__ == "__main__":
    main()
