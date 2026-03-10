# QuakeForge Workbench V1

QuakeForge ist eine modulare Python-Desktop-Anwendung (PySide6) für Quake-Modding-Workflows mit Source-Watching, Change-Journal, Build-Queue, Toolchain-Integration und PAK-Rebuild.

## Features (V1)

- Modulares GUI-Layout mit:
  - Source Tree (links oben)
  - Build/PAK Tree (links unten)
  - Preview-Bereich (rechts)
  - Tabs: Change Journal, Build Queue, Logs, Errors (unten)
- Source-Hot-Path Monitoring mit Debounce und Deduplizierung.
- Persistenter Change-Journal und Build-Queue in SQLite (`.quakeforge/workbench.db`).
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

## Installation

Voraussetzungen:

- Python 3.11+
- PySide6

Installation:

```bash
python -m venv .venv
source .venv/bin/activate
pip install PySide6
```

## Start

```bash
python -m app.main
```

Beim ersten Start werden Default-Ordner (`src`, `build`) und `.quakeforge/workbench.db` initialisiert.

## Toolchain-Setup

`Project -> Settings` öffnen und eintragen:

- QC Compiler: Executable + Args
- QBSP/VIS/LIGHT: Executables (+ optional Args)
- Pfade: Source/Build/Deploy/Pak
- Build-Modus: `fast`, `full`, `manual`

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
