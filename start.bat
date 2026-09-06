@echo off
title Квест по кампусу УрФУ
cd /d "%~dp0"
echo.
echo   Квест по новому кампусу УрФУ
echo   Откройте в браузере: http://localhost:8000/location/1
echo   Админка: http://localhost:8000/admin.html
echo   Остановка: Ctrl+C
echo.
python backend\server.py --host 0.0.0.0 --port 8000
pause
