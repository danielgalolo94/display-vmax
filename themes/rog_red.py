"""
Tema: ROG RED — Gaming HUD rojo con fondo ASUS ROG
Display landscape 960x480
Paleta roja sobre imagen ROG oscura
"""
import math, datetime, subprocess, threading, time, socket, json
import psutil
from PIL import Image, ImageDraw, ImageFont
import numpy as np

W, H = 960, 480
import os
_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS = os.path.join(_BASE, "assets")
_FD     = os.path.join(_BASE, "fonts")

_F_ORB = os.path.join(_FD, "Orbitron-Black.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_DAT = os.path.join(_FD, "NotoSansMono-Bold.ttf")
_F_MON = os.path.join(_FD, "ShareTechMono.ttf")
_F_NRD = os.path.join(_FD, "FiraCodeNerdFont-Medium.ttf")
_F_BEB = os.path.join(_FD, "BebasNeue-Regular.ttf")
_F_BCO = os.path.join(_FD, "BarlowCondensed-ExtraBold.ttf")
_F_MIC = os.path.join(_FD, "Michroma-Regular.ttf")

_FC = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(p, s)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Fo  = lambda s: _fnt(_F_ORB, s)
Fb  = lambda s: _fnt(_F_BEB, s)
Fbc = lambda s: _fnt(_F_BCO, s)
Fmc = lambda s: _fnt(_F_MIC, s)
Fr  = lambda s: _fnt(_F_RAJ, s)
Fd  = lambda s: _fnt(_F_DAT, s)
Fm  = lambda s: _fnt(_F_MON, s)
Fn  = lambda s: _fnt(_F_NRD, s)

# ── Paleta ROG RED ────────────────────────────────────────────────────────────
BG        = (8,   3,   3)
INK       = (238, 243, 255)
INK2      = (200, 155, 155)
INK3      = (100,  50,  50)
BLUE      = (215,  12,  12)    # rojo ROG principal (reusa nombre BLUE para compat.)
BLUE_DARK = (90,    5,   5)
BLUE_DIM  = (40,   10,  10)
PINK      = (255, 100,   0)    # naranja brillante como accent line
PINK2     = (255, 160,  30)
CY        = (215,  12,  12)    # = BLUE en este tema
GRN       = (18,  218, 108)
ORG       = (255, 128,  18)
WARN      = (255, 175,  10)
CRIT      = (255,  80,  20)
TRACK     = (28,    8,   8)
DIVL      = (48,   16,  16)

# Colores duros internos (gauge interior)
_GAUGE_CENTER_BG = (14,  5,  5)
_GAUGE_NUM_GLOW  = (100, 0,  0)
_GAUGE_BLADE_OFF = (30,  8,  8)

# ── Fondo ASUS ROG (cargado y teñido rojo) ────────────────────────────────────
_BG_PATH = os.path.join(_ASSETS, "rog_dark_bg.jpg")
_bg_img  = None

def _load_bg():
    global _bg_img
    try:
        src = Image.open(_BG_PATH).convert('RGB')
        w, h = src.size
        # Crop centrado a 2:1
        if w / h > W / H:
            nw = int(h * W / H)
            src = src.crop([(w-nw)//2, 0, (w-nw)//2+nw, h])
        else:
            nh = int(w * H / W)
            src = src.crop([0, (h-nh)//2, w, (h-nh)//2+nh])
        src = src.resize((W, H), Image.LANCZOS)
        # Teñir rojo: boost canal rojo, aplastar verde y azul
        arr = np.array(src, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * 0.40 + 8, 0, 255)
        arr[:, :, 1] = np.clip(arr[:, :, 1] * 0.08 + 3, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * 0.06 + 3, 0, 255)
        _bg_img = Image.fromarray(arr.astype(np.uint8))
    except Exception as e:
        print(f"[rog_red] bg load error: {e}")

_load_bg()

# ── Sensores ──────────────────────────────────────────────────────────────────
def _cores():
    try:    return psutil.cpu_percent(percpu=True, interval=None)
    except: return [0.0] * 4

def _mem():   return psutil.virtual_memory()

def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal', 'acpitz']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _gpu():
    try:
        r = subprocess.run(['cat', '/sys/class/drm/card1/device/gpu_busy_percent'],
                           capture_output=True, text=True, timeout=1)
        if r.returncode == 0: return float(r.stdout.strip())
    except: pass
    return None

def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu', 'nvidia', 'radeon']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _disk():
    for mount in ['/home', '/']:
        try:
            return psutil.disk_usage(mount), mount
        except: pass
    return None, '/'

def _freq():
    try:    return psutil.cpu_freq()
    except: return None

def _vram():
    try:
        u = int(open('/sys/class/drm/card1/device/mem_info_vram_used').read().strip())
        t = int(open('/sys/class/drm/card1/device/mem_info_vram_total').read().strip())
        return u / 1024**3, t / 1024**3
    except: return None, None

def _gpu_clock():
    try:
        with open('/sys/class/drm/card1/device/pp_dpm_sclk') as f:
            for line in f:
                if '*' in line:
                    for part in line.split():
                        p = part.replace('Mhz', '').replace('MHz', '')
                        try: return float(p)
                        except: pass
    except: pass
    return None

_mon_cache = {'res': None, 'hz': None, 'ts': 0.0}

def _monitor_info():
    if time.time() - _mon_cache['ts'] < 60:
        return _mon_cache['res'], _mon_cache['hz']
    try:
        r = subprocess.run(['hyprctl', 'monitors', '-j'],
                           capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            mons = json.loads(r.stdout)
            if mons:
                m = mons[0]
                _mon_cache['res'] = (m.get('width', 1920), m.get('height', 1080))
                _mon_cache['hz']  = int(m.get('refreshRate', 60))
    except: pass
    _mon_cache['ts'] = time.time()
    return _mon_cache['res'], _mon_cache['hz']

def _tc(t):
    if t is None: return CY
    if t < 65:    return CY
    if t < 80:    return WARN
    return CRIT

def _vc(v):
    if v < 70:  return INK
    if v < 90:  return WARN
    return CRIT

# ── Primitivas ────────────────────────────────────────────────────────────────
def _ctr(d, cx, y, txt, font, col):
    bb = d.textbbox((0, 0), txt, font=font)
    d.text((cx - (bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _right(d, rx, y, txt, font, col):
    bb = d.textbbox((0, 0), txt, font=font)
    d.text((rx - (bb[2]-bb[0]), y), txt, font=font, fill=col)

def _tw(d, txt, font):
    bb = d.textbbox((0, 0), txt, font=font)
    return bb[2]-bb[0], bb[3]-bb[1]

def _dotline(d, x, y, w, col, dw=5, gap=4):
    px = x
    while px < x + w:
        d.line([(px, y), (min(px+dw, x+w), y)], fill=col, width=2)
        px += dw + gap

def _tri(d, x, y, col=None):
    col = col or BLUE
    d.polygon([(x, y+6), (x+10, y+2), (x+10, y+10)], fill=col)

def _tri_r(d, rx, y, col=None):
    col = col or BLUE
    d.polygon([(rx, y+2), (rx, y+10), (rx-10, y+6)], fill=col)

def _data_row(d, x, y, value_str, unit_str, unit_font, col=INK):
    vf = Fb(66)
    vw, vh = _tw(d, value_str, vf)
    for off in [(2,0),(-2,0),(0,2),(0,-2)]:
        d.text((x+off[0], y+off[1]), value_str, font=vf,
               fill=tuple(min(255,c//5) for c in col))
    d.text((x, y), value_str, font=vf, fill=INK)
    d.text((x+vw+5, y+vh-_tw(d, unit_str, unit_font)[1]-4), unit_str,
           font=unit_font, fill=INK2)
    return vh

def _data_row_r(d, rx, y, value_str, unit_str, unit_font, col=INK):
    vf = Fb(68)
    vw, vh = _tw(d, value_str, vf)
    uw, uh = _tw(d, unit_str, unit_font)
    ux = rx - uw
    vx = ux - 5 - vw
    for off in [(2,0),(-2,0),(0,2),(0,-2)]:
        d.text((vx+off[0], y+off[1]), value_str, font=vf,
               fill=tuple(min(255,c//5) for c in col))
    d.text((vx, y), value_str, font=vf, fill=INK)
    d.text((ux, y+vh-uh-4), unit_str, font=unit_font, fill=INK2)
    return vh

# ── Badge estilo ROG ──────────────────────────────────────────────────────────
def _rog_badge(d, x1, y1, x2, y2, text):
    h = y2 - y1
    w = x2 - x1
    d.rectangle([x1, y1, x2, y2], fill=BLUE)
    stripe = tuple(max(0, c - 50) for c in BLUE)
    for i in range(-h, w + h, 10):
        lx1, lx2 = x1 + i, x1 + i + h
        ly1, ly2 = y1, y2
        if lx1 < x1:
            ratio = (x1 - lx1) / max(h, 1)
            ly1 = int(y1 + ratio * h); lx1 = x1
        if lx2 > x2:
            ratio = (lx2 - x2) / max(h, 1)
            ly2 = int(y2 - ratio * h); lx2 = x2
        if lx1 < x2 and lx2 > x1:
            d.line([(lx1, ly1), (lx2, ly2)], fill=stripe, width=4)
    d.text((x1+10, y1 + (h-20)//2), text, font=Fbc(26), fill=INK)

# ── Gauge circular RAM (rojo) ─────────────────────────────────────────────────
def _ram_gauge(d, cx, cy, r, pct, frame):
    # Glow exterior rojizo
    for gr in range(r+28, r+5, -4):
        intensity = max(0, 22 - (gr - r))
        d.ellipse([cx-gr, cy-gr, cx+gr, cy+gr],
                  outline=(intensity*3, intensity//4, intensity//4), width=1)

    # Tick marks exteriores
    N_TICKS = 60
    for i in range(N_TICKS):
        a = math.radians(-90 + i * 360 / N_TICKS)
        big = (i % 5 == 0)
        r1 = r + (1 if big else 3)
        r2 = r + (12 if big else 7)
        col = INK3 if big else DIVL
        d.line([(cx+r1*math.cos(a), cy+r1*math.sin(a)),
                (cx+r2*math.cos(a), cy+r2*math.sin(a))],
               fill=col, width=(2 if big else 1))

    # Anillo de segmentos exteriores
    N_SEGS = 36
    r_arc  = r - 22
    filled = int(N_SEGS * pct / 100)
    for i in range(N_SEGS):
        sa = -90 + i * 360/N_SEGS
        ea = sa + 360/N_SEGS - 2.5
        col = BLUE if i < filled else BLUE_DIM
        if i < filled and i == filled - 1:
            d.arc([cx-r_arc-4, cy-r_arc-4, cx+r_arc+4, cy+r_arc+4],
                  start=sa, end=ea, fill=tuple(min(255,c//2) for c in BLUE), width=18)
        d.arc([cx-r_arc, cy-r_arc, cx+r_arc, cy+r_arc],
              start=sa, end=ea, fill=col, width=14)

    # Arco naranja de progreso en exterior
    if pct > 1:
        arc_end = -90 + 360 * pct / 100
        d.arc([cx-(r+16), cy-(r+16), cx+(r+16), cy+(r+16)],
              start=-90, end=arc_end, fill=PINK, width=3)
        tip_a = math.radians(arc_end)
        tx = cx + (r+16) * math.cos(tip_a)
        ty = cy + (r+16) * math.sin(tip_a)
        d.ellipse([tx-5, ty-5, tx+5, ty+5], fill=PINK2)

    # Indicador superior
    d.polygon([(cx, cy-r-20), (cx-6, cy-r-8), (cx+6, cy-r-8)], fill=BLUE)

    # Anillo interior de aspas
    N_BLADES = 24
    r_blade  = r_arc - 20
    filled_b = int(N_BLADES * pct / 100)
    for i in range(N_BLADES):
        sa = -90 + i * 360/N_BLADES
        ea = sa + 360/N_BLADES - 3
        col = BLUE if i < filled_b else _GAUGE_BLADE_OFF
        d.arc([cx-r_blade, cy-r_blade, cx+r_blade, cy+r_blade],
              start=sa, end=ea, fill=col, width=16)

    # Círculo central
    r_center = r_blade - 20
    d.ellipse([cx-r_center, cy-r_center, cx+r_center, cy+r_center],
              fill=_GAUGE_CENTER_BG)

    # Anillo pulsante
    pulse = 0.5 + 0.5 * math.sin(frame * 0.07)
    pr = int(r_center - 6 - pulse * 6)
    d.ellipse([cx-pr, cy-pr, cx+pr, cy+pr],
              outline=(int(BLUE[0]*pulse*0.4), 0, 0), width=1)

    # Número central
    pct_str = f"{pct:.0f}"
    pfont   = Fb(80)
    pw, ph  = _tw(d, pct_str, pfont)
    for off in [(3,0),(-3,0),(0,3),(0,-3),(2,2),(-2,-2)]:
        d.text((cx-pw//2+off[0], cy-ph//2-6+off[1]), pct_str,
               font=pfont, fill=_GAUGE_NUM_GLOW)
    d.text((cx-pw//2, cy-ph//2-6), pct_str, font=pfont, fill=INK)
    d.text((cx+pw//2+3, cy-ph//2+12), "%", font=Fbc(22), fill=INK2)

    _ctr(d, cx, cy+ph//2+10, "RAM Usage", Fbc(18), INK2)
    _ctr(d, cx, cy-ph//2-26, "MEMORY",    Fr(15), INK3)

    # Barra inferior de RAM
    ram_bar_w = r_center * 2 - 20
    bx = cx - ram_bar_w//2
    by = cy + ph//2 + 34
    d.rectangle([bx, by, bx+ram_bar_w, by+5], fill=TRACK)
    fw = int(ram_bar_w * pct / 100)
    if fw > 0:
        d.rectangle([bx, by, bx+fw, by+5], fill=BLUE)


# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    # Base: fondo ROG teñido rojo o color sólido si no hay imagen
    if _bg_img:
        img = _bg_img.copy()
    else:
        img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    # ── Leer sensores ─────────────────────────────────────────────────────────
    cores = _cores()
    cpu   = sum(cores)/len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gpu   = _gpu()
    gt    = _gtemp()
    disk, _ = _disk()
    freq  = _freq()
    vu, vt  = _vram()
    gpu_clk = _gpu_clock()
    res, hz = _monitor_info()
    now   = datetime.datetime.now()

    # ── CABECERA ──────────────────────────────────────────────────────────────
    ts = now.strftime("%H:%M:%S")
    d.text((14, 8), ts, font=Fb(42), fill=INK)
    tw_ts, _ = _tw(d, ts, Fb(42))
    d.line([(14, 42), (14+tw_ts, 42)], fill=BLUE, width=2)

    _right(d, W-14, 8, now.strftime("%Y/%m/%d"), Fr(26), INK2)
    d.line([(0, 50), (W, 50)], fill=DIVL, width=1)

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    LX  = 14
    LW  = 268
    RX  = W - 14 - 268
    RPX = W - 14
    GCX = W // 2
    GCY = 275
    GR  = 165

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL IZQUIERDO — CPU
    # ══════════════════════════════════════════════════════════════════════════
    Y = 56

    _rog_badge(d, LX, Y, LX+LW-8, Y+30, "CPU")
    d.rectangle([LX+LW-8, Y, LX+LW+60, Y+30], fill=BLUE_DARK)
    d.line([(LX, Y+31), (LX+LW+60, Y+31)], fill=BLUE, width=2)
    Y += 38

    # Temperatura
    tc_val = f"{ct:.1f}" if ct is not None else "--.-"
    _data_row(d, LX, Y, tc_val, "°C", Fbc(28), _tc(ct))
    _, th = _tw(d, tc_val, Fb(66))
    _dotline(d, LX, Y+th+6, 175, PINK)
    Y += th + 16

    # Frecuencia
    freq_val = f"{freq.current:.1f}" if freq else "---.-"
    _data_row(d, LX, Y, freq_val, "MHz", Fbc(26))
    _, th2 = _tw(d, freq_val, Fb(66))
    _dotline(d, LX, Y+th2+6, 175, PINK)
    Y += th2 + 16

    # Uso %
    cpu_str = f"{cpu:.1f}"
    _data_row(d, LX, Y, cpu_str, " %", Fbc(26), _vc(cpu))
    _, th3 = _tw(d, cpu_str, Fb(66))
    _dotline(d, LX, Y+th3+6, 175, PINK)
    Y += th3 + 14

    d.line([(LX, Y), (LX+LW, Y)], fill=DIVL, width=1)
    Y += 10

    # Storage
    _tri(d, LX, Y+1)
    d.text((LX+14, Y), "Storage Usage", font=Fbc(20), fill=INK2)
    Y += 22
    if disk:
        ds = f"{disk.percent:.0f}"
        dw2, dh2 = _tw(d, ds, Fb(44))
        d.text((LX, Y), ds, font=Fb(44), fill=INK)
        d.text((LX+dw2+4, Y+dh2-20), "%", font=Fbc(20), fill=INK2)
        _dotline(d, LX, Y+dh2+5, 175, PINK)
        Y += dh2 + 14
    else:
        d.text((LX, Y), "N/A", font=Fo(30), fill=INK3)
        Y += 38

    # Refresh Rate
    _tri(d, LX, Y+1)
    d.text((LX+14, Y), "Refresh Rate", font=Fbc(20), fill=INK2)
    Y += 22
    fps_str = f"{hz}" if hz else "60"
    fw2, fh2 = _tw(d, fps_str, Fb(44))
    d.text((LX, Y), fps_str, font=Fb(44), fill=INK)
    d.text((LX+fw2+5, Y+fh2-20), "FPS", font=Fbc(20), fill=INK2)
    _dotline(d, LX, Y+fh2+5, 175, PINK)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL DERECHO — GPU (right-aligned)
    # ══════════════════════════════════════════════════════════════════════════
    Y = 56

    _rog_badge(d, RX+8, Y, RPX, Y+30, "GPU")
    d.rectangle([RX-60, Y, RX+8, Y+30], fill=BLUE_DARK)
    d.line([(RX-60, Y+31), (RPX, Y+31)], fill=BLUE, width=2)
    Y += 38

    # Temp GPU
    gt_str = f"{gt:.1f}" if gt is not None else "--.-"
    _data_row_r(d, RPX, Y, gt_str, "°C", Fbc(30), _tc(gt))
    _, gth = _tw(d, gt_str, Fb(68))
    _dotline(d, RPX-175, Y+gth+6, 175, PINK)
    Y += gth + 16

    # GPU Clock
    clk_str = (f"{gpu_clk:.1f}" if gpu_clk is not None
               else f"{vu*1000:.0f}" if vu is not None else "---.-")
    _data_row_r(d, RPX, Y, clk_str, "MHz", Fbc(28))
    _, clkh = _tw(d, clk_str, Fb(68))
    _dotline(d, RPX-175, Y+clkh+6, 175, PINK)
    Y += clkh + 16

    # GPU Usage
    gpu_pct = gpu if gpu is not None else 0.0
    gpu_str = f"{gpu_pct:.1f}"
    _data_row_r(d, RPX, Y, gpu_str, " %", Fbc(28), _vc(gpu_pct))
    _, gpuh = _tw(d, gpu_str, Fb(68))
    _dotline(d, RPX-175, Y+gpuh+6, 175, PINK)
    Y += gpuh + 14

    d.line([(RX, Y), (RPX, Y)], fill=DIVL, width=1)
    Y += 10

    # Resolution
    _tri_r(d, RPX, Y+1)
    _right(d, RPX-14, Y, "Resolution", Fbc(20), INK2)
    Y += 22
    res_str = f"{res[0]} x {res[1]}" if res else "1920 x 1080"
    _, rh = _tw(d, res_str, Fbc(28))
    _right(d, RPX, Y, res_str, Fbc(28), INK)
    _dotline(d, RPX-175, Y+rh+5, 175, PINK)
    Y += rh + 14

    # VRAM
    _tri_r(d, RPX, Y+1)
    _right(d, RPX-14, Y, "VRAM", Fbc(20), INK2)
    Y += 22
    if vu is not None and vt is not None:
        vram_str = f"{vu:.1f} / {vt:.1f} GB"
        _, vh3 = _tw(d, vram_str, Fbc(24))
        _right(d, RPX, Y, vram_str, Fbc(24), INK)
        _dotline(d, RPX-175, Y+vh3+5, 175, PINK)
    else:
        _right(d, RPX, Y, "N/A", Fbc(24), INK3)

    # ══════════════════════════════════════════════════════════════════════════
    # CENTRO — Gauge RAM
    # ══════════════════════════════════════════════════════════════════════════
    _ram_gauge(d, GCX, GCY, GR, mem.percent, frame)

    ram_used = (mem.total - mem.available) / 1024**3
    ram_tot  = mem.total / 1024**3
    _ctr(d, GCX, GCY + GR + 16, f"{ram_used:.1f} / {ram_tot:.0f} GB", Fm(17), INK3)
    _ctr(d, GCX, GCY + GR + 33, socket.gethostname().upper(), Fr(16), INK3)

    # Líneas decorativas laterales
    gl  = GCX - GR - 18
    gr_ = GCX + GR + 18
    d.line([(LX+LW+6, GCY), (gl,  GCY)], fill=DIVL, width=1)
    d.line([(gr_, GCY), (RX-6, GCY)],    fill=DIVL, width=1)
    d.ellipse([gl-4,  GCY-4, gl+4,  GCY+4], fill=BLUE_DARK, outline=INK3, width=1)
    d.ellipse([gr_-4, GCY-4, gr_+4, GCY+4], fill=BLUE_DARK, outline=INK3, width=1)

    return img
