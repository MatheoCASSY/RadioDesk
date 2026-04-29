# RadioDesk - Self-contained installer creator (no Inno Setup needed)
# Creates a self-extracting archive that installs RadioDesk on Windows
#
# Usage: powershell -ExecutionPolicy Bypass -File setup\create_installer.ps1

param(
    [string]$Version = "1.0.0",
    [string]$ExePath = "dist\RadioDesk.exe",
    [string]$OutDir  = "release"
)

Set-Location $PSScriptRoot\..

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " RadioDesk $Version - Installer Creator" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check source exe exists
if (-not (Test-Path $ExePath)) {
    Write-Host "ERREUR: $ExePath introuvable. Lancez build.bat d'abord." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$installerPath = "$OutDir\RadioDesk-Setup-$Version.exe"

# ── Read the exe as bytes ────────────────────────────────────────────────────
Write-Host "`n[1/2] Lecture de RadioDesk.exe..."
$exeBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $ExePath))
$exeBase64 = [Convert]::ToBase64String($exeBytes)
Write-Host "      Taille: $([math]::Round($exeBytes.Length/1MB, 1)) MB"

# ── Create self-extracting PowerShell EXE via ps2exe (if available) ──────────
# We'll create a launcher script that uses the sfx approach with a simple zip
Write-Host "`n[2/2] Creation de l'installateur..."

# Compress exe to zip first
$zipPath = "$OutDir\RadioDesk.zip"
Compress-Archive -Path $ExePath -DestinationPath $zipPath -Force

# Create the installer script
$installerScript = @'
# RadioDesk Installer
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName PresentationFramework

$appName    = "RadioDesk"
$appVersion = "VERSION_PLACEHOLDER"
$installDir = "$env:LOCALAPPDATA\RadioDesk"

# ── Welcome dialog ─────────────────────────────────────────────────────────
$result = [System.Windows.Forms.MessageBox]::Show(
    "Bienvenue dans l'installation de RadioDesk $appVersion`n`nL'application sera installee dans :`n$installDir`n`nContinuer ?",
    "Installation de RadioDesk",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Information
)
if ($result -ne [System.Windows.Forms.DialogResult]::Yes) { exit 0 }

# ── Extract ────────────────────────────────────────────────────────────────
try {
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null

    # Extract zip next to this script
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $zipFile   = Join-Path $scriptDir "RadioDesk.zip"

    Expand-Archive -Path $zipFile -DestinationPath $installDir -Force

    # ── Start menu shortcut ─────────────────────────────────────────────────
    $startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RadioDesk"
    New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut("$startMenu\RadioDesk.lnk")
    $shortcut.TargetPath = "$installDir\RadioDesk.exe"
    $shortcut.WorkingDirectory = $installDir
    $shortcut.Description = "RadioDesk - Admin Panel FluffRadio"
    $shortcut.Save()

    # ── Desktop shortcut ────────────────────────────────────────────────────
    $desktop  = [Environment]::GetFolderPath("Desktop")
    $shortcut2 = $WshShell.CreateShortcut("$desktop\RadioDesk.lnk")
    $shortcut2.TargetPath = "$installDir\RadioDesk.exe"
    $shortcut2.WorkingDirectory = $installDir
    $shortcut2.Save()

    # ── Uninstall script ────────────────────────────────────────────────────
    $uninstall = @"
Remove-Item -Recurse -Force "$installDir" -ErrorAction SilentlyContinue
Remove-Item -Force "$startMenu\RadioDesk.lnk" -ErrorAction SilentlyContinue
Remove-Item -Force "$desktop\RadioDesk.lnk"   -ErrorAction SilentlyContinue
Remove-Item -Force "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RadioDesk\RadioDesk.lnk" -ErrorAction SilentlyContinue
[System.Windows.Forms.MessageBox]::Show("RadioDesk a ete desinstalle.", "Desinstallation", 0, 64) | Out-Null
"@
    $uninstall | Set-Content "$installDir\Uninstall.ps1" -Encoding UTF8

    $WshShell2 = New-Object -ComObject WScript.Shell
    $unShortcut = $WshShell2.CreateShortcut("$startMenu\Desinstaller RadioDesk.lnk")
    $unShortcut.TargetPath  = "powershell.exe"
    $unShortcut.Arguments   = "-ExecutionPolicy Bypass -File `"$installDir\Uninstall.ps1`""
    $unShortcut.Description = "Desinstaller RadioDesk"
    $unShortcut.Save()

    [System.Windows.Forms.MessageBox]::Show(
        "RadioDesk $appVersion installe avec succes !`n`nDemarrez l'application depuis le Bureau ou le menu Demarrer.",
        "Installation reussie",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null

    # Launch the app
    Start-Process "$installDir\RadioDesk.exe"

} catch {
    [System.Windows.Forms.MessageBox]::Show(
        "Erreur lors de l'installation :`n$_",
        "Erreur",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 1
}
'@

$installerScript = $installerScript.Replace("VERSION_PLACEHOLDER", $Version)
$installerScript | Set-Content "$OutDir\Install-RadioDesk.ps1" -Encoding UTF8

# ── Create a simple batch launcher for the installer ────────────────────────
$batchContent = @"
@echo off
echo Installation de RadioDesk $Version...
powershell -ExecutionPolicy Bypass -File "%~dp0Install-RadioDesk.ps1"
"@
$batchContent | Set-Content "$OutDir\RadioDesk-Setup-$Version.bat" -Encoding ASCII

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Installateur cree !" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host " release\" -ForegroundColor White
Write-Host "   RadioDesk.zip                   <- application compressee" -ForegroundColor Gray
Write-Host "   Install-RadioDesk.ps1           <- script d'installation" -ForegroundColor Gray
Write-Host "   RadioDesk-Setup-$Version.bat   <- lanceur (double-clic)" -ForegroundColor Yellow
Write-Host ""
Write-Host " Pour distribuer : copiez le dossier release\ entier." -ForegroundColor Cyan
Write-Host " L'utilisateur double-clique sur RadioDesk-Setup-$Version.bat" -ForegroundColor Cyan
Write-Host ""

# Also try ps2exe if available for a true .exe installer
$ps2exe = Get-Command "ps2exe" -ErrorAction SilentlyContinue
if ($ps2exe) {
    Write-Host "[BONUS] ps2exe detecte - generation de l'exe installateur..." -ForegroundColor Magenta
    ps2exe "$OutDir\Install-RadioDesk.ps1" "$OutDir\RadioDesk-Setup-$Version.exe" `
        -title "RadioDesk Installer" -description "RadioDesk $Version Installer" `
        -noConsole -requireAdmin
    Write-Host "  RadioDesk-Setup-$Version.exe genere !" -ForegroundColor Green
}
