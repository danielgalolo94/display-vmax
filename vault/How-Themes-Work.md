# How Themes Work

Technical architecture of the theme system.

## The contract

Each theme is a single `.py` file in `themes/`. It must export one function:

```python
def render(frame: int) -> PIL.Image.Image:
    ...
```

- `frame` — integer that increments by 1 each render cycle
- Return value — a `PIL.Image` in `RGB` mode, **960×480 pixels**
- The engine calls `render()` approximately every 200ms (~5 fps)
- `frame / 5` ≈ elapsed seconds since the theme was loaded

That's the entire API surface. No base class, no configuration dict, no callbacks.

---

## The engine loop

`display-engine.py` does this every 200ms:

1. Check `~/.local/share/xyz-display/theme` for a name change (hot-reload)
2. If changed: `importlib` loads the new theme module fresh
3. Call `theme.render(frame)`
4. Rotate the 960×480 image to the hardware's portrait orientation (FLIP_TOP_BOTTOM + TRANSPOSE)
5. JPEG-encode at quality 88
6. Write to USB bulk endpoint `0x02`

```
theme.render(frame) → 960×480 RGB → rotate → 480×960 JPEG → USB
```

> [!NOTE]
> Themes never need to handle rotation. Always draw in landscape 960×480 and the engine handles the rest.

---

## Canvas conventions

| Property | Value |
|---|---|
| Size | 960 × 480 px |
| Mode | `RGB` (no alpha) |
| Origin | Top-left (0, 0) |
| Coordinate system | Standard PIL — x right, y down |

```python
from PIL import Image, ImageDraw
img = Image.new('RGB', (960, 480), (0, 0, 0))
d   = ImageDraw.Draw(img)
```

---

## Font loading pattern

The standard caching pattern used across all themes:

```python
import os
from PIL import ImageFont

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

_F_ORB = os.path.join(_FD, "Orbitron-Black.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")

_FC = {}

def _fnt(path, size):
    k = (path, size)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(path, size)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

# Convenience lambdas per font
Fo = lambda s: _fnt(_F_ORB, s)   # Orbitron-Black
Fr = lambda s: _fnt(_F_RAJ, s)   # Rajdhani-SemiBold
```

The `_FC` dict is module-level, so fonts are only loaded from disk once per theme session. If a font file is missing, `load_default()` is silently used.

---

## Color convention

Colors are always plain RGB tuples — no alpha, no hex strings:

```python
CYAN  = (0, 218, 255)
PINK  = (255, 12, 188)
GREEN = (0, 210, 128)
BG    = (3, 6, 16)        # near-black background
DIM   = (0, 45, 65)       # muted accent
```

Alpha compositing (for glow effects) is done via temporary `RGBA` layers that get flattened back to `RGB` before return.

---

## Animation state

Themes use module-level globals to persist animation state between frames:

```python
# Rain drop positions
_drops = [random.randint(0, 480) for _ in range(80)]

# Star field
_stars = [(random.randint(0,960), random.randint(0,480), random.random())
          for _ in range(200)]

# Network delta tracking
_NET_ST = {'t': 0.0, 'sent': 0, 'recv': 0, 'ul': 0.0, 'dl': 0.0}
```

These are initialized at import time and mutated by each `render()` call. This is intentional — module-level globals survive across frames because the engine keeps the module alive.

> [!WARNING]
> When a theme is hot-reloaded, the module is re-imported fresh. All module-level state resets. This is usually fine (animation restarts from zero) but means any accumulated learning (like AGC in the music theme) resets too.

---

## Async / background threads

Slow I/O (audio capture, `playerctl`, network checks) must run in a background thread. The pattern:

```python
import threading, time

_result = None
_lock   = threading.Lock()

def _worker():
    global _result
    while True:
        val = slow_operation()
        with _lock:
            _result = val
        time.sleep(2)

threading.Thread(target=_worker, daemon=True).start()
```

In `render()`, read under the lock:

```python
with _lock:
    current = _result
```

`daemon=True` is required — it means the thread dies when the process exits, no cleanup needed.

---

## Theme identification (docstring)

`tema.sh` reads the `Tema:` line from the module docstring to display a human-readable description in the menu:

```python
"""
Tema: PHANTOM — White HUD para gabinete blanco
Display landscape 960x480
...
"""
```

The grep is `grep -m1 "Tema:" themes/mytheme.py`. Put it on the second line of the docstring.

---

## Hot-reload mechanism

The engine polls `~/.local/share/xyz-display/theme` every frame. When `tema.sh` applies a theme:

1. It writes the theme name to that file
2. On the next frame, the engine detects the change
3. It calls `importlib.util.spec_from_file_location()` to load the new `.py` fresh
4. `frame` resets to 0
5. The old module is garbage collected

This means you can switch themes without restarting the systemd service.

---

## The Tema: docstring convention

Each theme file should start with:

```python
"""
Tema: SHORT NAME — brief description in Spanish or English
Display landscape 960x480
[any additional notes]
"""
```

`tema.sh` uses `grep -m1 "Tema:"` to extract the description for the interactive menu.

See [[Creating-a-Theme]] for a full walkthrough, and [[Themes-Gallery]] for all existing themes.
