"""
Tema: RETROWAVE / SYNTHWAVE
Display landscape 960×480 — 100% PIL, sin URLs externas
"""
import math, random, datetime, subprocess, os
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H  = 960, 480
SKY_H = 238   # zona animada (0-237); stats en 238-480 (242px)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

# ── Paleta ────────────────────────────────────────────────────────────────────
BG    = (13,  0, 25)
PANEL = (8,   0, 18)
PINK  = (255,  0, 110)
DPINK = (100,  0,  45)
CYAN  = (0, 245, 255)
DCYAN = (0,  75, 100)
GOLD  = (255, 190,  11)
DGOLD = (90,   65,   0)
DPUR  = (35,   0,   65)

# ── Caché de fuentes ──────────────────────────────────────────────────────────
_FC = {}

def _fnt(path, size):
    k = (path, size)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(path, size)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

_FORB = os.path.join(_FD, "Orbitron-Black.ttf")
_FRAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_FMONO= os.path.join(_FD, "ShareTechMono.ttf")
_FTEKO= os.path.join(_FD, "Teko-Medium.ttf")

def _forb(s):  return _fnt(_FORB, s)
def _fraj(s):  return _fnt(_FRAJ, s)
def _fmono(s): return _fnt(_FMONO, s)

# ── Estrellas (posiciones fijas, parpadeo animado) ─────────────────────────────
random.seed(42)
_STARS = [(random.randint(0, W-1), random.randint(2, SKY_H-72), random.randint(1, 2))
          for _ in range(130)]
_TWINK = [random.uniform(0, 2*math.pi) for _ in range(130)]

# ── Red: tracking de delta de bytes ──────────────────────────────────────────
_nt   = [0, 0]       # [bytes_sent, bytes_recv] anterior
_ntx  = [0] * 20    # historial bytes_sent/s (ventana 20 frames)
_nrx  = [0] * 20    # historial bytes_recv/s

# ── Helpers de datos del sistema ─────────────────────────────────────────────
def _cpu():
    return psutil.cpu_percent(interval=None)

def _mem():
    return psutil.virtual_memory()

def _temp_cpu():
    try:
        t = psutil.sensors_temperatures()
        for k in ('k10temp', 'coretemp', 'cpu_thermal', 'acpitz'):
            if k in t:
                return t[k][0].current
    except Exception:
        pass
    return None

def _gpu_pct():
    try:
        r = subprocess.run(
            ['cat', '/sys/class/drm/card1/device/gpu_busy_percent'],
            capture_output=True, text=True, timeout=1)
        if r.returncode == 0:
            return int(r.stdout.strip())
    except Exception:
        pass
    return None

def _gpu_temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ('amdgpu', 'nvidia', 'radeon'):
            if k in t:
                return t[k][0].current
    except Exception:
        pass
    return None

def _disk():
    for path in ('/home', '/'):
        try:
            return psutil.disk_usage(path), path
        except Exception:
            pass
    return None, '/'

def _net(frame):
    global _nt, _ntx, _nrx
    if frame % 2 == 0:
        try:
            c = psutil.net_io_counters()
            if _nt[0]:
                tx = max(0, c.bytes_sent - _nt[0])
                rx = max(0, c.bytes_recv - _nt[1])
                _ntx = _ntx[1:] + [tx]
                _nrx = _nrx[1:] + [rx]
            _nt = [c.bytes_sent, c.bytes_recv]
        except Exception:
            pass
    return _ntx[-1], _nrx[-1]

def _fmt_bps(bps):
    # bytes per ~200ms → convert to per second
    bps_s = bps * 5
    if bps_s >= 1024*1024:
        return f"{bps_s/1024/1024:.1f}M/s"
    if bps_s >= 1024:
        return f"{bps_s/1024:.0f}K/s"
    return f"{bps_s:.0f}B/s"

def _val_col(v):
    if v < 70: return CYAN
    if v < 90: return GOLD
    return PINK

def _dim_of(col):
    if col == CYAN:  return DCYAN
    if col == GOLD:  return DGOLD
    return DPINK

def _temp_col(t):
    if t is None:  return DCYAN
    if t < 65:     return CYAN
    if t < 80:     return GOLD
    return PINK

# ── Glow helper ───────────────────────────────────────────────────────────────
_GLOW_OFFSETS = [(-2,-1),(2,-1),(-2,1),(2,1),(0,-2),(0,2)]

def _glow(d, x, y, text, font, col, dim):
    for dx, dy in _GLOW_OFFSETS:
        d.text((x+dx, y+dy), text, font=font, fill=dim)
    d.text((x, y), text, font=font, fill=col)

# ── Progress bar ─────────────────────────────────────────────────────────────
def _bar(d, x, y, w, h, pct, col, dim):
    d.rectangle([x-1, y-1, x+w+1, y+h+1], fill=(15, 3, 28), outline=dim)
    fw = int(w * min(pct, 100) / 100)
    for xi in range(fw):
        ratio = xi / max(fw, 1)
        r = int(col[0] * (0.15 + 0.85*ratio))
        g = int(col[1] * (0.15 + 0.85*ratio))
        b = int(col[2] * (0.15 + 0.85*ratio))
        d.line([(x+xi, y), (x+xi, y+h)], fill=(r, g, b))
    if fw > 2:
        d.line([(x+fw-1, y), (x+fw-1, y+h)], fill=col)

# ── Escena synthwave ──────────────────────────────────────────────────────────
def _draw_sky(img, d, frame):
    # Gradiente cielo (muy oscuro arriba → negro profundo)
    for y in range(SKY_H):
        ratio = y / SKY_H
        r = int(6  + ratio * 28)
        g = 0
        b = int(12 + ratio * 30)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Estrellas titilantes
    for i, (sx, sy, sr) in enumerate(_STARS):
        bright = int(110 + math.sin(frame * 0.17 + _TWINK[i]) * 90)
        bright = max(30, min(255, bright))
        c = (bright, bright, min(255, bright + 25))
        d.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=c)

    sun_cx, sun_cy = W // 2, 92
    sun_r = 62
    HORIZ = 168

    # Glow rings del sol (pulsantes)
    pulse = abs(math.sin(frame * 0.08))
    for i, ring_r in enumerate(range(sun_r + 38, sun_r + 8, -6)):
        fade_base = max(0, 70 - (ring_r - sun_r) * 4)
        fade = int(fade_base * (0.6 + 0.4 * pulse))
        ring_col = (min(255, fade + 30), 0, min(255, fade // 2))
        d.ellipse([sun_cx-ring_r, sun_cy-ring_r, sun_cx+ring_r, sun_cy+ring_r],
                  fill=ring_col)

    # Sol: círculo con gradiente amarillo→naranja→rosa (scanlines negras cada 5px)
    for sy in range(sun_cy - sun_r, sun_cy + sun_r + 1):
        dy2 = (sy - sun_cy) ** 2
        if dy2 > sun_r * sun_r:
            continue
        xd = int(math.sqrt(sun_r * sun_r - dy2))
        ratio = (sy - (sun_cy - sun_r)) / (2 * sun_r)  # 0 top, 1 bottom
        # top: yellow (255,220,0) → mid: orange (255,90,0) → bottom: hot pink (255,0,120)
        if ratio < 0.5:
            t = ratio * 2
            sr_ = 255
            sg_ = int(220 - t * 130)
            sb_ = 0
        else:
            t = (ratio - 0.5) * 2
            sr_ = 255
            sg_ = int(90 - t * 90)
            sb_ = int(t * 120)
        d.line([(sun_cx - xd, sy), (sun_cx + xd, sy)], fill=(sr_, sg_, sb_))

    # Scanlines negras cada 5px
    for sy in range(sun_cy - sun_r, sun_cy + sun_r + 1, 5):
        dy2 = (sy - sun_cy) ** 2
        if dy2 > sun_r * sun_r:
            continue
        xd = int(math.sqrt(sun_r * sun_r - dy2))
        d.line([(sun_cx - xd, sy), (sun_cx + xd, sy)], fill=BG, width=2)

    # Línea horizonte (triple para efecto neón)
    d.line([(0, HORIZ+2), (W, HORIZ+2)], fill=DPINK, width=4)
    d.line([(0, HORIZ),   (W, HORIZ)],   fill=PINK,  width=2)
    d.line([(0, HORIZ-1), (W, HORIZ-1)], fill=(255, 120, 180), width=1)

    # Grid perspectiva (HORIZ-238): líneas convergiendo al punto de fuga
    VP_X = W // 2
    VP_Y = HORIZ
    FLOOR_H = SKY_H - HORIZ  # 70px

    # Líneas verticales de perspectiva (radios desde VP)
    n_radials = 22
    for i in range(-n_radials // 2, n_radials // 2 + 1):
        bx = VP_X + i * (W // n_radials)
        d.line([(VP_X, VP_Y), (bx, SKY_H)], fill=DPINK, width=1)

    # Líneas horizontales con scroll hacia el espectador
    grid_speed = 4
    grid_period = 28
    grid_off = (frame * grid_speed) % grid_period
    n_hlines = 9
    for step in range(n_hlines + 2):
        # t: perspectiva cuadrática, 0=VP, 1=espectador
        raw = (step / n_hlines + grid_off / (n_hlines * grid_period)) % 1.0
        t2 = raw * raw
        gy = int(VP_Y + t2 * FLOOR_H)
        if gy < VP_Y or gy > SKY_H:
            continue
        # ancho de la línea se estrecha cerca del horizonte
        lx = int(VP_X - t2 * VP_X)
        rx = int(VP_X + t2 * (W - VP_X))
        intensity = int(40 + t2 * 180)
        grid_pink = (min(255, intensity), 0, min(255, intensity * 45 // 100))
        d.line([(lx, gy), (rx, gy)], fill=grid_pink, width=1)


# ── Panel de stats ────────────────────────────────────────────────────────────
def _draw_stats(d, frame, cpu, mem, ct, gpu, gt, disk_u, disk_path, tx, rx, now):
    PY0 = SKY_H   # 238

    # Fondo del panel
    d.rectangle([0, PY0, W, H], fill=PANEL)

    # Separador pulsante
    pw = int(abs(math.sin(frame * 0.12)) * W)
    d.line([(0, PY0),   (W, PY0)],   fill=DPINK, width=3)
    d.line([(0, PY0+2), (pw, PY0+2)], fill=PINK, width=1)

    # ── Determinar columnas de datos ──────────────────────────────────────────
    # 4 columnas de datos + 1 columna reloj (220px)
    CLK_W = 220
    DATA_W = W - CLK_W   # 740px
    N_COLS = 4

    # Columna 0: CPU
    # Columna 1: GPU si disponible, si no RAM
    # Columna 2: RAM
    # Columna 3: DISK /home

    disk_pct  = (disk_u.used / disk_u.total * 100) if disk_u else 0
    disk_used = (disk_u.used / 1024**3) if disk_u else 0
    disk_tot  = (disk_u.total / 1024**3) if disk_u else 0

    mem_used = (mem.total - mem.available) / 1024**3
    mem_tot  = mem.total / 1024**3

    # (label, value_str, pct, col, temp, sub_str)
    cols = []
    cc = _val_col(cpu)
    cols.append(("CPU", f"{cpu:.0f}%", cpu, cc, ct, None))

    if gpu is not None:
        gc = _val_col(gpu)
        cols.append(("GPU", f"{gpu:.0f}%", gpu, gc, gt, None))
    else:
        rc2 = _val_col(mem.percent)
        cols.append(("RAM", f"{mem_used:.1f}G", mem.percent, rc2, None, f"/{mem_tot:.0f}G"))

    rc = _val_col(mem.percent)
    cols.append(("RAM", f"{mem_used:.1f}G", mem.percent, rc, None, f"/{mem_tot:.0f}G"))

    dc = _val_col(disk_pct)
    lbl_disk = disk_path.replace('/home', 'HOME').replace('/', 'ROOT')
    cols.append((lbl_disk, f"{disk_used:.0f}G", disk_pct, dc, None, f"/{disk_tot:.0f}G"))

    # Asegurarse de que tenemos exactamente N_COLS
    cols = cols[:N_COLS]
    COL_W = DATA_W // N_COLS   # 185px

    TOP_PAD = 10
    py = PY0 + TOP_PAD

    # Alturas fijas dentro de las 242px disponibles:
    # py+0:  label (Rajdhani 24)
    # py+24: temp (Rajdhani 24) — solo si existe
    # py+36: valor grande (Orbitron-Black 84, con glow)
    # py+145: barra (altura 10)
    # py+158: sub-text (Rajdhani 20)
    # total ocupado: ~178px → cabe bien en 242px

    VAL_Y   = py + 36
    BAR_Y   = py + 150
    BAR_H   = 10
    SUB_Y   = py + 164

    for i, col_data in enumerate(cols):
        label, val_str, pct, col, temp, sub = col_data
        dim = _dim_of(col)
        cx = i * COL_W
        px = cx + 10
        pw_bar = COL_W - 20

        # Separador vertical (excepto antes del primero)
        if i > 0:
            d.line([(cx, PY0 + 5), (cx, H - 5)], fill=DPUR, width=1)

        # Label
        d.text((px, py), label, font=_fraj(24), fill=dim)

        # Temperatura (si existe) — alineada a la derecha de la columna
        if temp is not None:
            tc = _temp_col(temp)
            t_str = f"{temp:.0f}°C"
            # aproximamos ancho: 7px/char * len
            t_x = cx + COL_W - len(t_str) * 14 - 8
            d.text((t_x, py + 1), t_str, font=_fraj(22), fill=tc)

        # Valor principal con glow — auto-fit para que quepa en la columna
        max_w = pw_bar - 4
        for vsize in (84, 72, 60, 48, 38):
            f_test = _forb(vsize)
            bb = d.textbbox((0, 0), val_str, font=f_test)
            if (bb[2] - bb[0]) <= max_w:
                break
        _glow(d, px, VAL_Y, val_str, _forb(vsize), col, dim)

        # Barra de progreso
        _bar(d, px, BAR_Y, pw_bar, BAR_H, pct, col, dim)

        # Sub texto
        if sub:
            d.text((px, SUB_Y), sub, font=_fraj(20), fill=dim)

    # ── Columna reloj ─────────────────────────────────────────────────────────
    sep_x = DATA_W
    clk_x = sep_x + 6

    d.line([(sep_x, PY0 + 5), (sep_x, H - 5)], fill=DPUR, width=1)

    # HH:MM — tamaño 64 cabe bien en 214px disponibles
    hhmm = now.strftime("%H:%M")
    _glow(d, clk_x, py, hhmm, _forb(64), GOLD, DGOLD)

    # :SS en dorado tenue debajo
    ss = now.strftime(":%S")
    d.text((clk_x, py + 74), ss, font=_forb(40), fill=DGOLD)

    # Fecha
    fecha = now.strftime("%d/%m/%Y")
    d.text((clk_x, py + 120), fecha, font=_fraj(20), fill=DPUR)

    # NET up/down
    d.text((clk_x, py + 146), f"UP  {_fmt_bps(tx)}", font=_fmono(18), fill=DCYAN)
    d.text((clk_x, py + 168), f"DN  {_fmt_bps(rx)}", font=_fmono(18), fill=DPINK)


# ── Render principal ──────────────────────────────────────────────────────────
def render(frame):
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    # Zona superior: escena synthwave
    _draw_sky(img, d, frame)

    # Recoger datos del sistema
    cpu   = _cpu()
    mem   = _mem()
    ct    = _temp_cpu()
    gpu   = _gpu_pct()
    gt    = _gpu_temp()
    du, dp = _disk()
    tx, rx = _net(frame)
    now   = datetime.datetime.now()

    # Zona inferior: panel de stats
    _draw_stats(d, frame, cpu, mem, ct, gpu, gt, du, dp, tx, rx, now)

    return img
