# Creating a Theme

Step-by-step guide to writing a new theme from scratch.

---

## Minimal template

Save this as `themes/mytheme.py` and it will immediately work:

```python
"""
Tema: MY THEME — one-line description
Display landscape 960x480
"""
import datetime
import psutil
from PIL import Image, ImageDraw, ImageFont
import os

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 960, 480

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")
_F_ORB = os.path.join(_FD, "Orbitron-Black.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")

# ── Font cache ────────────────────────────────────────────────────────────────
_FC = {}
def _fnt(path, size):
    k = (path, size)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(path, size)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Fo = lambda s: _fnt(_F_ORB, s)   # Orbitron-Black  — big values
Fr = lambda s: _fnt(_F_RAJ, s)   # Rajdhani        — labels

# ── Palette ───────────────────────────────────────────────────────────────────
BG   = (5, 8, 20)
CYAN = (0, 218, 255)
DIM  = (0, 60, 90)
WHT  = (200, 230, 255)

# ── Animation state ───────────────────────────────────────────────────────────
# (add module-level variables here for things that persist across frames)

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame: int):
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    now = datetime.datetime.now()
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    # Clock
    d.text((480, 60), now.strftime('%H:%M:%S'), font=Fo(72), fill=CYAN, anchor='mt')

    # CPU bar
    bar_w = int(900 * cpu / 100)
    d.rectangle([30, 180, 930, 220], outline=DIM)
    d.rectangle([30, 180, 30 + bar_w, 220], fill=CYAN)
    d.text((30, 230), f"CPU  {cpu:.0f}%", font=Fr(36), fill=WHT)

    # RAM bar
    bar_w = int(900 * mem.percent / 100)
    d.rectangle([30, 280, 930, 320], outline=DIM)
    d.rectangle([30, 280, 30 + bar_w, 320], fill=(100, 60, 255))
    d.text((30, 330), f"RAM  {mem.percent:.0f}%  ({mem.used//1024**3:.1f} / {mem.total//1024**3:.0f} GB)",
           font=Fr(36), fill=WHT)

    return img
```

---

## Test without the display

```bash
python3 -c "from themes.mytheme import render; render(0).save('/tmp/test.png')"
xdg-open /tmp/test.png
```

Test a few frames:

```bash
python3 -c "
from themes.mytheme import render
for i in [0, 30, 60, 120]:
    render(i).save(f'/tmp/test_{i}.png')
    print(f'frame {i} saved')
"
```

---

## Apply to the display

```bash
bash tema.sh mytheme
```

---

## Standard sections (in order)

Every real theme follows this structure:

```
1. Module docstring with Tema: line
2. Imports
3. W, H = 960, 480
4. Path setup (_BASE, _FD, font paths)
5. Font cache (_FC, _fnt, shortcut lambdas)
6. Palette (color constants)
7. Sensor helpers (_temp, _gpu_pct, etc.)
8. Animation state (module-level globals)
9. Background thread (if needed for slow I/O)
10. render(frame) function
```

---

## Pattern: horizontal bar gauge

```python
def _hbar(d, x, y, w, h, pct, col, bg=(20, 20, 40)):
    """Draw a filled horizontal progress bar."""
    d.rectangle([x, y, x + w, y + h], fill=bg, outline=col)
    fw = int(w * min(pct, 100) / 100)
    if fw > 0:
        d.rectangle([x, y, x + fw, y + h], fill=col)

# Usage
_hbar(d, 30, 200, 400, 14, cpu_percent, (0, 218, 255))
```

---

## Pattern: glow text

PIL has no built-in glow. The trick is to draw shifted copies in a dim color first:

```python
def _glow_text(d, x, y, text, size, col, glow_col, font_fn):
    f = font_fn(size)
    offsets = [(-2,-1),(2,-1),(-2,1),(2,1),(0,-2),(0,2),(-1,-2),(1,-2)]
    for dx, dy in offsets:
        d.text((x + dx, y + dy), text, font=f, fill=glow_col)
    d.text((x, y), text, font=f, fill=col)

# Usage
_glow_text(d, 100, 50, "99%", 80, (0, 218, 255), (0, 40, 60), Fo)
```

---

## Pattern: sparkline (mini graph)

```python
_history = []   # module-level

def _sparkline(d, x, y, w, h, values, col):
    if len(values) < 2:
        return
    mx = max(values) or 1
    pts = []
    for i, v in enumerate(values[-w:]):
        px_ = x + int(i * w / len(values))
        py_ = y + h - int(v / mx * h)
        pts.append((px_, py_))
    if len(pts) >= 2:
        d.line(pts, fill=col, width=1)

# In render():
_history.append(psutil.cpu_percent(interval=None))
if len(_history) > 120:
    _history.pop(0)
_sparkline(d, 30, 300, 300, 60, _history, (0, 218, 255))
```

---

## Pattern: color-coded value (green/yellow/red)

```python
def _val_col(v, warn=70, crit=90):
    if v < warn:  return (28, 185, 95)    # green
    if v < crit:  return (215, 155, 15)   # yellow/orange
    return (215, 50, 50)                   # red
```

---

## Standard sensor helpers (copy-paste ready)

```python
import psutil, subprocess

def _cpu_pct():
    return psutil.cpu_percent(interval=None)

def _mem():
    return psutil.virtual_memory()

def _temp():
    """CPU temperature — works on AMD (k10temp) and Intel (coretemp)."""
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal', 'acpitz']:
            if k in t:
                return t[k][0].current
    except:
        pass
    return None

def _gpu_pct():
    """AMD GPU busy % via sysfs."""
    try:
        r = subprocess.run(
            ['cat', '/sys/class/drm/card1/device/gpu_busy_percent'],
            capture_output=True, text=True, timeout=1)
        if r.returncode == 0:
            return int(r.stdout.strip())
    except:
        pass
    return None

def _gtemp():
    """GPU temperature via psutil sensors."""
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu', 'nvidia', 'radeon']:
            if k in t:
                return t[k][0].current
    except:
        pass
    return None

# Network delta — call _net() every frame
_NET_ST = {'t': 0.0, 'sent': 0, 'recv': 0, 'ul': 0.0, 'dl': 0.0}

def _net():
    import time as _time
    global _NET_ST
    try:
        now = _time.time()
        c   = psutil.net_io_counters()
        dt  = now - _NET_ST['t']
        if dt > 0.05 and _NET_ST['t'] > 0:
            _NET_ST['ul'] = (c.bytes_sent - _NET_ST['sent']) / dt / 1024
            _NET_ST['dl'] = (c.bytes_recv - _NET_ST['recv']) / dt / 1024
        _NET_ST.update({'t': now, 'sent': c.bytes_sent, 'recv': c.bytes_recv})
        return max(0.0, _NET_ST['ul']), max(0.0, _NET_ST['dl'])
    except:
        return 0.0, 0.0
```

---

## Adding an async worker (slow I/O)

For anything that might block (DNS, subprocess, file read over network):

```python
import threading, time

_cached_value = None
_lock         = threading.Lock()

def _worker():
    global _cached_value
    while True:
        try:
            result = slow_external_call()
            with _lock:
                _cached_value = result
        except Exception as e:
            print(f"[mytheme] worker error: {e}")
        time.sleep(5)   # update interval

threading.Thread(target=_worker, daemon=True).start()

# In render():
with _lock:
    val = _cached_value
```

> [!WARNING]
> Never do blocking I/O directly in `render()`. It will cause the engine to stutter or freeze the frame loop.

---

## Checklist before shipping

- [ ] Docstring has a `Tema:` line on line 2
- [ ] `render()` always returns a `PIL.Image` in `RGB` mode, size `960x480`
- [ ] No blocking calls in `render()` — slow I/O is in a daemon thread
- [ ] `psutil.cpu_percent(interval=None)` — non-blocking form
- [ ] Fonts loaded via `_FC` cache, not `ImageFont.truetype()` in `render()` directly
- [ ] Module-level globals initialized before `render()` is called
- [ ] Tested with `python3 -c "from themes.mytheme import render; render(0).save('/tmp/t.png')"`

See [[How-Themes-Work]] for architecture details, [[Sensors-Reference]] for all available sensor calls.
