@echo off
setlocal

REM QuakeForge Workbench EXE Build Script (Windows)
REM Usage: run in repo root with active Python environment.

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [INFO] PyInstaller nicht gefunden. Installiere pyinstaller...
  python -m pip install pyinstaller
  if errorlevel 1 (
    echo [ERROR] Konnte pyinstaller nicht installieren.
    exit /b 1
  )
)

echo [INFO] Erzeuge EXE mit PyInstaller...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name QuakeForgeWorkbench ^
  app/main.py

if errorlevel 1 (
  echo [ERROR] Build fehlgeschlagen.
  exit /b 1
)

echo [OK] Build erfolgreich.
echo [OK] EXE: dist\QuakeForgeWorkbench\QuakeForgeWorkbench.exe

endlocal
