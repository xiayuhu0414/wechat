$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$env:Path = "C:\Program Files\nodejs;$env:Path"

Write-Host "Installing Python dependencies..."
python -m pip install -r requirements.txt
python -m pip install pyinstaller

Write-Host "Building frontend..."
Push-Location frontend
& "C:\Program Files\nodejs\npm.cmd" install
& "C:\Program Files\nodejs\npm.cmd" run build
Pop-Location

Write-Host "Building Windows app..."
python -m PyInstaller packaging\autoWechatConsole.spec --clean --noconfirm

Write-Host ""
Write-Host "Done: $Root\dist\autoWechat Console\autoWechat Console.exe"

