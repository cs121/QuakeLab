# QuakeLab Workbench

A modular Python desktop application (PySide6) for Quake modding workflows — source watching, change journal, build queue, full toolchain integration, PAK rebuild, and rich asset previews.

---

## Requirements

- Python **3.11+**
- OS: Linux, macOS, or Windows
- For EXE packaging: Windows + PyInstaller

## Installation

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install PySide6
# optional: pip install pytest pyinstaller
```

## Running

```bash
python -m app.main
```

On first launch, QuakeLab automatically creates the default folders (`src/`, `build/`) and the SQLite database at `.quakelab/quakelab.db`.

---

## Quick-Start

1. **Launch** `python -m app.main`.
2. Open **Project → Settings** and configure paths:
   - Source Root, Build Root, Deploy Root, PAK Output
   - Engine executable
3. In **Settings → Toolchains** set up the compiler paths:
   - QC Compiler, QBSP, VIS, LIGHT, TrenchBroom
4. Drop / edit files in the `src/` folder.
5. QuakeLab detects changes and enqueues build actions automatically.
6. Click **Flush Build Queue** (status bar) or let Auto-Flush fire periodically.
7. Check results in the bottom tabs: Change Journal · Build Queue · Build Output · Logs · Errors.

---

## Features

### File Browser & Editor
- **Source Tree** (left panel) — full file system view of the source root with drag-and-drop support.
- **Editable preview** — clicking any text-format file (`.qc`, `.map`, `.cfg`, `.shader`, `.md`, `.ent`, …) opens it in an inline editor with a **Save** button and unsaved-changes indicator.
- **QuakeC syntax highlighting** — `.qc` / `.qh` files get full syntax colouring: types, control flow, built-in functions, string literals, numbers, single- and block-comments, preprocessor directives.
- **GLSL syntax highlighting** — `.glsl` / `.vert` / `.frag` files.

### Context Menus
Right-click any file or folder in the Source Tree:

| Context | Actions |
|---------|---------|
| `.map` file | Open in TrenchBroom · Compile Map · Rename · Delete |
| Any file | Rename · Delete |
| Folder | New File/Folder · Rename · Delete |
| Empty space | New File/Folder |

### TrenchBroom Integration
- **Double-click** a `.map` file to open it in TrenchBroom.
- Configure the TrenchBroom executable in **Settings → Toolchains → TrenchBroom**.

### Build Templates
Five preset compilation profiles selectable from **Build → Build Template** or **Settings → Build Templates**:

| Template | Pipeline | Use case |
|----------|----------|----------|
| **preview** | QBSP only | Instant preview, no lighting |
| **fast** | QBSP + VIS `-fast` | Quick iteration |
| **normal** | QBSP + VIS + LIGHT | Standard release quality |
| **high** | QBSP + VIS `-level 4` + LIGHT `-extra4 -soft` | Final high-quality build |
| **custom** | Configurable args | Full control |

### Asset Previews

| Extension | Viewer |
|-----------|--------|
| `.bsp` | Summary, Entities, Textures tabs |
| `.wad` (WAD2/WAD3) | Directory listing + per-texture MIPTEX/QPic preview |
| `.mdl` (IDPO v6) | Metadata summary + first skin texture |
| `.spr` (IDSP v1) | Metadata summary + frame-by-frame preview |
| `.lmp` | Palette-indexed image; 768-byte files show 256-colour swatch grid |
| `.dem` | Demo format detection + message block statistics |
| `.png` `.jpg` `.tga` `.bmp` | Scrollable image with dimensions |
| `.wav` | Audio player (play/stop) + metadata |
| `.glsl` `.vert` `.frag` | Syntax-highlighted read view |
| `.qc` `.qh` `.map` `.cfg` `.shader` `.md` `.ent` `.txt` | Editable text with syntax highlighting |
| Everything else | Hex/text fallback |

All palette-indexed formats (WAD, MDL, SPR, LMP) automatically load `gfx/palette.lmp` from your source root for accurate Quake colours, falling back to a built-in colour cube.

### Automatic Tool Download
**Settings → Toolchains → Download Tools…** downloads and installs tools directly into the `toolchain/` folder and auto-configures all settings paths:

- **ericw-tools** — QBSP / VIS / LIGHT (fetches latest GitHub release)
- **TrenchBroom** — map editor (fetches latest GitHub release)

An *Install from Archive* option accepts a locally downloaded zip/tar.gz.

### QuakeC Source Code
**Project → QuakeC Source…** downloads QuakeC source code into your source root:

| Source | Description |
|--------|-------------|
| **id Software Quake QC** | Original GPL progs source (id-Software/Quake on GitHub) |
| **Copper QC** | Modern vanilla-compatible mod base by Lunaran |
| **Quake Remastered QC** | Community adaptation for the 2021 Nightdive remaster |

Each entry shows a progress bar, extracts `.qc` files into a named subfolder, and has an in-app README viewer.

### Build Pipeline
- **Source watching** — background polling with SHA1-based change detection and 0.7 s debounce.
- **Change Journal** — every detected file change is logged to SQLite.
- **Build Queue** — rule-based action resolver maps file changes to `compile_qc`, `compile_map`, `pack_asset`, `remove_asset`, `rebuild_pak`.
- **Streaming output** — live QBSP/VIS/LIGHT output appears line-by-line in the Build Output tab.
- **Compiler diagnostics** — errors parsed from build output; double-click an error to jump to the line in the editor.
- **PAK rebuild** — atomic write-then-swap ensures the output PAK is never left in a partial state.
- **Auto-flush** — configurable timer fires the build queue periodically (default 3 min).
- **Deploy** — optional post-build copy of the PAK to a game directory.

### Project Panel (Build/PAK Tree)
Displays the contents of the output PAK file in a hierarchical tree, auto-refreshed whenever the PAK changes.

### Settings
- Import / Export all settings as JSON.
- Per-tool live validation indicators (green OK / red ✗).
- Reset workspace — rebuilds the database and cleans src/build/deploy.

---

## Architecture

```
app/                    Bootstrap, dependency wiring, entry point
core/
  models/               Domain dataclasses (BuildAction, BuildTemplate, …)
  rules/                Build-action resolution rules
  services/             Business logic (no GUI imports):
                          compiler, pack, deploy, launch, rebuild,
                          preview, settings, log, build-queue,
                          change-journal, tool-download, validation
infrastructure/
  archives/pak.py       Quake PAK read/write
  db/database.py        SQLite (settings, journal, queue, logs)
  filesystem/watcher.py Polling file watcher
  formats/
    bsp.py              BSP lump parser
    wad.py              WAD2/WAD3 parser
    mdl.py              MDL (IDPO v6) parser
    spr.py              SPR (IDSP v1) parser
    palette.py          Shared palette loader
  process/              Blocking + streaming subprocess runners
ui/
  dialogs/              Settings, tool download, QC source download
  panels/               Source tree view (drag-drop, context menu)
  syntax/               QcHighlighter, GlslHighlighter
  viewers/              BSP, WAD, MDL, SPR, LMP, DEM, image, WAV,
                        text (editable), GLSL, fallback
  main_window.py        Main window, layout, signal wiring
tests/
```

### Layer rules
- **Core** and **Infrastructure** have zero Qt/GUI imports — fully testable in isolation.
- **UI** layer wires everything together via signals and service calls.
- All services are injected via `app/bootstrap.py`.

---

## Typical Source Layout

```
src/
  qc/           QuakeC source (.qc, .qh)
  maps/         Map files (.map)
  textures/     WAD files, LMP textures
  sounds/       WAV files
  models/       MDL models, SPR sprites
  gfx/          palette.lmp, status-bar graphics
  music/
build/
  pak0.pak
toolchain/
  ericw-tools/  qbsp, vis, light
  trenchbroom/  TrenchBroom
```

---

## Windows EXE

```bat
build_exe.bat
```

Output: `dist\QuakeLab.exe`

---

## Roadmap

- Plugin / extension system
- Multi-PAK overlay support
- Full dependency graph (incremental rebuilds)
- MDL / SPR frame animation playback
- Quake palette editor
