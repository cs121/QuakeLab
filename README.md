# QuakeLab Workbench V1

QuakeLab ist eine modulare Python-Desktop-Anwendung (PySide6) für Quake-Modding-Workflows mit Source-Watching, Change-Journal, Build-Queue, Toolchain-Integration und PAK-Rebuild.

## Voraussetzungen

- Python **3.11+**
- Betriebssystem: Linux, macOS oder Windows
- Für EXE-Build: Windows + PyInstaller

## Benötigte Python-Libraries

Pflichtabhängigkeiten:

- `PySide6` (GUI, Multimedia, Datei-Modelle)

Für Entwicklung und Tests empfohlen:

- `pytest`
- `pyinstaller` (nur für EXE-Erzeugung)

Installation (Beispiel mit virtueller Umgebung):

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install PySide6 pytest pyinstaller
```

## Anwendung starten

Projektwurzel öffnen und starten:

```bash
python -m app.main
```

Beim ersten Start werden automatisch Standardordner (`src`, `build`) und die SQLite-Datenbank unter `.quakelab/quakelab.db` angelegt.

## Bedienung (Kurz-Anleitung)

1. **Starten** mit `python -m app.main`.
2. Über **Project → Settings** die Pfade setzen:
   - Source Root
   - Build Root
   - Deploy Root
   - Pak Output
3. In **Project → Settings** die Toolchain konfigurieren:
   - QC Compiler (Executable + optionale Argumente)
   - QBSP / VIS / LIGHT (optional)
4. Dateien im `src/`-Ordner bearbeiten/ablegen.
5. Das Tool erkennt Änderungen automatisch und legt Build-Aktionen in der Queue an.
6. Unten rechts **Flush Build Queue** klicken (oder Auto-Flush nutzen), um die Aktionen abzuarbeiten.
7. Ergebnisse prüfen:
   - **Build Queue**-Tab für Status
   - **Logs**-Tab für Ausgaben
   - **Errors**-Tab bei Fehlern
   - **Preview** rechts für selektierte Dateien

## EXE erstellen (Windows)

Im Hauptordner liegt das Script `build_exe.bat`.

Ausführen in einer aktiven Python-Umgebung:

```bat
build_exe.bat
```

Ergebnis:

- EXE-Datei unter `dist\`
- Startdatei: `dist\QuakeLab.exe`

## Features (V1)

- Modulares GUI-Layout mit:
  - Source Tree (links oben)
  - Build/PAK Tree (links unten)
  - Preview-Bereich (rechts)
  - Tabs: Change Journal, Build Queue, Logs, Errors (unten)
- Source-Hot-Path Monitoring mit Debounce und Deduplizierung.
- Persistenter Change-Journal und Build-Queue in SQLite (`.quakelab/quakelab.db`).
- Regelbasierte Build-Aktionen (`compile_qc`, `compile_map`, `pack_asset`, `remove_asset`, `rebuild_pak`).
- QuakeC-/Map-Toolchain-Integration via konfigurierbare externe Prozesse.
- Periodischer oder manueller Queue-Flush inkl. atomischem PAK-Rebuild.
- Preview-Handler-System:
  - Bilder (`png/jpg/jpeg/tga/bmp`)
  - WAV inkl. Play/Stop und Metadaten
  - GLSL mit Syntax-Highlighting
  - Allgemeine Textformate
  - Fallback-Viewer
- JSON Export/Import für Settings.

## Architekturüberblick

```text
app/
  main.py
  bootstrap.py
core/
  models/
  rules/
  services/
infrastructure/
  archives/
  db/
  filesystem/
  process/
ui/
  dialogs/
  viewers/
  syntax/
  main_window.py
examples/
  project_config.example.json
tests/
```

### Schichten

- **App-Layer**: Bootstrap, Dependency-Wiring, App-Start.
- **Core-Layer**: Domänenmodelle, Regeln, Services ohne GUI-Logik.
- **Infrastructure-Layer**: SQLite, Watcher, Hashing, Prozessausführung, PAK-Implementierung.
- **UI-Layer**: MainWindow, Dialoge, Preview-Widgets.

## Typische Projektstruktur

```text
src/
  qc/
  maps/
  textures/
  sounds/
  music/
  shaders/
  glsl/
build/
  pak0.pak
```

## JSON Import/Export

Im Settings-Dialog:

- `Export JSON`: schreibt portable Konfiguration.
- `Import JSON`: lädt Konfiguration wieder ein.

Beispiel: `examples/project_config.example.json`

## Hinweise zu V1-Scope

Nicht enthalten in V1:

- Plugin-System
- Multi-PAK Overlay
- Erweiterte Dependency-Engine
- Vollständige Diff-/Undo-Pipelines

Die Architektur ist dafür vorbereitet (Handler-/Service-basierter Schnitt).
