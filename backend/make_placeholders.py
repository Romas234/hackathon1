#!/usr/bin/env python3
"""Этап 3: временные SVG-заглушки фото для Экрана 2.

Читает data/locations.json (title, emoji, color) и создаёт
frontend/photos/locNN.svg — градиент цвета локации + эмодзи + название.

Цепочка показа фото на Экране 2 (см. frontend/js/app.js renderPhoto):
    locNN.jpg (реальное фото) -> locNN.svg (эта заглушка) -> эмодзи-фон.
Положите рядом одноимённый .jpg — и он автоматически станет приоритетным,
перегенерировать ничего не нужно.

Использование: python backend/make_placeholders.py
"""
import html
import json
from pathlib import Path

BASE = Path(__file__).parent  # /backend
ROOT = BASE.parent
DATA_PATH = ROOT / "data" / "locations.json"
OUT_DIR = ROOT / "frontend" / "photos"

W, H = 800, 450

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{color}"/><stop offset="1" stop-color="#0f172a"/>
</linearGradient></defs>
<rect width="{w}" height="{h}" fill="url(#g)"/>
<text x="{w_half}" y="215" text-anchor="middle" font-size="130">{emoji}</text>
<text x="{w_half}" y="330" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="44" font-weight="bold" fill="#ffffff">{title}</text>
<text x="{w_half}" y="375" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="24" fill="#ffffff" opacity="0.8">УрФУ · Новый кампус</text>
</svg>
"""


def main() -> None:
    locs = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for loc in locs:
        svg = SVG.format(
            w=W, h=H, w_half=W // 2,
            color=html.escape(loc.get("color", "#1e6fff")),
            emoji=html.escape(loc.get("emoji", "📍")),
            title=html.escape(loc.get("title", "")),
        )
        p = OUT_DIR / ("loc%02d.svg" % loc["id"])
        p.write_text(svg, encoding="utf-8")
        print("%d. %s -> %s" % (loc["id"], loc["title"], p.relative_to(ROOT)))
    print("Готово: %d заглушек. Реальные фото кладите рядом как locNN.jpg." % len(locs))


if __name__ == "__main__":
    main()
