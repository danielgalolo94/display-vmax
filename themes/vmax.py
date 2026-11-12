"""
Tema: VMAX — HUD FUI azul/cian (Ryzen 9 9900X · 48 GB)
Estilo: fondo azul marino, líneas cian con brillo, paneles con esquinas
cortadas, anillos tipo radar, barras segmentadas y gráfico de área.
Display landscape 960×480. Textos grandes (mínimo 26 px) para el display chico.
Métricas con psutil (funciona en Windows y Linux).
"""
import os, math, time as _t, datetime
from collections import deque
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H  = 960, 480
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = (4, 12, 26)
PANEL  = (8, 22, 42)
CYAN   = (0, 232, 255)
CYAN_M = (0, 150, 190)
CYAN_D = (0, 64, 92)
CYAN_V = (6, 36, 58)
AMBER  = (255, 176, 0)
RED    = (255, 72, 84)
TXT    = (226, 248, 255)

def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

# ── Fuentes (grandes a propósito) ─────────────────────────────────────────────
_FONTS = {}
def F(sz, name="Orbitron-Bold.ttf"):
    key = (name, sz)
    if key not in _FONTS:
        try:    _FONTS[key] = ImageFont.truetype(os.path.join(_FD, name), sz)
        except: _FONTS[key] = ImageFont.load_default()
    return _FONTS[key]
NUM   = "Orbitron-Bold.ttf"
TXT_F = "Rajdhani-SemiBold.ttf"
MONO  = "CaskaydiaMonoNF-SemiBold.ttf"

# ── Métricas ──────────────────────────────────────────────────────────────────
psutil.cpu_percent(interval=None)
psutil.cpu_percent(interval=None, percpu=True)
_NET  = {"t": 0.0, "sent": 0, "recv": 0, "ul": 0.0, "dl": 0.0}
_HIST = deque([0.0] * 60, maxlen=60)

def _net():
    try:
        now = _t.time(); c = psutil.net_io_counters()
        dt = now - _NET["t"]
        if _NET["t"] > 0 and dt > 0.05:
            _NET["ul"] = (c.bytes_sent - _NET["sent"]) / dt / 1024
            _NET["dl"] = (c.bytes_recv - _NET["recv"]) / dt / 1024
        _NET.update({"t": now, "sent": c.bytes_sent, "recv": c.bytes_recv})
    except Exception:
        pass
    return max(0.0, _NET["ul"]), max(0.0, _NET["dl"])

def _rate(kb):
    return f"{kb/1024:.1f} MB/s" if kb >= 1024 else f"{kb:.0f} KB/s"

def _disks():
    res = []
    try:
        for p in psutil.disk_partitions(all=False):
            if "cdrom" in p.opts.lower() or not p.fstype:
                continue
            try:
                u = psutil.disk_usage(p.mountpoint)
                res.append((p.mountpoint.rstrip("\\/"), u.percent))
            except Exception:
                pass
    except Exception:
        pass
    return res[:2]

def _vcol(v):
    return CYAN if v < 70 else (AMBER if v < 90 else RED)

# ── Formas HUD ────────────────────────────────────────────────────────────────
def _chamfer(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
            (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]

def _glow_lines(d, pts, col, closed=True, w=2):
    n = len(pts)
    segs = range(n) if closed else range(n - 1)
    for i in segs:
        a = pts[i]; b = pts[(i + 1) % n]
        d.line([a, b], fill=mix(col, BG, 0.75), width=w + 4)
        d.line([a, b], fill=col, width=w)

def _panel(d, x0, y0, x1, y1, title, pulse):
    pts = _chamfer(x0, y0, x1, y1, 22)
    d.polygon(pts, fill=PANEL)
    _glow_lines(d, pts, mix(CYAN_M, CYAN, pulse * 0.4), closed=True, w=2)
    # notch decorativo arriba a la derecha
    d.line([(x1 - 120, y0 + 1), (x1 - 40, y0 + 1)], fill=CYAN, width=3)
    d.text((x0 + 24, y0 + 10), title, font=F(30, TXT_F), fill=CYAN)
    d.line([(x0 + 24, y0 + 48), (x0 + 84, y0 + 48)], fill=AMBER, width=3)

def _ring(d, cx, cy, r, pct, col, frame):
    # anillo exterior con segmentos de fondo y arco de valor
    bbox = [cx - r, cy - r, cx + r, cy + r]
    for k in range(0, 360, 12):
        d.arc(bbox, k, k + 8, fill=CYAN_V, width=10)
    end = 135 + 270 * max(0.0, min(pct, 100)) / 100
    if pct > 0:
        d.arc([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], 135, end, fill=col, width=10)
    # anillo interior giratorio (radar)
    ri = r - 26
    rot = (frame * 4) % 360
    for k in range(0, 360, 30):
        a0 = k + rot
        d.arc([cx - ri, cy - ri, cx + ri, cy + ri], a0, a0 + 16, fill=CYAN_M, width=3)
    # marca de barrido: arco corto sobre el anillo interior (sin tapar el número)
    d.arc([cx - ri, cy - ri, cx + ri, cy + ri], rot, rot + 40, fill=CYAN, width=5)

def _seg_bar(d, x, y, w, h, pct, col, n=20):
    gap = 4
    sw = (w - gap * (n - 1)) / n
    on = int(round(n * max(0.0, min(pct, 100)) / 100))
    for i in range(n):
        x0 = x + i * (sw + gap)
        fill = col if i < on else CYAN_V
        d.rectangle([x0, y, x0 + sw, y + h], fill=fill)

def _capsule(d, x, y, w, h, pct, col):
    r = h // 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=CYAN_V, outline=CYAN_D, width=2)
    fw = int((w - 6) * max(0.0, min(pct, 100)) / 100)
    if fw > 4:
        d.rounded_rectangle([x + 3, y + 3, x + 3 + fw, y + h - 3], radius=r - 3, fill=col)

def _area(d, x0, y0, x1, y1, vals, col):
    n = len(vals)
    if n < 2: return
    h = y1 - y0
    pts = []
    for i, v in enumerate(vals):
        px = x0 + (x1 - x0) * i / (n - 1)
        py = y1 - h * max(0.0, min(v, 100)) / 100
        pts.append((px, py))
    # relleno translúcido simulado
    fill_col = mix(BG, col, 0.22)
    poly = pts + [(x1, y1), (x0, y1)]
    d.polygon(poly, fill=fill_col)
    for i in range(n - 1):
        d.line([pts[i], pts[i + 1]], fill=col, width=3)
    # rejilla
    for k in (25, 50, 75):
        gy = y1 - h * k / 100
        d.line([(x0, gy), (x1, gy)], fill=CYAN_V, width=1)

# ── Render ────────────────────────────────────────────────────────────────────
_GRID = None
def _grid():
    # la rejilla no cambia: se dibuja una vez y se reutiliza en cada frame
    global _GRID
    if _GRID is None:
        _GRID = Image.new("RGB", (W, H), BG)
        g = ImageDraw.Draw(_GRID)
        for gx in range(0, W, 40):
            g.line([(gx, 0), (gx, H)], fill=(7, 20, 38))
        for gy in range(0, H, 40):
            g.line([(0, gy), (W, gy)], fill=(7, 20, 38))
    return _GRID

def render(frame):
    img = _grid().copy()
    d = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(frame * 0.35)

    now = datetime.datetime.now()
    cpu = psutil.cpu_percent(interval=None)
    cores = psutil.cpu_percent(interval=None, percpu=True)
    vm = psutil.virtual_memory()
    ul, dl = _net()
    _HIST.append(cpu)

    # ── Barra superior ────────────────────────────────────────────────────
    d.rectangle([0, 0, W, 50], fill=(5, 16, 32))
    d.line([(0, 50), (W, 50)], fill=CYAN_M, width=2)
    d.text((18, 25), "VMAX", font=F(36, NUM), fill=CYAN, anchor="lm")
    d.text((196, 25), "SYSTEM CORE", font=F(30, TXT_F), fill=AMBER, anchor="lm")
    d.text((W - 18, 25), now.strftime("%H:%M:%S"), font=F(36, MONO),
           fill=TXT, anchor="rm")

    # ── Panel 1: CPU con anillos ──────────────────────────────────────────
    _panel(d, 12, 62, 316, 470, "CPU", pulse)
    _ring(d, 164, 236, 96, cpu, _vcol(cpu), frame)
    d.text((164, 226), f"{cpu:.0f}", font=F(76, NUM), fill=TXT, anchor="mm")
    d.text((164, 290), "%", font=F(30, TXT_F), fill=CYAN, anchor="mm")
    temp_txt = "TEMP --"   # Windows no expone temperatura de CPU a psutil
    d.text((164, 380), temp_txt, font=F(32, TXT_F), fill=CYAN, anchor="mm")
    d.text((164, 428), f"{psutil.cpu_count(logical=True)} HILOS",
           font=F(30, TXT_F), fill=TXT, anchor="mm")

    # ── Panel 2: RAM + discos ─────────────────────────────────────────────
    _panel(d, 330, 62, 634, 470, "RAM", pulse)
    _ring(d, 482, 236, 96, vm.percent, _vcol(vm.percent), frame + 40)
    d.text((482, 226), f"{vm.percent:.0f}", font=F(76, NUM), fill=TXT, anchor="mm")
    d.text((482, 290), "%", font=F(30, TXT_F), fill=CYAN, anchor="mm")
    used = vm.used / 1024**3; tot = vm.total / 1024**3
    d.text((482, 352), f"{used:.0f}/{tot:.0f} GB", font=F(30, TXT_F),
           fill=TXT, anchor="mm")
    y = 388
    for mnt, pct in _disks():
        d.text((352, y + 15), mnt, font=F(30, TXT_F), fill=CYAN, anchor="lm")
        _capsule(d, 404, y, 122, 30, pct, _vcol(pct))
        d.text((604, y + 15), f"{pct:.0f}%", font=F(28, MONO), fill=TXT, anchor="rm")
        y += 42

    # ── Panel 3: historial + hilos + red ──────────────────────────────────
    _panel(d, 648, 62, 948, 470, "HILOS", pulse)
    _area(d, 664, 110, 932, 250, list(_HIST), CYAN)
    bx0, bw, gap = 664, 8, 3
    for i, v in enumerate(cores[:24]):
        x = bx0 + i * (bw + gap)
        top = 330
        d.rectangle([x, top, x + bw, 370], fill=CYAN_V)
        fh = int(40 * max(0.0, min(v, 100)) / 100)
        if fh > 0:
            d.rectangle([x, 370 - fh, x + bw, 370], fill=_vcol(v))
    d.text((664, 396), "UP", font=F(30, TXT_F), fill=AMBER, anchor="lm")
    d.text((932, 396), _rate(ul), font=F(28, MONO), fill=TXT, anchor="rm")
    d.text((664, 440), "DN", font=F(30, TXT_F), fill=CYAN, anchor="lm")
    d.text((932, 440), _rate(dl), font=F(28, MONO), fill=TXT, anchor="rm")

    # ── Línea de escaneo animada ──────────────────────────────────────────
    sy = (frame * 7) % (H - 80) + 60
    d.line([(14, sy), (W - 14, sy)], fill=mix(BG, CYAN, 0.12), width=1)

    return img
