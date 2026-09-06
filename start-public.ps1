<# Доступ к квесту ИЗ ИНТЕРНЕТА через Cloudflare Tunnel (quick tunnel).
   Публикует локальный сервер наружу, печатает https-URL для QR-кодов.

   Использование:
     powershell -ExecutionPolicy Bypass -File .\start-public.ps1
     powershell -ExecutionPolicy Bypass -File .\start-public.ps1 -Port 8000

   Требуется cloudflared в PATH или tools\cloudflared.exe:
     https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
   После появления URL сгенерируйте интернет-QR:
     python backend/generate_qr.py --base-url <URL-из-туннеля>

   Внимание: quick-tunnel URL случаен и живёт пока запущен скрипт.
   Для постоянного адреса нужен именованный туннель / ngrok (см. README).
   Админка (/admin.html, /api/admin/...) без авторизации — надолго
   без присмотра публикацию держать не стоит, только на время демо.
#>
param([int]$Port = 8000)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf -and (Test-Path -LiteralPath "tools\cloudflared.exe")) {
  $cf = (Resolve-Path -LiteralPath "tools\cloudflared.exe").Path
}
if (-not $cf) {
  Write-Host "Не найден cloudflared. Скачайте cloudflared-windows-amd64.exe:"
  Write-Host "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  Write-Host "и положите как tools\cloudflared.exe или добавьте в PATH."
  exit 1
}

try {
  $null = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/api/stats" -f $Port) -UseBasicParsing -TimeoutSec 3
  Write-Host ("Сервер уже слушает порт {0}." -f $Port)
} catch {
  Write-Host ("Запускаю сервер на порту {0} в отдельном окне..." -f $Port)
  Start-Process python -ArgumentList ("backend/server.py --host 0.0.0.0 --port {0}" -f $Port)
  Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "Открываю туннель. Публичный URL — в строке с trycloudflare.com ниже." -ForegroundColor Green
Write-Host "QR для интернета потом: python backend/generate_qr.py --base-url <URL>" -ForegroundColor Yellow
Write-Host "Остановка: Ctrl+C (URL перестанет работать)."
Write-Host ""

& $cf tunnel --url ("http://localhost:{0}" -f $Port)
