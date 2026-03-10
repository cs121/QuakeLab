@echo off
setlocal

REM QuakeLab EXE Build Script (Windows)
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

echo [INFO] Erzeuge eigenstaendige EXE mit PyInstaller (--onefile)...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onefile ^
  --name QuakeLab ^
  --collect-all PySide6 ^
  app/main.py

if errorlevel 1 (
  echo [ERROR] Build fehlgeschlagen.
  exit /b 1
)

echo [OK] Build erfolgreich.
echo [OK] EXE: dist\QuakeLab.exe

endlocal
