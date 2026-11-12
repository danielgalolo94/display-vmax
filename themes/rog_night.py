"""
Tema: ROG NIGHT — Gaming HUD estilo ROG / ASUS
Display landscape 960x480
Tres columnas: CPU (izq), RAM gauge circular (centro), GPU (der)
"""
import math, datetime, subprocess, threading, time, socket, json
import psutil
from PIL import Image, ImageDraw, ImageFont, ImageOps

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

Fo  = lambda s: _fnt(_F_ORB, s)   # Orbitron — clock/cabecera
Fb  = lambda s: _fnt(_F_BEB, s)   # Bebas Neue — números grandes
Fbc = lambda s: _fnt(_F_BCO, s)   # Barlow Condensed — unidades/labels
Fmc = lambda s: _fnt(_F_MIC, s)   # Michroma — badges y texto angular
Fr  = lambda s: _fnt(_F_RAJ, s)   # Rajdhani — fallback secundario
Fd  = lambda s: _fnt(_F_DAT, s)
Fm  = lambda s: _fnt(_F_MON, s)
Fn  = lambda s: _fnt(_F_NRD, s)

# ── Paleta ROG ────────────────────────────────────────────────────────────────
BG        = (5,   6,  14)
GRID_DOT  = (16,  18,  34)
INK       = (238, 243, 255)
INK2      = (148, 162, 200)
INK3      = (58,   66, 106)
BLUE      = (30,  130, 255)
BLUE_DARK = (12,   48, 130)
BLUE_DIM  = (18,   24,  52)
PINK      = (210,  28, 195)
PINK2     = (255,  70, 230)
CY        = (0,   200, 248)
GRN       = (18,  218, 108)
ORG       = (255, 128,  18)
WARN      = (255, 175,  10)
CRIT      = (245,  48,  48)
TRACK     = (16,   20,  42)
DIVL      = (22,   26,  50)

# ── Sensores (portados de phantom_night) ─────────────────────────────────────
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

# Monitor info (cached)
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

def _tri(d, x, y, col=BLUE):
    d.polygon([(x, y+6), (x+10, y+2), (x+10, y+10)], fill=col)

def _tri_r(d, rx, y, col=BLUE):
    d.polygon([(rx, y+2), (rx, y+10), (rx-10, y+6)], fill=col)

def _data_row_r(d, rx, y, value_str, unit_str, unit_font, col=INK):
    vf = Fb(68)
    uf = unit_font
    vw, vh = _tw(d, value_str, vf)
    uw, uh = _tw(d, unit_str, uf)
    ux = rx - uw
    vx = ux - 5 - vw
    for off in [(2,0),(-2,0),(0,2),(0,-2)]:
        d.text((vx+off[0], y+off[1]), value_str, font=vf,
               fill=tuple(min(255,c//5) for c in col))
    d.text((vx, y), value_str, font=vf, fill=INK)
    d.text((ux, y+vh-uh-4), unit_str, font=uf, fill=INK2)
    return vh

# ── Badge estilo ROG con rayas diagonales ─────────────────────────────────────
def _rog_badge(d, x1, y1, x2, y2, text):
    h = y2 - y1
    w = x2 - x1
    d.rectangle([x1, y1, x2, y2], fill=BLUE)
    # Diagonal stripes clipped to badge
    stripe = tuple(max(0, c - 55) for c in BLUE)
    for i in range(-h, w + h, 10):
        lx1 = x1 + i
        lx2 = x1 + i + h
        ly1, ly2 = y1, y2
        if lx1 < x1:
            ratio = (x1 - lx1) / max(h, 1)
            ly1 = int(y1 + ratio * h)
            lx1 = x1
        if lx2 > x2:
            ratio = (lx2 - x2) / max(h, 1)
            ly2 = int(y2 - ratio * h)
            lx2 = x2
        if lx1 < x2 and lx2 > x1:
            d.line([(lx1, ly1), (lx2, ly2)], fill=stripe, width=4)
    d.text((x1+10, y1 + (h-20)//2), text, font=Fbc(26), fill=INK)

# ── Gauge circular RAM ────────────────────────────────────────────────────────
def _ram_gauge(d, cx, cy, r, pct, frame):
    # Glow exterior muy sutil
    for gr in range(r+28, r+5, -4):
        intensity = max(0, 22 - (gr - r))
        d.ellipse([cx-gr, cy-gr, cx+gr, cy+gr],
                  outline=(0, intensity//2, intensity*2), width=1)

    # Tick marks exteriores (60 marcas)
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

    # Anillo de segmentos exteriores (36 segmentos = progreso)
    N_SEGS = 36
    r_arc  = r - 22
    filled = int(N_SEGS * pct / 100)
    for i in range(N_SEGS):
        sa = -90 + i * 360/N_SEGS
        ea = sa + 360/N_SEGS - 2.5
        col = BLUE if i < filled else BLUE_DIM
        # Glow para segmentos llenos
        if i < filled and i == filled - 1:
            d.arc([cx-r_arc-4, cy-r_arc-4, cx+r_arc+4, cy+r_arc+4],
                  start=sa, end=ea, fill=tuple(min(255,c//2) for c in BLUE), width=18)
        d.arc([cx-r_arc, cy-r_arc, cx+r_arc, cy+r_arc],
              start=sa, end=ea, fill=col, width=14)

    # Arco rosa de progreso en exterior
    if pct > 1:
        arc_end = -90 + 360 * pct / 100
        d.arc([cx-(r+16), cy-(r+16), cx+(r+16), cy+(r+16)],
              start=-90, end=arc_end, fill=PINK, width=3)
        # Punto de punta
        tip_a = math.radians(arc_end)
        tx = cx + (r+16) * math.cos(tip_a)
        ty = cy + (r+16) * math.sin(tip_a)
        d.ellipse([tx-5, ty-5, tx+5, ty+5], fill=PINK2)

    # Indicador superior (triángulo)
    d.polygon([(cx, cy-r-20), (cx-6, cy-r-8), (cx+6, cy-r-8)], fill=BLUE)

    # Anillo interior de aspas (24 segmentos)
    N_BLADES = 24
    r_blade  = r_arc - 20
    filled_b = int(N_BLADES * pct / 100)
    for i in range(N_BLADES):
        sa = -90 + i * 360/N_BLADES
        ea = sa + 360/N_BLADES - 3
        col = BLUE if i < filled_b else (14, 17, 36)
        d.arc([cx-r_blade, cy-r_blade, cx+r_blade, cy+r_blade],
              start=sa, end=ea, fill=col, width=16)

    # Círculo central (fondo oscuro)
    r_center = r_blade - 20
    d.ellipse([cx-r_center, cy-r_center, cx+r_center, cy+r_center], fill=(6, 7, 17))

    # Anillo pulsante animado
    pulse = 0.5 + 0.5 * math.sin(frame * 0.07)
    pr = int(r_center - 6 - pulse * 6)
    d.ellipse([cx-pr, cy-pr, cx+pr, cy+pr],
              outline=(0, int(BLUE[1]*pulse*0.4), int(BLUE[2]*pulse*0.4)), width=1)

    # Número central (porcentaje)
    pct_str = f"{pct:.0f}"
    pfont   = Fb(80)
    pw, ph  = _tw(d, pct_str, pfont)
    # Glow del número
    for off in [(3,0),(-3,0),(0,3),(0,-3),(2,2),(-2,-2)]:
        d.text((cx-pw//2+off[0], cy-ph//2-6+off[1]), pct_str,
               font=pfont, fill=(0, 45, 110))
    d.text((cx-pw//2, cy-ph//2-6), pct_str, font=pfont, fill=INK)
    d.text((cx+pw//2+3, cy-ph//2+12), "%", font=Fbc(22), fill=INK2)

    # Etiquetas centro
    _ctr(d, cx, cy+ph//2+10, "RAM Usage", Fbc(18), INK2)
    _ctr(d, cx, cy-ph//2-26, "MEMORY", Fmc(13), INK3)

    # Barra de RAM inferior pequeña
    ram_bar_w = r_center * 2 - 20
    bx = cx - ram_bar_w//2
    by = cy + ph//2 + 34
    d.rectangle([bx, by, bx+ram_bar_w, by+5], fill=TRACK)
    fw = int(ram_bar_w * pct / 100)
    if fw > 0:
        d.rectangle([bx, by, bx+fw, by+5], fill=BLUE)


# ── Bloque de dato grande (temp, freq, usage) ─────────────────────────────────
def _data_row(d, x, y, value_str, unit_str, unit_font, col=INK):
    vf = Fb(66)
    uf = unit_font
    vw, vh = _tw(d, value_str, vf)
    # Glow sutil
    for off in [(2,0),(-2,0),(0,2),(0,-2)]:
        d.text((x+off[0], y+off[1]), value_str, font=vf,
               fill=tuple(min(255,c//5) for c in col))
    d.text((x, y), value_str, font=vf, fill=INK)
    d.text((x+vw+5, y+vh-_tw(d, unit_str, uf)[1]-4), unit_str, font=uf, fill=INK2)
    return vh


# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    # Grilla de puntos sutil
    for gx in range(0, W, 22):
        for gy in range(0, H, 22):
            d.point((gx, gy), fill=GRID_DOT)

    # ── Leer sensores ─────────────────────────────────────────────────────────
    cores = _cores()
    cpu   = sum(cores)/len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gpu   = _gpu()
    gt    = _gtemp()
    disk, disk_mount = _disk()
    freq  = _freq()
    vu, vt = _vram()
    gpu_clk = _gpu_clock()
    res, hz = _monitor_info()
    now   = datetime.datetime.now()

    # ── CABECERA: hora (izq) y fecha (der) ────────────────────────────────────
    ts = now.strftime("%H:%M:%S")
    d.text((14, 8), ts, font=Fb(42), fill=INK)
    # Pequeña línea blue debajo del reloj
    tw_ts, _ = _tw(d, ts, Fb(42))
    d.line([(14, 42), (14+tw_ts, 42)], fill=BLUE, width=2)

    date_str = now.strftime("%Y/%m/%d")
    _right(d, W-14, 8, date_str, Fbc(22), INK2)

    # Separador horizontal sutil
    d.line([(0, 50), (W, 50)], fill=DIVL, width=1)

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    LX  = 14           # margen izquierdo
    LW  = 268          # ancho panel izquierdo
    RX  = W-14-268     # inicio panel derecho = 678
    RPX = W-14          # borde derecho del panel GPU = 946
    GCX = W//2         # centro gauge = 480
    GCY = 275          # centro gauge Y
    GR  = 165          # radio gauge

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL IZQUIERDO — CPU
    # ══════════════════════════════════════════════════════════════════════════
    Y = 56

    # Badge CPU
    _rog_badge(d, LX, Y, LX+LW-8, Y+30, "CPU")
    # Barra azul horizontal desde badge hasta borde
    d.rectangle([LX+LW-8, Y, LX+LW+60, Y+30], fill=BLUE_DARK)
    d.line([(LX, Y+31), (LX+LW+60, Y+31)], fill=BLUE, width=2)

    Y += 38

    # Temperatura CPU
    tc_val = f"{ct:.1f}" if ct is not None else "--.-"
    tc_col = _tc(ct)
    _data_row(d, LX, Y, tc_val, "°C", Fbc(28), tc_col)
    _, th = _tw(d, tc_val, Fb(66))
    _dotline(d, LX, Y+th+6, 175, PINK)

    Y += th + 16

    # Frecuencia CPU
    freq_val = f"{freq.current:.1f}" if freq else "---.-"
    _data_row(d, LX, Y, freq_val, "MHz", Fbc(26))
    _, th2 = _tw(d, freq_val, Fb(66))
    _dotline(d, LX, Y+th2+6, 175, PINK)

    Y += th2 + 16

    # Uso CPU %
    cpu_str = f"{cpu:.1f}"
    cc = _vc(cpu)
    _data_row(d, LX, Y, cpu_str, " %", Fbc(26), cc)
    _, th3 = _tw(d, cpu_str, Fb(66))
    _dotline(d, LX, Y+th3+6, 175, PINK)

    Y += th3 + 14

    # Divisor
    d.line([(LX, Y), (LX+LW, Y)], fill=DIVL, width=1)
    Y += 10

    # Storage Usage
    _tri(d, LX, Y+1)
    d.text((LX+14, Y), "Storage Usage", font=Fbc(20), fill=INK2)
    Y += 22
    if disk:
        ds = f"{disk.percent:.0f}"
        dw, dh = _tw(d, ds, Fb(44))
        d.text((LX, Y), ds, font=Fb(44), fill=INK)
        d.text((LX+dw+4, Y+dh-20), "%", font=Fbc(20), fill=INK2)
        _dotline(d, LX, Y+dh+5, 175, PINK)
        Y += dh + 14
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
    # PANEL DERECHO — GPU (right-aligned, fuentes +1pt)
    # ══════════════════════════════════════════════════════════════════════════
    Y = 56

    # Badge GPU (borde izquierdo del badge toca la zona central)
    _rog_badge(d, RX+8, Y, RPX, Y+30, "GPU")
    d.rectangle([RX-60, Y, RX+8, Y+30], fill=BLUE_DARK)
    d.line([(RX-60, Y+31), (RPX, Y+31)], fill=BLUE, width=2)

    Y += 38

    # Temperatura GPU — right-aligned, Fr(27) = +1pt vs "°C", Fbc(28)
    gt_str = f"{gt:.1f}" if gt is not None else "--.-"
    gtc    = _tc(gt)
    _data_row_r(d, RPX, Y, gt_str, "°C", Fbc(30), gtc)
    _, gth = _tw(d, gt_str, Fb(68))
    _dotline(d, RPX-175, Y+gth+6, 175, PINK)

    Y += gth + 16

    # GPU Clock (MHz) — right-aligned, Fr(23) = +1pt vs Fr(24)
    if gpu_clk is not None:
        clk_str = f"{gpu_clk:.1f}"
    elif vu is not None:
        clk_str = f"{vu*1000:.0f}"
    else:
        clk_str = "---.-"
    _data_row_r(d, RPX, Y, clk_str, "MHz", Fbc(28))
    _, clkh = _tw(d, clk_str, Fb(68))
    _dotline(d, RPX-175, Y+clkh+6, 175, PINK)

    Y += clkh + 16

    # GPU Usage % — right-aligned
    gpu_pct = gpu if gpu is not None else 0.0
    gpu_str = f"{gpu_pct:.1f}"
    gc = _vc(gpu_pct)
    _data_row_r(d, RPX, Y, gpu_str, " %", Fbc(28), gc)
    _, gpuh = _tw(d, gpu_str, Fb(68))
    _dotline(d, RPX-175, Y+gpuh+6, 175, PINK)

    Y += gpuh + 14

    # Divisor
    d.line([(RX, Y), (RPX, Y)], fill=DIVL, width=1)
    Y += 10

    # Resolution — right-aligned, Fr(19) = +1pt vs Fr(20)
    _tri_r(d, RPX, Y+1)
    _right(d, RPX-14, Y, "Resolution", Fbc(20), INK2)
    Y += 22
    res_str = f"{res[0]} x {res[1]}" if res else "1920 x 1080"
    _, rh = _tw(d, res_str, Fbc(28))
    _right(d, RPX, Y, res_str, Fbc(28), INK)
    _dotline(d, RPX-175, Y+rh+5, 175, PINK)

    Y += rh + 14

    # VRAM — right-aligned, Fr(23) = +1pt vs Fr(24)
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

    # Info RAM bajo el gauge
    ram_used = (mem.total - mem.available) / 1024**3
    ram_tot  = mem.total / 1024**3
    info_str = f"{ram_used:.1f} / {ram_tot:.0f} GB"
    _ctr(d, GCX, GCY + GR + 16, info_str, Fm(17), INK3)
    _ctr(d, GCX, GCY + GR + 33, socket.gethostname().upper(), Fr(16), INK3)

    # Decoración: líneas laterales al gauge
    gl = GCX - GR - 18
    gr_ = GCX + GR + 18
    d.line([(LX+LW+6, GCY), (gl, GCY)], fill=DIVL, width=1)
    d.line([(gr_, GCY), (RX-6, GCY)], fill=DIVL, width=1)
    d.ellipse([gl-4, GCY-4, gl+4, GCY+4], fill=BLUE_DARK, outline=INK3, width=1)
    d.ellipse([gr_-4, GCY-4, gr_+4, GCY+4], fill=BLUE_DARK, outline=INK3, width=1)

    return img
