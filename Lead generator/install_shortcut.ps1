# Creates a "Synex Lead Engine" shortcut on the Desktop.
# Double-click it to start the engine in the background and open the dashboard.
# If the engine is already running, it just opens the dashboard again.
#
#   powershell -ExecutionPolicy Bypass -File ".\install_shortcut.ps1"                    # desktop shortcut
#   powershell -ExecutionPolicy Bypass -File ".\install_shortcut.ps1" -Autostart         # also start at Windows login
#   powershell -ExecutionPolicy Bypass -File ".\install_shortcut.ps1" -RemoveAutostart   # stop starting at login

param(
    [switch]$Autostart,
    [switch]$RemoveAutostart
)

$root = $PSScriptRoot
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    Write-Error "Virtual environment not found at $pythonw. Create it first (see README)."
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$main = Join-Path $root "main.py"
$icon = (Join-Path $root "assets\synex-leads.ico") + ",0"

function New-EngineShortcut([string]$path, [string]$extraArgs, [string]$description) {
    $link = $shell.CreateShortcut($path)
    $link.TargetPath = $pythonw
    $link.Arguments = "`"$main`" start $extraArgs".Trim()
    $link.WorkingDirectory = $root
    $link.IconLocation = $icon
    $link.Description = $description
    $link.WindowStyle = 7
    $link.Save()
}

$startupPath = Join-Path ([Environment]::GetFolderPath("Startup")) "Synex Lead Engine.lnk"

if ($RemoveAutostart) {
    if (Test-Path $startupPath) { Remove-Item $startupPath -Force; Write-Output "Autostart removed." }
    else { Write-Output "Autostart was not set." }
    exit 0
}

$desktopPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Synex Lead Engine.lnk"
New-EngineShortcut $desktopPath "" "Start the Synex lead engine in the background and open its dashboard"
Write-Output "Shortcut created: $desktopPath"

if ($Autostart) {
    # At login: start quietly in the background, no browser tab
    New-EngineShortcut $startupPath "--no-browser" "Start the Synex lead engine at login (no browser)"
    Write-Output "Autostart enabled: $startupPath"
}
