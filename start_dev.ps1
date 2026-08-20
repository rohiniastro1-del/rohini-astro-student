$ErrorActionPreference = "Stop"

$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimePython = Join-Path $appRoot ".rohini-runtime\Scripts\python.exe"
$appScript = Join-Path $appRoot "app.py"
$pidFile = Join-Path $appRoot ".rohini-dev.pid"
$port = 5051
$url = "http://127.0.0.1:$port/"

Set-Location -LiteralPath $appRoot

function Test-DevHealth {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/__rohini_health" -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
    throw "Липсва средата '.rohini-runtime'. Стартирай основния линк 'Рохини Астро.vbs' веднъж, за да се подготви средата."
}

if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
    try {
        $oldPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
        $oldProcess = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($oldProcess) {
            Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
    }
    catch {
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$env:ROHINI_ASTRO_PORT = "$port"

$serverProcess = Start-Process -FilePath $runtimePython -ArgumentList ('"{0}"' -f $appScript) -WorkingDirectory $appRoot -PassThru -WindowStyle Minimized
Set-Content -LiteralPath $pidFile -Value $serverProcess.Id -Encoding ASCII

$healthy = $false
for ($attempt = 0; $attempt -lt 60; $attempt += 1) {
    Start-Sleep -Milliseconds 500
    if (Test-DevHealth) {
        $healthy = $true
        break
    }
    if ($serverProcess.HasExited) {
        throw "Сървърът спря при стартиране. Виж минимизирания прозорец за грешка."
    }
}
if (-not $healthy) {
    throw "Сървърът не отговори навреме на порт $port."
}

Start-Process -FilePath $url
