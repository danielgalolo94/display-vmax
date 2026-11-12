"""
Tema: MARK 50 — F.R.I.D.A.Y. Arc Reactor HUD
Display landscape 960x480
Estética Iron Man Mark L (Infinity War): arc reactor naranja/dorado,
panal hexagonal, triple gauge radial (CPU/GPU/RAM), barras por núcleo.
"""
import math, datetime, subprocess, socket, os, random
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

_F_ORB = os.path.join(_FD, "Orbitron-Bold.ttf")
_F_OBK = os.path.join(_FD, "Orbitron-Black.ttf")
_F_TKO = os.path.join(_FD, "Teko-Medium.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_DAT = os.path.join(_FD, "NotoSansMono-Bold.ttf")
_F_MON = os.path.join(_FD, "ShareTechMono.ttf")

_FC = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(p, s)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Fo = lambda s: _fnt(_F_ORB, s)
Fb = lambda s: _fnt(_F_OBK, s)
Ft = lambda s: _fnt(_F_TKO, s)
Fr = lambda s: _fnt(_F_RAJ, s)
Fd = lambda s: _fnt(_F_DAT, s)
Fm = lambda s: _fnt(_F_MON, s)

# ── Paleta MARK 50 — arc reactor cálido ───────────────────────────────────────
BG    = (14,  8,   3)
BG2   = (8,   5,   2)
GOLD  = (255, 176, 38)
GOLD2 = (255, 122, 12)
AMBER = (255, 210, 110)
HOT   = (255, 90,  20)
EMBER = (120, 55,  12)
EMBER2= (60,  28,  8)
WHITE = (255, 238, 210)
INK   = (235, 195, 140)
INK2  = (180, 130, 70)
INK3  = (95,  62,  28)
DIVL  = (55,  32,  12)
TRACK = (40,  24,  10)
CYAN  = (90,  210, 255)
GREEN = (90,  220, 120)
WARN  = (255, 170, 30)
RED   = (255, 70,  50)

# ── Sensores ──────────────────────────────────────────────────────────────────
def _cores():
    try:    return psutil.cpu_percent(percpu=True, interval=None)
    except: return [0.0] * 4

def _mem():  return psutil.virtual_memory()

def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal', 'acpitz']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _gpu():
    for card in ['card0', 'card1']:
        try:
            r = subprocess.run(['cat', f'/sys/class/drm/{card}/device/gpu_busy_percent'],
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
    for m in ['/home', '/']:
        try: return psutil.disk_usage(m), m
        except: pass
    return None, '/'

def _freq():
    try:    return psutil.cpu_freq()
    except: return None

def _fan():
    try:
        f = psutil.sensors_fans()
        for v in f.values():
            if v: return int(v[0].current)
    except: pass
    return None

def _vram():
    for card in ['card0', 'card1']:
        try:
            u = int(open(f'/sys/class/drm/{card}/device/mem_info_vram_used').read().strip())
            t = int(open(f'/sys/class/drm/{card}/device/mem_info_vram_total').read().strip())
            return u / 1024**3, t / 1024**3
        except: pass
    return None, None

_HN  = socket.gethostname()[:14]
_nt  = [0, 0]
_ntx = [0] * 40
_nrx = [0] * 40

def _update_net():
    global _nt, _ntx, _nrx
    try:
        c = psutil.net_io_counters()
        tx, rx = c.bytes_sent, c.bytes_recv
        pt, pr = _nt
        if pt:
            _ntx = _ntx[1:] + [max(0, tx - pt)]
            _nrx = _nrx[1:] + [max(0, rx - pr)]
        _nt = [tx, rx]
    except: pass

def _fmt(b):
    if b > 1_000_000: return f"{b/1_000_000:.1f}M"
    if b > 1_000:     return f"{b/1_000:.0f}K"
    return f"{int(b)}B"

# chispas de arc reactor derivan hacia arriba lentamente
_RNG   = random.Random(51)
_SPARKS = [(int(_RNG.random()*W), int(_RNG.random()*H),
            (_RNG.random()-0.5)*0.6, -(_RNG.random()*0.8+0.2),
            int(_RNG.random()*2)+1, int(_RNG.random()*628))
           for _ in range(60)]

def _vc(v):
    if v < 70: return GOLD
    if v < 90: return WARN
    return RED

def _tc(t):
    if t is None: return INK2
    if t < 65:   return CYAN
    if t < 80:   return WARN
    return RED

# ── Primitivas ────────────────────────────────────────────────────────────────
def _ctr(d, cx, y, txt, font, fill):
    bb = d.textbbox((0, 0), txt, font=font)
    d.text((cx - (bb[2]-bb[0])//2, y), txt, font=font, fill=fill)

def _right(d, rx, y, txt, font, fill):
    bb = d.textbbox((0, 0), txt, font=font)
    d.text((rx - (bb[2]-bb[0]), y), txt, font=font, fill=fill)

def _hbar(d, x, y, w, h, pct, col):
    d.rectangle([x, y, x+w, y+h], fill=TRACK)
    fw = int(pct / 100 * w)
    if fw < 1: return
    for i in range(fw):
        t = 0.3 + 0.7 * (i / max(fw, 1))
        d.line([(x+i, y), (x+i, y+h)],
               fill=(min(255, int(col[0]*t)), min(255, int(col[1]*t)), min(255, int(col[2]*t))))
    d.line([(x+fw-1, y), (x+fw-1, y+h)], fill=WHITE, width=1)

def _sparkline(d, x, y, w, h, data, col):
    if not any(data): return
    mx = max(data) or 1
    n  = len(data)
    pts = [(x + int(i*w/(n-1)), y+h - int(v/mx*h)) for i, v in enumerate(data)]
    if len(pts) > 1: d.line(pts, fill=col, width=1)

def _glow(d, x, y, txt, size, col, fn=None):
    f   = (fn or Ft)(size)
    dim = tuple(c // 4 for c in col)
    for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
        d.text((x+dx, y+dy), txt, font=f, fill=dim)
    d.text((x, y), txt, font=f, fill=col)

def _corner_bracket(d, x, y, w, h, col, L=12, g=2):
    segs = [
        (x,y,x+L,y),(x,y,x,y+L),
        (x+w-L,y,x+w,y),(x+w,y,x+w,y+L),
        (x,y+h-L,x,y+h),(x,y+h,x+L,y+h),
        (x+w-L,y+h,x+w,y+h),(x+w,y+h-L,x+w,y+h),
    ]
    gc = tuple(min(255, c//3) for c in col)
    for x1,y1,x2,y2 in segs:
        d.line([(x1,y1),(x2,y2)], fill=gc, width=g+2)
    for x1,y1,x2,y2 in segs:
        d.line([(x1,y1),(x2,y2)], fill=col, width=g)

def _section(d, x, y, w, label, col):
    d.rectangle([x, y, x+4, y+24], fill=col)
    d.rectangle([x+4, y, x+8, y+24], fill=tuple(c//4 for c in col))
    d.text((x+12, y+2), label, font=Fr(24), fill=col)
    d.line([(x+8, y+26), (x+w, y+26)], fill=DIVL, width=1)

# ── Fondo: panal hexagonal ─────────────────────────────────────────────────────
def _hex_bg(d):
    R   = 22
    col = (22, 14, 7)
    SQ3 = math.sqrt(3)
    cw  = SQ3 * R
    ch  = 1.5 * R
    cols_n = int(W / cw) + 3
    rows_n = int(H / ch) + 3
    for row in range(-1, rows_n):
        for ci in range(-1, cols_n):
            cx_ = ci * cw + (row % 2) * cw / 2
            cy_ = row * ch
            pts = [(cx_ + R * math.cos(math.radians(30 + 60*i)),
                    cy_ + R * math.sin(math.radians(30 + 60*i)))
                   for i in range(6)]
            d.polygon(pts, outline=col, fill=None)

# ── Triple gauge radial ────────────────────────────────────────────────────────
def _gauge(d, cx, cy, r, val, col, label, sub, frame, sd=1):
    S, SPAN = -215, 250
    AW = 13

    # anillo exterior giratorio
    a_s = int((frame * 0.55 * sd) % 360)
    d.arc([cx-r-7, cy-r-7, cx+r+7, cy+r+7],
          start=a_s, end=a_s+80,
          fill=tuple(c//5 for c in col), width=1)
    d.arc([cx-r-7, cy-r-7, cx+r+7, cy+r+7],
          start=(a_s+180)%360, end=(a_s+260)%360,
          fill=tuple(c//5 for c in col), width=1)

    # anillo estático tenue
    d.arc([cx-r-2, cy-r-2, cx+r+2, cy+r+2], start=0, end=360,
          fill=tuple(c//10 for c in col), width=1)

    # pista
    d.arc([cx-r, cy-r, cx+r, cy+r], start=S, end=S+SPAN,
          fill=TRACK, width=AW)

    # arco de valor
    arc_v = int(SPAN * max(val, 2) / 100)
    halo  = tuple(c//3 for c in col)
    d.arc([cx-r-4, cy-r-4, cx+r+4, cy+r+4],
          start=S, end=S+arc_v, fill=halo, width=AW+10)
    d.arc([cx-r-1, cy-r-1, cx+r+1, cy+r+1],
          start=S, end=S+arc_v, fill=col, width=AW+2)
    d.arc([cx-r, cy-r, cx+r, cy+r],
          start=S, end=S+arc_v, fill=col, width=AW)

    # punta del arco
    ta  = math.radians(S + arc_v)
    tx2 = cx + r * math.cos(ta)
    ty2 = cy + r * math.sin(ta)
    d.ellipse([tx2-6, ty2-6, tx2+6, ty2+6], fill=halo)
    d.ellipse([tx2-3, ty2-3, tx2+3, ty2+3], fill=col)

    # ticks
    for i in range(11):
        a   = math.radians(S + SPAN*i/10)
        big = (i % 5 == 0)
        r1  = r - (9 if big else 4)
        x1, y1 = cx + r1*math.cos(a), cy + r1*math.sin(a)
        x2, y2 = cx + (r+1)*math.cos(a), cy + (r+1)*math.sin(a)
        tc_ = INK3 if big else tuple(c//8 for c in col)
        d.line([(x1,y1),(x2,y2)], fill=tc_, width=(2 if big else 1))

    # círculo interior
    IR = r - AW - 5
    d.ellipse([cx-IR, cy-IR, cx+IR, cy+IR], fill=BG2)

    # número
    vs = f"{val:.0f}"
    vf = Fb(36)
    bb = d.textbbox((0, 0), vs, font=vf)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    vx = cx - tw//2 - bb[0]
    vy = cy - th//2 - bb[1] - 6
    dim2 = tuple(c//5 for c in col)
    for dx2, dy2 in [(2,2),(-2,2),(2,-2),(-2,-2)]:
        d.text((vx+dx2, vy+dy2), vs, font=vf, fill=dim2)
    d.text((vx, vy), vs, font=vf, fill=WHITE)
    _ctr(d, cx, vy+th+1, "%", Fr(16), col)

    # etiqueta inferior
    _ctr(d, cx, cy+IR-15, label, Fm(13), col)
    if sub:
        _ctr(d, cx, cy+IR-2, sub, Fm(11), INK3)

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    if frame % 2 == 0:
        _update_net()

    cores    = _cores()
    cpu      = sum(cores) / len(cores) if cores else 0.0
    mem      = _mem()
    ct       = _temp()
    gpu      = _gpu()
    gt       = _gtemp()
    disk, _  = _disk()
    freq     = _freq()
    fan      = _fan()
    vu, vt   = _vram()
    now      = datetime.datetime.now()
    la       = os.getloadavg()
    tx_v     = _ntx[-1] if _ntx else 0
    rx_v     = _nrx[-1] if _nrx else 0
    uptime   = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um   = divmod(int(uptime.total_seconds()) // 60, 60)

    img = Image.new('RGB', (W, H), BG2)
    d   = ImageDraw.Draw(img)

    # fondo hexagonal
    _hex_bg(d)

    # chispas de arc reactor
    for px_, py_, vx_, vy_, sz_, ph in _SPARKS:
        x_ = int(px_ + frame * vx_) % W
        y_ = int(py_ + frame * vy_) % H
        bright = 38 + int(28 * math.sin(frame * 0.06 + ph * 0.01))
        d.ellipse([x_-sz_, y_-sz_, x_+sz_, y_+sz_],
                  fill=(bright, bright//3, 0))

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    TB = 52
    d.rectangle([0, 0, W, TB], fill=(10, 6, 2))
    d.line([(0, TB-2), (W, TB-2)], fill=EMBER2, width=1)
    d.line([(0, TB-1), (W, TB-1)], fill=GOLD2,  width=2)

    blink = (frame % 10) < 6
    d.ellipse([12, TB//2-7, 24, TB//2+5], fill=GOLD if blink else EMBER)
    d.text((30, 7),       "F.R.I.D.A.Y.",   font=Fo(22), fill=GOLD)
    d.text((30, TB//2+9), "MARK L  ONLINE" if blink else "MARK L  ·····",
           font=Fm(15), fill=GOLD2 if blink else INK3)

    _ctr(d, W//2, 2,        now.strftime("%H:%M:%S"),         Fb(42), WHITE)
    _ctr(d, W//2, TB//2+14, now.strftime("%a %d %b %Y").upper(), Fr(17), INK2)

    _right(d, W-12, 7,        _HN.upper(),   Fo(19), AMBER)
    _right(d, W-12, TB//2+11, "STARK TECH", Fm(14), INK3)

    # ── CONSTANTES DE LAYOUT ──────────────────────────────────────────────────
    BB   = H - 28
    LX, LW = 8, 182
    RX, RW = W - 8 - 182, 182          # 770..952
    MX   = LX + LW + 4                 # 194
    MW   = RX - MX - 4                 # 572

    # ── TRIPLE GAUGE ──────────────────────────────────────────────────────────
    GR   = 76
    GCY  = TB + GR + 28                # 156
    G1X  = MX + MW // 6               # ~289
    G2X  = MX + MW // 2               # 480
    G3X  = MX + MW * 5 // 6           # ~670

    _gauge(d, G1X, GCY, GR, cpu,
           GOLD, "CPU",
           f"{ct:.0f}°C" if ct else None,
           frame, 1)
    _gauge(d, G2X, GCY, GR,
           gpu if gpu is not None else 0,
           HOT  if gpu is not None else INK3,
           "GPU",
           f"{gt:.0f}°C" if gt else ("N/A" if gpu is None else None),
           frame, -1)
    _gauge(d, G3X, GCY, GR, mem.percent,
           AMBER, "RAM",
           f"{(mem.total-mem.available)/1024**3:.1f}G",
           frame, 1)

    # líneas conector entre gauges
    for x1c, x2c in [(G1X+GR+6, G2X-GR-6), (G2X+GR+6, G3X-GR-6)]:
        d.line([(x1c, GCY), (x2c, GCY)], fill=DIVL, width=1)
        d.ellipse([x1c-3, GCY-3, x1c+3, GCY+3], fill=INK3)
        d.ellipse([x2c-3, GCY-3, x2c+3, GCY+3], fill=INK3)

    # texto de estado
    SY = GCY + GR + 14
    _ctr(d, MX+MW//2, SY,    "SYSTEM INTEGRITY · NOMINAL",      Fm(16), INK3)
    _ctr(d, MX+MW//2, SY+20, now.strftime("PROTOCOL ACTIVE  ·  %d/%m/%Y"), Fr(17), INK3)

    # barras por núcleo
    CY_Y = SY + 46
    nc   = len(cores)
    bw   = max(8, min(16, (MW - 24) // max(nc, 1)))
    total_bw = nc * bw + (nc - 1) * 2
    bx_s = MX + (MW - total_bw) // 2
    for i, cv in enumerate(cores):
        bx_i = bx_s + i * (bw + 2)
        bh   = max(4, int(40 * cv / 100))  # mínimo 4px visible en todos los cores
        cc   = GOLD if cv < 70 else WARN if cv < 90 else RED
        d.rectangle([bx_i, CY_Y+40-bh, bx_i+bw, CY_Y+40],
                    fill=tuple(c//4 for c in cc))
        d.rectangle([bx_i, CY_Y+40-bh, bx_i+bw, CY_Y+40-bh+2], fill=cc)
    _ctr(d, MX+MW//2, CY_Y+44, f"PER-CORE  {nc} THREADS", Fm(12), INK3)

    # sparkline de red al centro bajo
    NSY = CY_Y + 62
    if NSY + 50 < BB:
        _sparkline(d, MX+10, NSY,    MW-20, 24, _ntx[-40:], GOLD2)
        _sparkline(d, MX+10, NSY,    MW-20, 24, _nrx[-40:], INK3)
        d.line([(MX+10, NSY+24), (MX+MW-10, NSY+24)], fill=DIVL, width=1)
        d.text((MX+12, NSY+28),  f"↑ {_fmt(tx_v)}/s", font=Fm(14), fill=GOLD2)
        _right(d, MX+MW-12, NSY+28, f"↓ {_fmt(rx_v)}/s", Fm(14), INK3)

    # ── PANEL IZQUIERDO ───────────────────────────────────────────────────────
    py = TB + 4

    # CPU
    _section(d, LX, py, LW, "CPU STATUS", GOLD)
    py += 30
    cc = _vc(cpu)
    _glow(d, LX+8, py, f"{cpu:.0f}", 64, cc, Ft)
    if ct is not None:
        _right(d, LX+LW-4, py+4, f"{ct:.0f}°C", Fd(22), _tc(ct))
    if freq:
        d.text((LX+8, py+66), f"{freq.current/1000:.2f}", font=Fo(26), fill=AMBER)
        d.text((LX+8+88, py+72), "GHz", font=Fr(20), fill=INK2)
    _hbar(d, LX+8, py+96, LW-16, 10, cpu, cc)
    py += 112

    # MEMORIA
    _section(d, LX, py, LW, "MEMORY", AMBER)
    py += 30
    ram_ = (mem.total - mem.available) / 1024**3
    tot_ = mem.total / 1024**3
    _glow(d, LX+8, py, f"{ram_:.1f}G", 58, _vc(mem.percent), Ft)
    _right(d, LX+LW-4, py+16, f"/{tot_:.0f}G", Fr(22), INK2)
    _hbar(d, LX+8, py+66, LW-16, 10, mem.percent, AMBER)
    d.text((LX+8, py+80), f"{mem.percent:.0f}%  avail: {mem.available/1024**3:.1f}G",
           font=Fm(15), fill=INK3)
    py += 100

    # LOAD
    _section(d, LX, py, LW, "LOAD AVG", INK2)
    py += 30
    nc2 = psutil.cpu_count() or 4
    lc  = GREEN if la[0] < nc2*0.7 else WARN if la[0] < nc2 else RED
    d.text((LX+8,  py),    f"{la[0]:.2f}", font=Fo(28), fill=lc)
    d.text((LX+8,  py+34), f"5m:{la[1]:.2f}  15m:{la[2]:.2f}", font=Fm(15), fill=INK3)
    d.text((LX+8,  py+54), f"{len(psutil.pids())} procs", font=Fm(15), fill=INK3)
    py += 76

    # RED
    _section(d, LX, py, LW, "NETWORK", EMBER)
    py += 30
    d.text((LX+8, py),    f"UP  {_fmt(tx_v)}/s", font=Fd(18), fill=GOLD)
    d.text((LX+8, py+22), f"DL  {_fmt(rx_v)}/s", font=Fd(18), fill=INK2)
    _sparkline(d, LX+8, py+46, LW-16, 22, _ntx[-20:], GOLD2)

    # ── PANEL DERECHO ─────────────────────────────────────────────────────────
    py = TB + 4

    # GPU
    _section(d, RX, py, RW, "GPU", HOT)
    py += 30
    if gpu is not None:
        _glow(d, RX+8, py, f"{gpu:.0f}", 64, _vc(gpu), Ft)
        if gt is not None:
            _right(d, RX+RW-4, py+4, f"{gt:.0f}°C", Fd(22), _tc(gt))
        _hbar(d, RX+8, py+96, RW-16, 10, gpu, HOT)
        if vu is not None:
            d.text((RX+8, py+110), f"VRAM {vu:.1f}/{vt:.0f}G", font=Fm(16), fill=INK2)
        py += 128
    else:
        d.text((RX+8, py+20), "--", font=Ft(60), fill=INK3)
        py += 82

    # DISCO
    _section(d, RX, py, RW, "STORAGE", GOLD2)
    py += 30
    if disk:
        dc  = _vc(disk.percent)
        dg_ = disk.used / 1024**3
        dt_ = disk.total / 1024**3
        _glow(d, RX+8, py, f"{disk.percent:.0f}%", 52, dc, Ft)
        _right(d, RX+RW-4, py+16, f"{dg_:.0f}/{dt_:.0f}G", Fr(20), INK2)
        _hbar(d, RX+8, py+64, RW-16, 10, disk.percent, GOLD)
        d.text((RX+8, py+78), f"free: {dt_-dg_:.0f}G", font=Fm(15), fill=INK3)
        py += 98
    else:
        py += 30

    # THERMAL / FAN
    _section(d, RX, py, RW, "THERMAL", GOLD)
    py += 30
    if fan is not None:
        fc = CYAN if fan < 2500 else WARN if fan < 3500 else RED
        d.text((RX+8, py),    str(fan), font=Fo(30), fill=fc)
        d.text((RX+8, py+36), "RPM",   font=Fr(22), fill=INK3)
    elif ct is not None:
        d.text((RX+8, py),    f"{ct:.1f}", font=Fo(30), fill=_tc(ct))
        d.text((RX+8, py+36), "°C  CPU", font=Fr(22), fill=INK3)
    else:
        d.text((RX+8, py), "N/A", font=Fm(20), fill=INK3)
    py += 68

    # UPTIME (inline al final de THERMAL, no sección separada)
    d.text((RX+8, py), f"UP: {uh}h {um:02d}m", font=Fm(15), fill=INK3)
    d.text((RX+8, py+18), f"LOAD {la[0]:.2f}", font=Fm(15), fill=INK3)

    # ── BOTTOM BAR ────────────────────────────────────────────────────────────
    d.rectangle([0, BB, W, H], fill=(10, 6, 2))
    d.line([(0, BB),   (W, BB)],   fill=EMBER2, width=1)
    d.line([(0, BB+1), (W, BB+1)], fill=(6, 4, 1), width=1)

    bblink = GREEN if (frame % 12) < 8 else DIVL
    d.ellipse([8, BB+6, 18, BB+18], fill=bblink)
    d.text((24, BB+2), "ONLINE", font=Fm(17), fill=INK if bblink == GREEN else INK3)

    _sparkline(d, 88, BB+3, 100, 22, _ntx[-20:], GOLD2)
    d.text((194, BB+3),  f"↑{_fmt(tx_v)}", font=Fm(15), fill=GOLD2)
    d.text((194, BB+14), f"↓{_fmt(rx_v)}", font=Fm(15), fill=INK3)

    _right(d, W-10, BB+2,
           f"UP {uh}h{um:02d}m  LOAD {la[0]:.2f}  {len(psutil.pids())}p",
           Fm(15), INK3)

    # ── SCANLINE cálido ────────────────────────────────────────────────────────
    sy = TB + (frame * 2) % max(BB - TB, 1)
    d.line([(0, sy), (W, sy)], fill=(32, 16, 5), width=1)

    # ── CORNER BRACKETS ────────────────────────────────────────────────────────
    _corner_bracket(d, 4, 4, 14, 14, GOLD, 10, 1)
    _corner_bracket(d, W-18, 4, 14, 14, GOLD, 10, 1)
    _corner_bracket(d, 4, H-18, 14, 14, GOLD, 10, 1)
    _corner_bracket(d, W-18, H-18, 14, 14, GOLD, 10, 1)

    return img
