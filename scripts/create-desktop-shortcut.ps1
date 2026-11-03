# Create a Windows desktop shortcut that starts the dashboard in WSL.
# Run from Windows PowerShell:
#   powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu\home\<user>\<repo>\scripts\create-desktop-shortcut.ps1
# Keep this file ASCII-only: Windows PowerShell 5.1 misreads UTF-8 without BOM.
param(
    [string]$Name = "DIV Dashboard"
)

$ErrorActionPreference = "Stop"

$repoWinPath = Split-Path -Parent $PSScriptRoot
if ($repoWinPath -notmatch '^\\\\wsl(?:\.localhost|\$)\\([^\\]+)(\\.*)$') {
    throw "Run this script from a WSL path (\\wsl.localhost\<distro>\...). Current: $repoWinPath"
}
$distro = $Matches[1]
$repoLinuxPath = $Matches[2] -replace '\\', '/'

$wsl = Join-Path $env:SystemRoot "System32\wsl.exe"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "$Name.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $wsl
$shortcut.Arguments = "-d $distro --cd `"$repoLinuxPath`" -- bash scripts/run-desktop.sh"
$shortcut.WorkingDirectory = $env:USERPROFILE
$shortcut.IconLocation = "$wsl,0"
$shortcut.Description = "Start Docker services, DB migrations, and the FastAPI dashboard"
$shortcut.Save()

Write-Output "Created: $shortcutPath"
Write-Output "Target:  $wsl $($shortcut.Arguments)"
