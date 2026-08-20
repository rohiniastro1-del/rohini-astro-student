$ErrorActionPreference = "Stop"

$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeRoot = Join-Path $appRoot ".rohini-runtime"
$runtimePython = Join-Path $runtimeRoot "Scripts\python.exe"
$runtimePythonWindowed = Join-Path $runtimeRoot "Scripts\pythonw.exe"
$readyMarker = Join-Path $runtimeRoot ".rohini-ready"
$requirementsPath = Join-Path $appRoot "requirements.txt"
$desktopScript = Join-Path $appRoot "desktop_app.py"
$crashLog = Join-Path $appRoot ".rohini-desktop.crash.log"
$statePath = Join-Path $appRoot ".rohini-desktop.state.json"

Set-Location -LiteralPath $appRoot

$trackedFiles = @(
    Get-Item -LiteralPath (Join-Path $appRoot "app.py"), (Join-Path $appRoot "desktop_app.py"), (Join-Path $appRoot "requirements.txt")
    Get-ChildItem -LiteralPath (Join-Path $appRoot "templates") -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $appRoot "static") -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $appRoot "vedic_app") -Recurse -File |
        Where-Object { $_.FullName -notlike "*\__pycache__\*" -and $_.Extension -in @(".py", ".json") }
)
$latestSourceChange = ($trackedFiles | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1).LastWriteTimeUtc

function Get-RohiniState {
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        return $null
    }
    try {
        $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($state.app_root -ne $appRoot -or [int]$state.pid -le 0 -or [int]$state.port -le 0) {
            return $null
        }
        return $state
    }
    catch {
        return $null
    }
}

function Test-RohiniHealth($state) {
    try {
        $response = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/__rohini_health" -f $state.port) -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Open-RohiniWindow($state) {
    $url = "http://127.0.0.1:{0}/" -f $state.port
    Start-Process -FilePath "explorer.exe" -ArgumentList ("microsoft-edge:{0}" -f $url)
}

$existingState = Get-RohiniState
if ($existingState) {
    $existingProcess = Get-Process -Id ([int]$existingState.pid) -ErrorAction SilentlyContinue
    $runningVersionIsCurrent = $existingProcess -and $existingProcess.StartTime.ToUniversalTime() -ge $latestSourceChange
    if ($runningVersionIsCurrent -and (Test-RohiniHealth $existingState)) {
        Open-RohiniWindow $existingState
        exit 0
    }

    if ($existingProcess) {
        Stop-Process -Id $existingProcess.Id -Force
        $existingProcess.WaitForExit(5000) | Out-Null
    }
    if ([int]$existingState.server_pid -gt 0) {
        $existingServer = Get-Process -Id ([int]$existingState.server_pid) -ErrorAction SilentlyContinue
        if ($existingServer) {
            Stop-Process -Id $existingServer.Id -Force
            $existingServer.WaitForExit(5000) | Out-Null
        }
    }
    Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}

function Show-StartError([string]$message) {
    try {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($message, "Рохини Астро", "OK", "Error") | Out-Null
    }
    catch {
    }
}

try {
    if (-not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $pythonCommand) {
            throw "Не е намерен Python 3.11."
        }
        & $pythonCommand.Source -m venv $runtimeRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Не успях да подготвя личната среда на програмата."
        }
    }

    $requirementsHash = (Get-FileHash -LiteralPath $requirementsPath -Algorithm SHA256).Hash
    $savedHash = if (Test-Path -LiteralPath $readyMarker) { (Get-Content -LiteralPath $readyMarker -Raw).Trim() } else { "" }
    if ($savedHash -ne $requirementsHash) {
        & $runtimePython -m pip install --disable-pip-version-check --requirement $requirementsPath
        if ($LASTEXITCODE -ne 0) {
            throw "Необходимите компоненти не се инсталираха. Провери интернет връзката и опитай отново."
        }
        Set-Content -LiteralPath $readyMarker -Value $requirementsHash -Encoding ASCII
    }

    if (-not (Test-Path -LiteralPath $runtimePythonWindowed -PathType Leaf)) {
        throw "Липсва компонентът за безшумно стартиране."
    }

    Start-Process -FilePath $runtimePythonWindowed -ArgumentList ('"{0}"' -f $desktopScript) -WorkingDirectory $appRoot

    $healthy = $false
    for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
        Start-Sleep -Milliseconds 250
        $startedState = Get-RohiniState
        if ($startedState -and (Test-RohiniHealth $startedState)) {
            $healthy = $true
            break
        }
    }
    if (-not $healthy) {
        throw "Локалният модул не отговори навреме. Натисни иконата още веднъж."
    }
    Open-RohiniWindow $startedState
    exit 0
}
catch {
    $message = "Рохини Астро не успя да стартира.`n`n$($_.Exception.Message)"
    Set-Content -LiteralPath $crashLog -Value ($_ | Out-String) -Encoding UTF8
    Show-StartError $message
    exit 1
}
