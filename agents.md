\# QuakeForge – Agent Guidelines



This file defines the architecture rules and development guidelines for AI agents working on the QuakeForge project.



Agents MUST follow these rules when generating or modifying code.



---



\# Project Overview



QuakeForge is a \*\*Python desktop application\*\* for Quake mod development.



It functions as a \*\*modding workbench\*\* that manages:



\* source assets

\* QuakeC compilation

\* map compilation

\* asset packaging

\* PAK creation

\* deployment to game directories

\* preview of assets



The tool monitors a \*\*source folder (hot path)\*\* and automatically derives build actions from detected changes.



Core philosophy:



Source files → Build artifacts → Final PAK → Deploy



The \*\*source folder is always the ground truth\*\*.



---



\# Core Technologies



Agents MUST use the following technologies unless explicitly instructed otherwise.



Python version:



\* Python 3.11+



GUI:



\* PySide6



Database:



\* SQLite



Filesystem monitoring:



\* watchdog or equivalent



Image loading:



\* Pillow or Qt native image tools



Audio playback:



\* QtMultimedia (preferred)



Archive support:



\* Custom Quake PAK implementation

\* Architecture must allow future PK3 support



---



\# Architecture Rules



\## No Monolithic Scripts



The project MUST remain modular.



Agents MUST NOT create large single-file applications.



All logic should be organized into clear modules.



---



\## Layer Separation



The project should follow this logical separation.



\### App Layer



Application startup and composition.



app/

main.py

bootstrap.py



---



\### Core Layer



Business logic without GUI dependencies.



core/

models/

services/

rules/



Typical services include:



\* ProjectService

\* WatchService

\* ChangeJournalService

\* BuildQueueService

\* TaskResolverService

\* CompilerService

\* PackService

\* DeployService

\* PreviewService

\* SettingsService



---



\### Infrastructure Layer



External integrations.



infrastructure/

db/

filesystem/

process/

archives/



Responsibilities:



\* SQLite persistence

\* filesystem watching

\* hashing

\* external process execution

\* PAK archive reading/writing



---



\### UI Layer



All GUI components.



ui/

main\_window.py

panels/

dialogs/

viewers/

syntax/



The UI MUST NOT contain business logic.



UI components must call services instead.



---



\# Database Rules



SQLite is the central persistence layer.



Each project should use its own database file.



Recommended location:



<project>/.quakeforge/workbench.db



The database stores:



\* project configuration

\* settings

\* toolchains

\* build profiles

\* file change journal

\* build actions

\* logs

\* artifact status



Binary assets MUST NOT be stored in the database.



---



\# Source Folder Philosophy



The source folder is the \*\*hot path\*\*.



Agents MUST treat it as the authoritative state.



Typical structure:



src/

qc/

maps/

textures/

sounds/

music/

shaders/

glsl/



Build artifacts belong in:



build/



Final output:



build/pak0.pak



---



\# File Watching



The application monitors the source directory.



Detected events:



\* create

\* modify

\* delete

\* rename



Agents MUST implement:



\* event debouncing

\* duplicate suppression

\* stable file detection



Watchers MUST ignore:



\* build directories

\* deploy directories

\* temporary folders



---



\# Build Pipeline



File changes produce \*\*Build Actions\*\*.



Examples:



\*.qc → compile\_qc

\*.map → compile\_map

textures → pack\_asset

sounds → pack\_asset

deleted files → remove\_asset



Heavy tasks (map compile) must be controlled.



The system builds a \*\*build queue\*\*, not immediate execution.



---



\# PAK Generation



PAK archives are \*\*final artifacts\*\*.



Agents MUST NOT perform risky in-place modification.



Correct method:



1\. build temporary pak

2\. validate artifacts

3\. atomically replace existing pak



If a build fails:



\* previous artifacts remain active

\* no broken files enter the pak



---



\# Compiler Integration



The tool must support external tools.



\### QuakeC compiler



Examples:



\* fteqcc

\* frikqcc



\### Map tools



\* qbsp

\* vis

\* light



Agents must implement configurable toolchains.



Settings must be stored in SQLite.



---



\# Preview System



The preview panel must support multiple file types.



Agents MUST implement a handler system instead of a giant if/else block.



Minimum handlers:



\* ImagePreviewHandler

\* WavPreviewHandler

\* GlslPreviewHandler

\* TextPreviewHandler

\* FallbackPreviewHandler



Supported previews (V1):



Images:



\* png

\* jpg

\* tga

\* bmp



Audio:



\* wav



Code/Text:



\* qc

\* glsl

\* shader

\* cfg

\* map

\* txt



---



\# GUI Layout



+----------------+---------------------+

| Source Tree    |                     |

|                |                     |

|----------------|  Preview Panel     |

| Build / PAK    |                     |

| Tree           |                     |

+--------------------------------------+

| Logs | Changes | Build Queue | Errors|

+--------------------------------------+



---



\# Settings System



A settings dialog must exist.



Sections:



Project:



\* source root

\* build root

\* deploy root

\* pak output



Toolchains:



\* qc compiler

\* qbsp

\* vis

\* light

\* game executable



Build:



\* auto watch

\* auto flush interval

\* pack after build

\* deploy after build



---



\# JSON Import / Export



Although SQLite is the primary storage, the tool must support:



\* JSON export of project settings

\* JSON import of project configurations



Purpose:



portability and reproducibility.



---



\# Performance Rules



Agents MUST avoid:



\* blocking GUI threads

\* synchronous heavy builds in UI thread

\* uncontrolled rebuild loops



Long tasks should run in worker threads.



---



\# Error Handling



Failures must:



\* be logged

\* appear in the error panel

\* not corrupt the build state



Broken builds must never replace valid artifacts.



---



\# V1 Scope Limitations



Agents MUST NOT implement in V1:



\* plugin systems

\* complex dependency graphs

\* multi-PAK overlay simulation

\* full shader parsing AST

\* asset diff tools

\* advanced undo/redo systems



The architecture must allow these later.



---



\# Code Quality



Agents must generate code that is:



\* readable

\* documented where necessary

\* structured

\* consistent with Python conventions



Prefer maintainability over clever tricks.



---



\# Documentation



Agents must update README when major features are added.



README should include:



\* architecture overview

\* dependencies

\* setup instructions

\* toolchain configuration

\* project folder structure



---



\# Final Rule



When in doubt:



Prefer \*\*safe, modular, and maintainable solutions\*\*

over shortcuts or fragile hacks.



