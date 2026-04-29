@echo off
chcp 65001 > nul
echo ============================================
echo  RadioDesk - Build script
echo ============================================

cd /d "%~dp0"

:: --- 1. Generate icon ---
echo.
echo [1/3] Generation de l'icone...
python setup\make_icon.py
if errorlevel 1 (
    echo ERREUR: generation icone echouee
    pause & exit /b 1
)

:: --- 2. PyInstaller ---
echo.
echo [2/3] Compilation avec PyInstaller...
pyinstaller setup\radiodesk.spec --clean --noconfirm
if errorlevel 1 (
    echo ERREUR: PyInstaller a echoue
    pause & exit /b 1
)

echo.
echo [2/3] OK - dist\RadioDesk.exe genere

:: --- 3. Inno Setup (optionnel) ---
echo.
echo [3/3] Creation de l'installateur...

set ISCC_PATH=
for %%p in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) do (
    if exist %%p set ISCC_PATH=%%p
)

if defined ISCC_PATH (
    mkdir release 2>nul
    %ISCC_PATH% setup\radiodesk.iss
    if errorlevel 1 (
        echo ERREUR: Inno Setup a echoue
    ) else (
        echo OK - release\RadioDesk-Setup-1.0.0.exe genere
    )
) else (
    echo Inno Setup non installe - etape ignoree.
    echo Pour creer un installateur :
    echo   1. Telechargez Inno Setup sur https://jrsoftware.org/isdl.php
    echo   2. Relancez ce script
    echo.
    echo L'executable seul est disponible dans : dist\RadioDesk.exe
)

echo.
echo ============================================
echo  Build termine !
echo ============================================
if exist "dist\RadioDesk.exe" (
    echo  Executable : dist\RadioDesk.exe
)
if exist "release\RadioDesk-Setup-1.0.0.exe" (
    echo  Installateur : release\RadioDesk-Setup-1.0.0.exe
)
echo ============================================
pause
