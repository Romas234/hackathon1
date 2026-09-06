<# Этап 5 (задача 5.2): запуск квеста в локальной сети одной командой.
   Определяет LAN-IP машины, показывает URL для QR/телефонов и стартует сервер.

   Использование:
     powershell -ExecutionPolicy Bypass -File .\start-lan.ps1
     powershell -ExecutionPolicy Bypass -File .\start-lan.ps1 -Port 8000
#>
param([int]$Port = 8000)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$ip = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1 -ExpandProperty IPAddress

if (-not $ip) { $ip = "127.0.0.1" }

Write-Host ""
Write-Host "  Квест по кампусу УрФУ — запуск в локальной сети" -ForegroundColor Green
Write-Host ("  Локально:   http://localhost:{0}/location/1" -f $Port)
Write-Host ("  По сети:    http://{0}:{1}/location/1" -f $ip, $Port) -ForegroundColor Yellow
Write-Host ("  QR-коды:    python backend/generate_qr.py --host {0} --port {1}" -f $ip, $Port)
Write-Host "  Остановка:  Ctrl+C"
Write-Host ""

& python "backend/server.py" --host 0.0.0.0 --port $Port
