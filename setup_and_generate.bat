@echo off
title Генерация QR-кодов — Квест УрФУ
cd /d "%~dp0"

echo.
echo   ============================================
echo   Автоматическая настройка и генерация QR
echo   ============================================
echo.

:: 1. Создание виртуального окружения (если нет или сломано)
if not exist ".venv\Scripts\pip.exe" (
    if exist ".venv" (
        echo   [*] Удаляю сломанное виртуальное окружение...
        rmdir /s /q .venv
    )
    echo   [*] Создаю виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo   [!] Ошибка: не удалось создать venv. Убедитесь, что Python установлен.
        pause
        exit /b 1
    )
    echo   [+] Виртуальное окружение создано.
) else (
    echo   [+] Виртуальное окружение уже существует.
)

:: 2. Активация
call .venv\Scripts\activate.bat

:: 3. Установка зависимостей
echo.
echo   [*] Устанавливаю зависимости...
pip install -r backend\requirements.txt --quiet
if errorlevel 1 (
    echo   [!] Ошибка при установке зависимостей.
    pause
    exit /b 1
)
echo   [+] Зависимости установлены.

:: 4. Генерация QR-кодов
echo.
echo   [*] Генерирую QR-коды...
python backend\generate_qr.py
if errorlevel 1 (
    echo   [!] Ошибка при генерации QR-кодов.
    pause
    exit /b 1
)

:: 5. Готово
echo.
echo   ============================================
echo   Готово! QR-коды сохранены в frontend\qr_codes\
echo   Для печати откройте: qrcodes.html
echo   ============================================
echo.
pause
