# Eit Modernization Plan

## Game Overview

Eit ("Eittris") is a **Tetris clone with up to 4-player head-to-head combat** and 22 special
power-up blocks (Blind, Clear, Rumble, Inverse, Fill, etc.). Copyright 2006-2023 by Victor
Blomqvist, GPL licensed. It uses **pygame + PyOpenGL** for rendering and **PGU** (Phil's pyGame
Utilities) for the menu/dialog system.

## Architecture

| File               | Lines | Role                                                    |
| ------------------ | ----- | ------------------------------------------------------- |
| `eit.py`           | 603   | Entry point (`Main` class), game loop, menu, Scoretable |
| `blocks.py`        | 381   | Block shapes (I/T/O/L/J/S/Z) and 22 special block types|
| `blockfield.py`    | 344   | 10x23 playing field grid, line clearing, effects        |
| `playerfield.py`   | 821   | Player logic, controls, scoring, OpenGL drawing         |
| `datamanager.py`   | 127   | Asset loading (textures, sounds, music)                 |
| `dialogs.py`       | 535   | GUI dialogs (profiles, help, scores) via PGU            |
| `eit_constants.py` | 13    | Game timing/level constants                             |
| `setup.py`         | 62    | py2exe packaging script (obsolete)                      |

**Entry point:** `eit.py` -> `run_game()` -> `Main().main()`

## Dependencies

- **pygame** - display, sound, input
- **PyOpenGL** (GL, GLU, GLUT) - all rendering
- **PGU** v0.10.3 - bundled in `_pgu/` (partially ported to Python 3)
- **configobj** - config file handling (imported but not present in working dir)

## Issues Found

### Critical Python 2 Leftovers (will crash on Python 3)

| Issue                                     | Locations                                    |
| ----------------------------------------- | -------------------------------------------- |
| `dict.has_key()` (removed in Py3)         | `eit.py:71,93`, `dialogs.py:156,171`         |
| `dict.iteritems()` (removed in Py3)       | `playerfield.py:676`                         |
| `dict.keys().sort()` (views not sortable) | `dialogs.py:94,147,187,202,351,382`          |
| `pickle.load` with text mode `"r"`        | `eit.py:122` (needs `"rb"`)                  |
| Print statement (not function)            | `setup.py:28`                                |

### Code Quality Issues

| Issue                                        | Locations                                                                  |
| -------------------------------------------- | -------------------------------------------------------------------------- |
| Old-style classes (no `object` base)         | `blocks.py:8,70,270`, `blockfield.py:19`, `playerfield.py:24`, `eit.py:54`, `datamanager.py:11` |
| Bare `except:` clauses                       | `eit.py:124`, `blockfield.py:252,340`, `playerfield.py:586`, `datamanager.py:115,125`, `dialogs.py:130,197` |
| Wildcard `from X import *` everywhere        | `eit.py`, `blockfield.py`, `playerfield.py`, `datamanager.py`             |
| `glutBitmapCharacter` overridden to no-op    | `playerfield.py:21-22`                                                    |
| Unused `import operator`                     | `eit.py:51`                                                               |
| Tabs used for indentation (not PEP 8)        | `blocks.py` and others                                                    |

### Structural Issues

- No tests at all
- No `pyproject.toml` or modern packaging -- only an obsolete `setup.py` for py2exe
- `configobj` dependency missing from working directory (only in `_darcs/` and `dist/`)
- Large duplicate directories: `_darcs/current/`, `dist/`, `backup/` contain full or partial copies
- Bundled PGU library in `_pgu/` is old and only partially ported to Python 3
- No type hints anywhere
- No docstrings on most classes/functions
- Mixed concerns -- rendering (OpenGL calls) interleaved with game logic throughout

## Modernization Phases

### Phase 1: Cleanup (High Priority)

Remove dead code and legacy directories (`_darcs/`, `dist/`, `backup/`, py2exe `setup.py`),
remove unused imports, fix bare `except:` clauses. This immediately reduces noise.

### Phase 2: Python 3 Fixes (High Priority)

Fix actual runtime errors on Python 3:
- Replace `dict.has_key(k)` with `k in dict`
- Replace `.iteritems()` with `.items()`
- Replace `dict.keys()` + `.sort()` with `sorted(dict.keys())`
- Fix pickle `open()` mode from `"r"` to `"rb"` / `"wb"`
- Convert print statements to print functions

### Phase 3: Modernize Classes & Imports (High Priority)

- Modernize class definitions (old-style classes are a no-op difference in Python 3 but
  signal outdated code)
- Replace `from X import *` with explicit imports to make the code navigable and prevent
  namespace pollution

### Phase 4: Code Style (Medium Priority)

- Normalize indentation (tabs to 4 spaces)
- Apply PEP 8 formatting (Black)
- Add type hints to key functions
- Add docstrings to classes and modules

### Phase 5: Modern Packaging (Medium Priority)

- Create `pyproject.toml` with proper metadata and dependency declarations
- Add `requirements.txt` or equivalent
- Remove the obsolete py2exe `setup.py`

### Phase 6: Dependency Management (Medium Priority)

- **PGU**: unmaintained and bundled; consider replacing with `pygame-gui` or keeping the
  vendored copy clean
- **configobj**: replace with stdlib `configparser`

### Phase 7: Architecture Improvements (Low Priority)

- Separate OpenGL rendering from game logic (currently deeply interleaved)
- Fix the `glutBitmapCharacter` no-op hack
- Add proper `logging` instead of silently swallowing exceptions

### Phase 8: Add Tests (Low Priority)

- Unit tests for pure logic: block generation, scoring, line clearing
- These can be tested without OpenGL/pygame initialization
