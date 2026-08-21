$ErrorActionPreference = "Stop"

$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeRoot = Join-Path $appRoot ".rohini-runtime"
$runtimePython = Join-Path $runtimeRoot "Scripts\python.exe"
$runtimePythonWindowed = Join-Path $runtimeRoot "Scripts\pythonw.exe"
$readyMarker = Join-Path $runtimeRoot ".rohini-ready"
$requirementsPath = Join-Path $appRoot "requirements.txt"
$nativeScript = Join-Path $appRoot "native_window.py"
$crashLog = Join-Path $appRoot ".rohini-student-start.log"

Set-Location -LiteralPath $appRoot

function Show-StartError([string]$message) {
    try {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($message, "Рохини Астро Студент", "OK", "Error") | Out-Null
    }
    catch {
    }
}

function Get-Sha256([string]$path) {
    $stream = [System.IO.File]::OpenRead($path)
    try {
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hashBytes = $sha256.ComputeHash($stream)
            return ([System.BitConverter]::ToString($hashBytes)).Replace("-", "")
        }
        finally {
            $sha256.Dispose()
        }
    }
    finally {
        $stream.Dispose()
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

    $requirementsHash = Get-Sha256 $requirementsPath
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

    Start-Process -FilePath $runtimePythonWindowed -ArgumentList ('"{0}"' -f $nativeScript) -WorkingDirectory $appRoot
    exit 0
}
catch {
    $message = "Рохини Астро Студент не успя да стартира.`n`n$($_.Exception.Message)"
    Set-Content -LiteralPath $crashLog -Value ($_ | Out-String) -Encoding UTF8
    Show-StartError $message
    exit 1
}
