#!/usr/bin/env python3
"""Этап 1: база данных квеста по кампусу.

Выбор СУБД — SQLite (задача 1.1):
- легковесная, файловая, ноль настройки — идеально для учебного проекта и хакатона;
- драйвер sqlite3 входит в стандартную библиотеку Python;
- схема переносима на PostgreSQL без изменений логики (AUTOINCREMENT -> SERIAL,
  INTEGER-булевы флаги -> BOOLEAN) — задел на «боевой» этап.

Файл инициализации: этот модуль. Таблицы создаются при первом запуске
(``init_db()`` вызывается из ``server.py`` и из ``__main__`` ниже).

Таблицы (задачи 1.2–1.4):
- users: id, full_name, completed_locations (+ служебные name_key, created_at)
- quiz_progress: id, user_id FK, location_id 1..10, is_passed bool
- confidence_answers: id, user_id FK, location_number IN (3,6,10),
  confidence_score 1..10, timestamp

Миграция: БД этапа 0 использовала имена users(name)/visits/confidence.
``init_db()`` переносит их данные в новую схему и удаляет legacy-таблицы.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE = Path(__file__).parent  # /backend
ROOT = BASE.parent  # корень проекта
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "campus.db"
LOCATIONS_PATH = DATA_DIR / "locations.json"

MILESTONES = (3, 6, 10)
TOTAL = 10

# --- SQL создания таблиц (задачи 1.2, 1.3, 1.4) ------------------------------

SQL_USERS = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    completed_locations INTEGER NOT NULL DEFAULT 0,
    name_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

SQL_QUIZ_PROGRESS = """
CREATE TABLE IF NOT EXISTS quiz_progress(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL CHECK(location_id BETWEEN 1 AND 10),
    is_passed INTEGER NOT NULL DEFAULT 1 CHECK(is_passed IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, location_id)
)
"""

SQL_CONFIDENCE_ANSWERS = """
CREATE TABLE IF NOT EXISTS confidence_answers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_number INTEGER NOT NULL CHECK(location_number IN (3, 6, 10)),
    confidence_score INTEGER NOT NULL CHECK(confidence_score BETWEEN 1 AND 10),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, location_number)
)
"""

SCHEMA_SQL = "\n".join([SQL_USERS, SQL_QUIZ_PROGRESS, SQL_CONFIDENCE_ANSWERS])


def norm_name(name: str) -> str:
    """Схлопнуть пробелы: '  Иван   Петров ' -> 'Иван Петров'."""
    return " ".join(name.strip().split())


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _table_cols(con: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return (
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _migrate_legacy(con: sqlite3.Connection) -> None:
    """Перенос данных схемы этапа 0 (users(name)/visits/confidence).

    ВАЖНО: выполняется при PRAGMA foreign_keys=OFF — иначе SQLite при
    ``ALTER TABLE users RENAME`` переписывает REFERENCES во всех дочерних
    таблицах на users_legacy и ломает внешние ключи.
    """
    # 0) Чиним последствия прерванной миграции (если users_legacy остался):
    #    дочерние таблицы могли получить REFERENCES "users_legacy".
    if _table_exists(con, "users_legacy"):
        legacy_rows = con.execute("SELECT COUNT(*) FROM users_legacy").fetchone()[0]
        n_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if legacy_rows and not n_users:
            con.execute(
                """INSERT OR IGNORE INTO users(id, full_name, completed_locations, name_key, created_at)
                   SELECT id, name, 0, name_key, created_at FROM users_legacy"""
            )
        con.execute("DROP TABLE users_legacy")
    for table, sql in (
        ("quiz_progress", SQL_QUIZ_PROGRESS),
        ("confidence_answers", SQL_CONFIDENCE_ANSWERS),
    ):
        if _table_exists(con, table):
            ddl = con.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()["sql"]
            if "users_legacy" in ddl:
                con.execute(f"ALTER TABLE {table} RENAME TO {table}_broken")
                con.execute(sql)
                cols = ", ".join(
                    c for c in ("id", "user_id", "location_id", "is_passed",
                                "location_number", "confidence_score",
                                "created_at", "timestamp")
                    if c in _table_cols(con, f"{table}_broken")
                )
                con.execute(f"INSERT OR IGNORE INTO {table}({cols}) SELECT {cols} FROM {table}_broken")
                con.execute(f"DROP TABLE {table}_broken")

    # 1) users: name -> full_name (сохраняем id, добавляем completed_locations=0)
    if _table_exists(con, "users") and "full_name" not in _table_cols(con, "users"):
        con.execute("ALTER TABLE users RENAME TO users_legacy")
        con.execute(SQL_USERS)
        con.execute(
            """INSERT INTO users(id, full_name, completed_locations, name_key, created_at)
               SELECT id, name, 0, name_key, created_at FROM users_legacy"""
        )
        con.execute("DROP TABLE users_legacy")

    # 2) visits -> quiz_progress (каждый визит = пройденный квиз)
    if _table_exists(con, "visits"):
        con.execute(SQL_QUIZ_PROGRESS)
        con.execute(
            """INSERT OR IGNORE INTO quiz_progress(user_id, location_id, is_passed, created_at)
               SELECT user_id, location_id, 1, created_at FROM visits"""
        )
        con.execute("DROP TABLE visits")

    # 3) confidence -> confidence_answers
    if _table_exists(con, "confidence"):
        con.execute(SQL_CONFIDENCE_ANSWERS)
        con.execute(
            """INSERT OR IGNORE INTO confidence_answers(user_id, location_number, confidence_score, timestamp)
               SELECT user_id, milestone, value, created_at FROM confidence"""
        )
        con.execute("DROP TABLE confidence")


def _recompute_counters(con: sqlite3.Connection) -> None:
    """Синхронизировать users.completed_locations с quiz_progress (источник правды)."""
    con.execute(
        """UPDATE users SET completed_locations = (
               SELECT COUNT(*) FROM quiz_progress
               WHERE quiz_progress.user_id = users.id AND is_passed = 1)"""
    )


def init_db() -> sqlite3.Connection:
    """Создать таблицы при первом запуске + мигрировать legacy. Возвращает соединение."""
    con = connect()
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute(SQL_USERS)
    con.execute(SQL_QUIZ_PROGRESS)
    con.execute(SQL_CONFIDENCE_ANSWERS)
    _migrate_legacy(con)
    _recompute_counters(con)
    con.commit()
    con.execute("PRAGMA foreign_keys = ON")
    return con


# --- Операции уровня модели ---------------------------------------------------

def register_user(con: sqlite3.Connection, full_name: str) -> dict:
    """Найти пользователя по нормализованному имени или создать. Возвращает dict."""
    name = norm_name(full_name)
    if len(name) < 2:
        raise ValueError("Введите имя и фамилию")
    key = name.lower()
    row = con.execute("SELECT * FROM users WHERE name_key=?", (key,)).fetchone()
    if row is None:
        cur = con.execute(
            "INSERT INTO users(full_name, name_key) VALUES(?, ?)", (name, key)
        )
        con.commit()
        user_id, created = cur.lastrowid, True
    else:
        user_id, name, created = row["id"], row["full_name"], False
    passed = [
        r["location_id"]
        for r in con.execute(
            "SELECT location_id FROM quiz_progress WHERE user_id=? AND is_passed=1"
            " ORDER BY location_id",
            (user_id,),
        ).fetchall()
    ]
    confidence = {
        r["location_number"]: r["confidence_score"]
        for r in con.execute(
            "SELECT location_number, confidence_score FROM confidence_answers WHERE user_id=?",
            (user_id,),
        ).fetchall()
    }
    return {
        "user_id": user_id,
        "full_name": name,
        "created": created,
        "passed": passed,
        "count": len(passed),
        "confidence": confidence,
    }


def get_status(con: sqlite3.Connection, user_id: int, location_id: int) -> dict:
    row = con.execute(
        "SELECT 1 FROM quiz_progress WHERE user_id=? AND location_id=? AND is_passed=1",
        (user_id, location_id),
    ).fetchone()
    cnt = con.execute(
        "SELECT completed_locations FROM users WHERE id=?", (user_id,)
    ).fetchone()
    confidence = {
        r["location_number"]: r["confidence_score"]
        for r in con.execute(
            "SELECT location_number, confidence_score FROM confidence_answers WHERE user_id=?",
            (user_id,),
        ).fetchall()
    }
    return {
        "already": row is not None,
        "count": cnt["completed_locations"] if cnt else 0,
        "confidence": confidence,
    }


def complete_location(con: sqlite3.Connection, user_id: int, location_id: int) -> dict:
    if not con.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
        raise LookupError("unknown user")
    cur = con.execute(
        "INSERT OR IGNORE INTO quiz_progress(user_id, location_id, is_passed)"
        " VALUES(?, ?, 1)",
        (user_id, location_id),
    )
    con.commit()
    already = cur.rowcount == 0
    _recompute_counters(con)
    con.commit()
    row = con.execute(
        "SELECT full_name, completed_locations FROM users WHERE id=?", (user_id,)
    ).fetchone()
    cnt = row["completed_locations"]
    return {
        "already": already,
        "count": cnt,
        "full_name": row["full_name"],
        "need_confidence": cnt in MILESTONES,
        "milestone": cnt if cnt in MILESTONES else None,
    }


def check_quiz_answer(
    con: sqlite3.Connection,
    user_id: int,
    location_id: int,
    selected_option: int,
    correct_index: int,
) -> dict:
    """Задача 2.4: серверная проверка ответа на квиз.

    correct_index приходит из статического файла локаций (клиент его не знает).
    При верном ответе и первом прохождении — запись в quiz_progress и +1 к
    completed_locations. Возвращает контракт ТЗ + поле already (расширение).
    """
    if not con.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
        raise LookupError("unknown user")
    is_correct = selected_option == correct_index
    already = (
        con.execute(
            "SELECT 1 FROM quiz_progress WHERE user_id=? AND location_id=? AND is_passed=1",
            (user_id, location_id),
        ).fetchone()
        is not None
    )
    if is_correct and not already:
        con.execute(
            "INSERT OR IGNORE INTO quiz_progress(user_id, location_id, is_passed)"
            " VALUES(?, ?, 1)",
            (user_id, location_id),
        )
        con.commit()
        _recompute_counters(con)
        con.commit()
    count = con.execute(
        "SELECT completed_locations FROM users WHERE id=?", (user_id,)
    ).fetchone()["completed_locations"]
    return {"isCorrect": is_correct, "newCompletedCount": count, "already": already}


def save_confidence(
    con: sqlite3.Connection, user_id: int, location_number: int, score: int
) -> None:
    if location_number not in MILESTONES or not (1 <= score <= 10):
        raise ValueError("bad milestone/value")
    if not con.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
        raise LookupError("unknown user")
    con.execute(
        "INSERT OR REPLACE INTO confidence_answers(user_id, location_number, confidence_score)"
        " VALUES(?, ?, ?)",
        (user_id, location_number, score),
    )
    con.commit()


def get_stats(con: sqlite3.Connection) -> dict:
    users = con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    visits = con.execute(
        "SELECT COUNT(*) c FROM quiz_progress WHERE is_passed=1"
    ).fetchone()["c"]
    return {"users": users, "visits": visits, "total": TOTAL}


def get_confidence_stats(con: sqlite3.Connection) -> dict:
    """Админка: статистика оценок уверенности по этапам 3/6/10.

    Для каждого этапа: число ответов, средний/мин/макс балл,
    распределение по оценкам 1..10 и сами ответы (кто, сколько, когда).
    """
    out = {}
    for m in MILESTONES:
        rows = con.execute(
            """SELECT u.full_name, c.confidence_score, c.timestamp
               FROM confidence_answers c JOIN users u ON u.id = c.user_id
               WHERE c.location_number = ? ORDER BY c.timestamp""",
            (m,),
        ).fetchall()
        scores = [r["confidence_score"] for r in rows]
        dist = {str(i): 0 for i in range(1, 11)}
        for s in scores:
            dist[str(s)] += 1
        out[str(m)] = {
            "count": len(scores),
            "avg": round(sum(scores) / len(scores), 2) if scores else None,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
            "dist": dist,
            "answers": [
                {
                    "user": r["full_name"],
                    "score": r["confidence_score"],
                    "at": r["timestamp"],
                }
                for r in rows
            ],
        }
    return {"milestones": out}


def get_overview(con: sqlite3.Connection) -> dict:
    """Админка: общий срез — счётчики, прохождения по локациям, таблица игроков."""
    users = con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    visits = con.execute(
        "SELECT COUNT(*) c FROM quiz_progress WHERE is_passed=1"
    ).fetchone()["c"]
    by_location = [
        {"location_id": r["location_id"], "passed": r["c"]}
        for r in con.execute(
            "SELECT location_id, COUNT(*) c FROM quiz_progress"
            " WHERE is_passed = 1 GROUP BY location_id ORDER BY location_id"
        ).fetchall()
    ]
    table = []
    for u in con.execute(
        "SELECT id, full_name, completed_locations FROM users"
        " ORDER BY completed_locations DESC, full_name"
    ).fetchall():
        conf = {
            r["location_number"]: r["confidence_score"]
            for r in con.execute(
                "SELECT location_number, confidence_score FROM confidence_answers"
                " WHERE user_id = ?",
                (u["id"],),
            ).fetchall()
        }
        table.append(
            {
                "full_name": u["full_name"],
                "completed": u["completed_locations"],
                "c3": conf.get(3),
                "c6": conf.get(6),
                "c10": conf.get(10),
            }
        )
    return {
        "users": users,
        "visits": visits,
        "total": TOTAL,
        "byLocation": by_location,
        "usersTable": table,
    }


def main() -> None:
    con = init_db()
    tables = [
        r["name"]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    con.close()
    print(f"БД готова: {DB_PATH}")
    print("Таблицы:", ", ".join(tables))


if __name__ == "__main__":
    main()
