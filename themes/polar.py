"""
Tema: NEBULA 2 — Plasma con gauges de RAM y disco
Variante de NEBULA: misma base de plasma procedural y partículas,
pero la columna izquierda muestra dos gauges de arco circulares
(RAM usada y disco libre). El gauge de disco activa un barrido
luminoso cuando detecta actividad de lectura.
"""
import math, datetime, socket, os
import numpy as np
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

# ── Plasma ─────────────────────────────────────────────────────────────────────
PW, PH = 240, 120

def _make_palette(heat: float) -> np.ndarray:
    t = np.linspace(0, 1, 256)
    cool = np.stack([
        (0.01 + 0.10*np.sin(t*math.pi*2.0 + 1.5)) * 255,
        (0.08 + 0.38*np.sin(t*math.pi*2.0 + 0.8)) * 255,
        (0.18 + 0.62*np.sin(t*math.pi*1.5 + 0.0)) * 255,
    ], axis=1)
    hot = np.stack([
        (0.42 + 0.45*np.sin(t*math.pi*2.0 + 1.2)) * 255,
        (0.48 + 0.45*np.sin(t*math.pi*2.0 + 1.2)) * 255,
        (0.52 + 0.42*np.sin(t*math.pi*1.5 + 0.0)) * 255,
    ], axis=1)
    return np.clip(cool*(1-heat) + hot*heat, 0, 255).astype(np.uint8)

_PALETTE   = _make_palette(0.0)
_LAST_HEAT = 0.0

def _update_palette(cpu):
    global _PALETTE, _LAST_HEAT
    _LAST_HEAT += (cpu/100.0 - _LAST_HEAT) * 0.04
    _PALETTE = _make_palette(_LAST_HEAT)

_xs = np.linspace(0, 2*math.pi, PW, dtype=np.float32)
_ys = np.linspace(0, 2*math.pi, PH, dtype=np.float32)
_X, _Y   = np.meshgrid(_xs, _ys)
_xi = np.arange(PW, dtype=np.float32) - PW//2
_yi = (np.arange(PH, dtype=np.float32) - PH//2)[:, None]
_DIST = np.sqrt(_xi**2 + _yi**2) / (PW * 0.35)

def _plasma(t):
    v  = np.sin(_X + t*0.9)
    v += np.sin(_Y*0.8 + t*0.7)
    v += np.sin((_X+_Y)*0.6 + t*1.1)
    v += np.sin(_DIST*5.5 - t*1.4)
    v   = (v - v.min()) / (v.max() - v.min() + 1e-9)
    idx = (v * 255).astype(np.uint8)
    return Image.fromarray(_PALETTE[idx], 'RGB').resize((W, H), Image.BILINEAR)

# ── Sensores ───────────────────────────────────────────────────────────────────
def _mem():   return psutil.virtual_memory()

def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp','coretemp','cpu_thermal','acpitz']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _gpu():
    for card in ['card0','card1']:
        try:
            import subprocess
            r = subprocess.run(['cat', f'/sys/class/drm/{card}/device/gpu_busy_percent'],
                               capture_output=True, text=True, timeout=1)
            if r.returncode == 0: return float(r.stdout.strip())
        except: pass
    return None

def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu','nvidia','radeon']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _disk():
    for m in ['/home','/']:
        try: return psutil.disk_usage(m)
        except: pass
    return None

def _freq():
    try: return psutil.cpu_freq()
    except: return None

# ── Red ────────────────────────────────────────────────────────────────────────
_nt  = [0, 0]
_ntx = [0] * 60
_nrx = [0] * 60

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

# ── CPU history ────────────────────────────────────────────────────────────────
_cpu_hist = [0.0] * 300

def _push_cpu(v):
    global _cpu_hist
    _cpu_hist = _cpu_hist[1:] + [float(v)]

# ── Disk I/O ───────────────────────────────────────────────────────────────────
_dt  = [0, 0]
_dwr = [0] * 60
_drr = [0] * 60

def _update_disk_io():
    global _dt, _dwr, _drr
    try:
        c = psutil.disk_io_counters()
        if c:
            w, r = c.write_bytes, c.read_bytes
            pw, pr = _dt
            if pw:
                _dwr = _dwr[1:] + [max(0, w - pw)]
                _drr = _drr[1:] + [max(0, r - pr)]
            _dt = [w, r]
    except: pass

def _fmt(b):
    if b > 1_000_000: return f"{b/1_000_000:.1f}M"
    if b > 1_000:     return f"{b/1_000:.0f}K"
    return f"{int(b)}B"

import subprocess as _sp, threading as _th, time as _ti

# ── System updates (background, cada 5 min) ────────────────────────────────────
_upd_count = [-1]   # -1=verificando, 0=al día, N=actualizaciones

def _check_updates():
    while True:
        try:
            r = _sp.run(['pacman', '-Qu'], capture_output=True, text=True, timeout=20)
            _upd_count[0] = len([l for l in r.stdout.splitlines() if l.strip()])
        except: pass
        _ti.sleep(300)

_th.Thread(target=_check_updates, daemon=True).start()

# ── Archivos temporales (background, cada 15 s) ────────────────────────────────
_tmp_data = [0, 0.0]   # [count, size_mb]

def _check_tmp():
    while True:
        try:
            entries = list(os.scandir('/tmp'))
            sz = sum(e.stat().st_size for e in entries if e.is_file(follow_symlinks=False))
            _tmp_data[0] = len(entries)
            _tmp_data[1] = sz / 1024**2
        except: pass
        _ti.sleep(15)

_th.Thread(target=_check_tmp, daemon=True).start()

# ── Logo Arch (precargado) ─────────────────────────────────────────────────────
_ARCH_LOGO = None
try:
    _al = Image.open(os.path.join(_BASE, 'assets', 'arch-logo-light.png')).convert('RGBA')
    _h  = _al.size[1]
    _ARCH_LOGO = _al.crop((0, 0, _h, _h)).resize((26, 26), Image.LANCZOS)
except: pass

# ── Partículas flotantes ───────────────────────────────────────────────────────
import random as _rnd_m
_rnd_m2 = _rnd_m.Random(17)
_PARTS = [(
    _rnd_m2.uniform(0, W),
    _rnd_m2.uniform(0, H),
    _rnd_m2.uniform(-0.18, 0.18),
    _rnd_m2.uniform(0.20, 0.90),
    _rnd_m2.randint(1, 2),
    _rnd_m2.uniform(0, 2*math.pi),
    _rnd_m2.uniform(0.40, 1.0),
) for _ in range(42)]

_HN = socket.gethostname()[:18]

# ── Primitivas ─────────────────────────────────────────────────────────────────
def _glow_text(d, x, y, txt, font, col, intensity=3):
    dim = tuple(min(255, int(c*0.18)) for c in col)
    for ox, oy in [(-intensity,0),(intensity,0),(0,-intensity),(0,intensity),
                   (-intensity,-intensity),(intensity,-intensity),
                   (-intensity,intensity),(intensity,intensity)]:
        d.text((x+ox, y+oy), txt, font=font, fill=dim)
    d.text((x, y), txt, font=font, fill=col)

def _ctr_glow(d, cx, y, txt, font, col, intensity=3):
    bb = d.textbbox((0,0), txt, font=font)
    _glow_text(d, cx-(bb[2]-bb[0])//2, y, txt, font, col, intensity)

def _right_glow(d, rx, y, txt, font, col, intensity=2):
    bb = d.textbbox((0,0), txt, font=font)
    _glow_text(d, rx-(bb[2]-bb[0]), y, txt, font, col, intensity)

def _net_spark(img, x, y, w, h, tx_data, rx_data, col_tx, col_rx):
    n = min(len(tx_data), len(rx_data))
    if n < 2: return ImageDraw.Draw(img)
    all_max = max(max(tx_data), max(rx_data), 1)
    half = h//2 - 1
    mid  = y + half
    nov  = Image.new('RGBA', (W, H), (0,0,0,0))
    nd   = ImageDraw.Draw(nov)
    tx_pts = [(x+int(i*w/(n-1)), mid-int(tx_data[i]/all_max*half)) for i in range(n)]
    rx_pts = [(x+int(i*w/(n-1)), mid+int(rx_data[i]/all_max*half)) for i in range(n)]
    nd.polygon(tx_pts+[(x+w,mid),(x,mid)], fill=col_tx[:3]+(55,))
    nd.polygon(rx_pts+[(x+w,mid),(x,mid)], fill=col_rx[:3]+(38,))
    img.paste(Image.alpha_composite(img, nov))
    d2 = ImageDraw.Draw(img)
    d2.line([(x,mid),(x+w,mid)], fill=tuple(c//5 for c in col_tx), width=1)
    if any(tx_data): d2.line(tx_pts, fill=col_tx, width=1)
    if any(rx_data): d2.line(rx_pts, fill=col_rx, width=1)
    return d2

# ── Pingüino PIL ──────────────────────────────────────────────────────────────
def _penguin(d, cx, cy, s, col):
    """Pingüino simple dibujado con elipses. s = tamaño base."""
    bl, wh, org = (10,10,10), (205,205,205), (255,140,0)
    d.ellipse([cx-s, cy, cx+s, cy+s*2], fill=bl, outline=col, width=1)
    d.ellipse([cx-s//2, cy+s//3, cx+s//2, cy+s*5//3], fill=wh)
    d.ellipse([cx-int(s*.8), cy-int(s*1.5), cx+int(s*.8), cy+int(s*.3)],
              fill=bl, outline=col, width=1)
    for ex in [cx-s//3, cx+s//6]:
        d.ellipse([ex, cy-s, ex+int(s*.3), cy-s+int(s*.3)], fill=wh)
        d.ellipse([ex+1, cy-s+1, ex+int(s*.18)+1, cy-s+int(s*.18)+1], fill=bl)
    d.polygon([(cx-s//5, cy-s//2), (cx+s//5, cy-s//2), (cx, cy-s//5)], fill=org)
    d.ellipse([cx-int(s*1.9), cy+s//4, cx-s, cy+int(s*1.5)], fill=bl, outline=col, width=1)
    d.ellipse([cx+s, cy+s//4, cx+int(s*1.9), cy+int(s*1.5)], fill=bl, outline=col, width=1)
    for fx in [cx-s//2, cx+s//6]:
        d.ellipse([fx, cy+s*2-1, fx+s//2+1, cy+s*2+s//2], fill=org)

# ── Gauge de arco circular ─────────────────────────────────────────────────────
def _arc_gauge(img, d, cx, cy, R, pct, label, val_str, col, frame,
               active=False, reading=False, rd_rate=0, sub_lines=None,
               val_fsize=30, lbl_fsize=17):
    """
    Gauge de 270° (135°→405°). Cuando reading=True activa el barrido exterior
    proporcional a rd_rate (bytes/tick).
    sub_lines: lista de (texto, color) para mostrar debajo del gauge.
    """
    START, SPAN = 135, 270
    dim  = tuple(c // 5 for c in col)
    glow = tuple(min(255, c + 35) for c in col)

    # fondo oscuro circular para contraste
    bg_ov = Image.new('RGBA', (W, H), (0,0,0,0))
    bd    = ImageDraw.Draw(bg_ov)
    bd.ellipse([cx-R-10, cy-R-10, cx+R+10, cy+R+10], fill=(0,0,0,150))
    img.paste(Image.alpha_composite(img, bg_ov))
    d = ImageDraw.Draw(img)

    # ticks cada 45°
    for deg in range(START, START+SPAN+1, 45):
        a  = math.radians(deg)
        x1 = cx + int((R-7)*math.cos(a));  y1 = cy + int((R-7)*math.sin(a))
        x2 = cx + int(R*math.cos(a));      y2 = cy + int(R*math.sin(a))
        d.line([(x1,y1),(x2,y2)], fill=dim, width=1)

    # pista (track) completa
    d.arc([cx-R, cy-R, cx+R, cy+R], start=START, end=START+SPAN,
          fill=dim, width=3)

    # arco de valor — respira cuando hay actividad (lectura o escritura)
    pct_c  = min(max(pct, 0), 100)
    breath = int(5 * math.sin(frame * 0.16)) if active else 0
    arc_deg = max(0, min(int(SPAN * pct_c / 100) + breath, SPAN))

    if arc_deg > 2:
        d.arc([cx-R, cy-R, cx+R, cy+R],
              start=START, end=START+arc_deg, fill=col, width=4)
        ae = math.radians(START + arc_deg)
        ex = cx + int(R * math.cos(ae))
        ey = cy + int(R * math.sin(ae))
        d.ellipse([ex-6, ey-6, ex+6, ey+6], fill=glow)
        d.ellipse([ex-3, ey-3, ex+3, ey+3], fill=col)

    # barrido exterior cuando hay lectura activa
    if reading and rd_rate > 150_000:
        spd    = min(rd_rate / 600_000, 4.5) * 1.8
        sweep  = int((frame * spd) % SPAN)
        Ro = R + 14
        sc_ov  = Image.new('RGBA', (W, H), (0,0,0,0))
        sd     = ImageDraw.Draw(sc_ov)
        # trail tenue
        if sweep > 5:
            sd.arc([cx-Ro, cy-Ro, cx+Ro, cy+Ro],
                   start=START, end=START+sweep,
                   fill=col[:3]+(55,), width=2)
        # cabeza brillante
        head = START + sweep
        sd.arc([cx-Ro, cy-Ro, cx+Ro, cy+Ro],
               start=max(START, head-30), end=head,
               fill=glow[:3]+(200,), width=2)
        # dot en la punta
        he  = math.radians(head)
        hx  = cx + int(Ro * math.cos(he))
        hy  = cy + int(Ro * math.sin(he))
        sd.ellipse([hx-4, hy-4, hx+4, hy+4], fill=glow[:3]+(230,))
        img.paste(Image.alpha_composite(img, sc_ov))
        d = ImageDraw.Draw(img)

    # número central y label — posición y color legibles
    lbl_col = tuple(min(255, c//2 + 80) for c in col)
    _ctr_glow(d, cx, cy - int(val_fsize * 0.80), val_str, Fb(val_fsize), col,     4)
    _ctr_glow(d, cx, cy + int(val_fsize * 0.72), label,   Fr(lbl_fsize), lbl_col, 2)

    # líneas de sub-datos — fuente más grande, más glow
    if sub_lines:
        sy = cy + R + 10
        for txt, tc in sub_lines:
            _ctr_glow(d, cx, sy, txt, Fm(16), tc, 2)
            sy += 22

    return d


# ── Render ─────────────────────────────────────────────────────────────────────
def render(frame: int) -> Image.Image:
    if frame % 2 == 0:
        _update_net()
        _update_disk_io()
    _push_cpu(psutil.cpu_percent(interval=None))

    cores  = psutil.cpu_percent(percpu=True, interval=None)
    cpu    = sum(cores) / len(cores) if cores else 0.0
    mem    = _mem()
    ct     = _temp()
    gpu    = _gpu()
    gt     = _gtemp()
    disk   = _disk()
    freq   = _freq()
    now    = datetime.datetime.now()
    la     = os.getloadavg()
    tx_v   = _ntx[-1] if _ntx else 0
    rx_v   = _nrx[-1] if _nrx else 0
    uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um = divmod(int(uptime.total_seconds()) // 60, 60)
    rd_now = _drr[-1] if _drr else 0
    wr_now = _dwr[-1] if _dwr else 0

    t = frame * (0.018 + cpu * 0.00018)
    _update_palette(cpu)

    img = _plasma(t).convert('RGBA')
    d   = ImageDraw.Draw(img)

    # velo oscuro
    veil = Image.new('RGBA', (W, H), (0,0,0,55))
    img  = Image.alpha_composite(img, veil)
    d    = ImageDraw.Draw(img)

    # paleta de texto
    heat = _LAST_HEAT
    if heat < 0.35:
        TXT   = (195, 228, 255)
        BRIGHT= ( 70, 175, 255)
        DIM   = ( 25,  75, 160)
        ACC   = ( 95, 200, 255)
    elif heat < 0.65:
        TXT   = (210, 238, 255)
        BRIGHT= (145, 215, 255)
        DIM   = ( 55, 115, 200)
        ACC   = (165, 225, 255)
    else:
        TXT   = (228, 245, 255)
        BRIGHT= (215, 238, 255)
        DIM   = (115, 165, 230)
        ACC   = (220, 245, 255)

    WARN = (255, 220,  80)
    RED  = (255,  95,  80)
    def _vc(v):
        if v < 70: return BRIGHT
        if v < 90: return WARN
        return RED

    # ── PARTÍCULAS ────────────────────────────────────────────────────────────
    p_spd = 0.28 + cpu * 0.009
    p_ov  = Image.new('RGBA', (W, H), (0,0,0,0))
    pd2   = ImageDraw.Draw(p_ov)
    for x0, y0, dvx, vy, sz, ph, af in _PARTS:
        px  = int((x0 + dvx*frame + sz*9*math.sin(ph + frame*0.038)) % W)
        py  = int((y0 - vy*p_spd*frame) % H)
        alp = int(af * (65 + 38*math.sin(ph + frame*0.065)))
        pd2.ellipse([px-sz, py-sz, px+sz, py+sz], fill=BRIGHT+(min(220,alp),))
    img = Image.alpha_composite(img, p_ov)
    d   = ImageDraw.Draw(img)

    # ── CPU CENTRO ────────────────────────────────────────────────────────────
    halo = Image.new('RGBA', (W, H), (0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([W//2-185, H//2-135, W//2+185, H//2+125], fill=(0,0,0,160))
    img  = Image.alpha_composite(img, halo)
    d    = ImageDraw.Draw(img)

    # anillo de temperatura
    tc_arc = BRIGHT
    if ct is not None:
        TR = 178
        T_S, T_SPAN = -210, 240
        t_pct = min(ct, 100) / 100.0
        if t_pct < 0.5:
            tc_arc = (int(255*t_pct*2), int(210 - 50*t_pct*2), 255)
        else:
            tc_arc = (255, int(160 - 160*(t_pct-0.5)*2), int(255 - 255*(t_pct-0.5)*2))
        t_arc_end = int(T_SPAN * t_pct)
        dim_arc = tuple(c//4 for c in tc_arc)
        d.arc([W//2-TR, H//2-TR, W//2+TR, H//2+TR],
              start=T_S, end=T_S+T_SPAN, fill=dim_arc, width=2)
        if t_arc_end > 2:
            d.arc([W//2-TR, H//2-TR, W//2+TR, H//2+TR],
                  start=T_S, end=T_S+t_arc_end, fill=tc_arc, width=2)
            ta_e = math.radians(T_S + t_arc_end)
            d.ellipse([W//2+int(TR*math.cos(ta_e))-4, H//2+int(TR*math.sin(ta_e))-4,
                       W//2+int(TR*math.cos(ta_e))+4, H//2+int(TR*math.sin(ta_e))+4],
                      fill=tc_arc)

    cc = _vc(cpu)
    _ctr_glow(d, W//2, H//2-115, f"{cpu:.0f}", Fb(160), cc,   7)
    _ctr_glow(d, W//2, H//2+72,  "% CPU",      Fr(38),  DIM,  3)
    if ct is not None:
        _ctr_glow(d, W//2, H//2+110, f"{ct:.0f}°C", Fd(30), tc_arc, 2)

    # anillos de pulso
    pov = Image.new('RGBA', (W, H), (0,0,0,0))
    pd  = ImageDraw.Draw(pov)
    for ph, base_r, alpha in [(0.0, 130, 95), (math.pi, 165, 55)]:
        pulse_r = int(base_r + 30*math.sin(frame*0.10+ph))
        pr_col  = tuple(min(255, c) for c in cc) + (alpha,)
        pd.ellipse([W//2-pulse_r, H//2-pulse_r, W//2+pulse_r, H//2+pulse_r],
                   outline=pr_col, width=2)
    img = Image.alpha_composite(img, pov)
    d   = ImageDraw.Draw(img)

    # ── GAUGES IZQUIERDA ──────────────────────────────────────────────────────
    # RAM: +38px arriba, +38px a la derecha respecto al centro original
    GX1, GY1, GR1 = 163, 108, 75   # RAM
    GX2, GY2, GR2 = 122, 315, 82   # DISK — más grande en el espacio liberado

    # línea vertical izquierda sutil
    d.line([(4, 10), (4, H-40)], fill=tuple(c//2 for c in BRIGHT), width=2)

    # separador entre gauges
    sep_y = (GY1 + GR1 + GY2 - GR2) // 2
    d.line([(14, sep_y), (GX2*2-14, sep_y)], fill=tuple(c//5 for c in BRIGHT), width=1)

    # gauge RAM
    ram_col  = _vc(mem.percent)
    ram_subs = [
        (f"{mem.used/1024**3:.1f}G / {mem.total/1024**3:.0f}G", TXT),
        (f"{mem.percent:.0f}% used", DIM),
    ]
    d = _arc_gauge(img, d, GX1, GY1, GR1,
                   mem.percent, "RAM", f"{mem.used/1024**3:.1f}G",
                   ram_col, frame,
                   reading=False, rd_rate=0,
                   sub_lines=ram_subs,
                   val_fsize=36, lbl_fsize=19)

    # gauge DISCO — muestra % libre; color y animación según I/O
    if disk:
        free_pct  = 100 - disk.percent
        is_reading = rd_now > 150_000
        is_writing = wr_now > 150_000
        # color del arco: naranja cuando escribe, cyan cuando lee, normal si idle
        if is_writing:
            disk_col = (255, 135, 20)
        elif is_reading:
            disk_col = (60, 200, 255)
        else:
            disk_col = _vc(disk.percent)
        disk_subs = [(f"{disk.free/1024**3:.0f}G libre", TXT)]
        if is_writing:
            disk_subs.append((f"WRITE  {_fmt(wr_now)}/t", (255, 160, 40)))
        elif is_reading:
            disk_subs.append((f"READ   {_fmt(rd_now)}/t", (80, 220, 255)))
        d = _arc_gauge(img, d, GX2, GY2, GR2,
                       free_pct, "DISK FREE", f"{free_pct:.0f}%",
                       disk_col, frame,
                       active=is_reading or is_writing,
                       reading=is_reading, rd_rate=rd_now,
                       sub_lines=disk_subs,
                       val_fsize=40, lbl_fsize=17)

    # ── PANEL DERECHO ─────────────────────────────────────────────────────────
    RW_ = 222
    RX  = W - 8 - RW_
    RY, RH = 12, H - 44
    _ra = (130*np.maximum(0, (np.arange(RW_, dtype=np.float32)/RW_)**0.55)).astype(np.uint8)
    _rb = np.zeros((RH, RW_, 4), dtype=np.uint8)
    _rb[:, :, 3] = _ra[np.newaxis, :]
    rovl = Image.fromarray(_rb, 'RGBA')
    img.paste(rovl, (RX, RY), rovl)
    d = ImageDraw.Draw(img)

    d.line([(RX+RW_, RY), (RX+RW_, RY+RH)], fill=tuple(c//2 for c in BRIGHT), width=2)

    # ── TEMP FILES — barra ancha arriba del panel derecho (posición fija) ────
    tmp_n  = _tmp_data[0]
    tmp_mb = _tmp_data[1]
    tcol   = RED if tmp_n > 50 else WARN if tmp_n > 15 else tuple(c//2 for c in BRIGHT)
    TBX, TBY, TBW, TBH = RX + 2, RY + 2, RW_ - 4, 12
    d.rectangle([TBX, TBY, TBX+TBW, TBY+TBH], fill=(10,10,10,200))
    tfw = max(0, int(TBW * min(tmp_n, 80) / 80))
    if tfw > 0:
        d.rectangle([TBX, TBY, TBX+tfw, TBY+TBH], fill=tcol)
    tlbl = f"TMP  {tmp_n}f" + (f"  {tmp_mb:.0f}M" if tmp_mb >= 1 else "")
    _ctr_glow(d, RX + RW_//2, TBY - 1, tlbl, Fm(11), tcol, 1)

    py = RY + 14

    # ── PINGÜINO / LOGO — top-right ──────────────────────────────────────────
    upd = _upd_count[0]
    if upd > 0:
        _penguin(d, RX+17, py+14, 6, WARN)
        _glow_text(d, RX+37, py+3,  str(upd),   Fb(22), WARN, 3)
        _glow_text(d, RX+37, py+26, "UPDATE" if upd == 1 else "UPDATES", Fm(11), DIM, 1)
    elif upd == 0:
        if _ARCH_LOGO:
            img.paste(_ARCH_LOGO, (RX+4, py), _ARCH_LOGO)
            d = ImageDraw.Draw(img)
        _right_glow(d, RX+RW_-8, py+7, "OMARCHY", Fr(17),
                    tuple(c//2 for c in BRIGHT), 1)
    if upd >= 0:
        py += 30

    def _rrow(label, val, col):
        nonlocal py
        d.text((RX+12, py), label, font=Fm(17), fill=DIM)
        _right_glow(d, RX+RW_-10, py, val, Fo(17), col, 2)
        py += 24

    def _rbig_row(label, val, col):
        nonlocal py
        d.text((RX+12, py), label, font=Fr(22), fill=DIM)
        py += 22
        _glow_text(d, RX+12, py, val, Ft(68), col, 4)
        py += 76

    def _rbar_row(pct, col):
        nonlocal py
        bw = RW_ - 24
        d.rectangle([RX+12, py, RX+12+bw, py+14], fill=(20,20,20,200))
        fw = int(bw * pct / 100)
        if fw > 1:
            for i in range(fw):
                t_ = 0.3 + 0.7*(i/max(fw,1))
                d.line([(RX+12+i, py),(RX+12+i, py+14)],
                       fill=(min(255,int(col[0]*t_)), min(255,int(col[1]*t_)), min(255,int(col[2]*t_))))
            d.line([(RX+12+fw-1, py),(RX+12+fw-1, py+14)], fill=TXT, width=1)
        py += 20

    if gpu is not None:
        _rbig_row("GPU", f"{gpu:.0f}%", _vc(gpu))
        _rbar_row(gpu, _vc(gpu))
        if gt is not None: _rrow("gpu temp", f"{gt:.0f}°C", _vc(gpu if gt > 70 else 0))
    else:
        d.text((RX+12, py+20), "NO GPU", font=Fo(22), fill=DIM)
        py += 68

    py += 10
    _rbig_row("NET UP", f"{_fmt(tx_v)}/s", BRIGHT)
    d = _net_spark(img, RX+12, py, RW_-24, 36, _ntx[-40:], _nrx[-40:], BRIGHT, ACC)
    py += 42
    _rrow("net dl",  f"{_fmt(rx_v)}/s", TXT)
    py += 4
    _rrow("load",    f"{la[0]:.2f}",   _vc(la[0]/max(psutil.cpu_count() or 4,1)*100))
    _rrow("uptime",  f"{uh}h{um:02d}m", TXT)
    if freq:
        _rrow("freq", f"{freq.current/1000:.2f}GHz", BRIGHT)

    # ── WAVEFORM CPU ──────────────────────────────────────────────────────────
    WX  = GX2 + GR2 + 28
    WX2 = RX - 28
    WW  = WX2 - WX
    WY  = H - 88
    WH  = 44
    hist = _cpu_hist[-WW:]
    if len(hist) > 2:
        n = len(hist)
        fill_pts  = [(WX+int(i*WW/(n-1)), WY+WH-int(v/100*WH)) for i,v in enumerate(hist)]
        fill_pts += [(WX2, WY+WH), (WX, WY+WH)]
        wov = Image.new('RGBA', (W, H), (0,0,0,0))
        wd  = ImageDraw.Draw(wov)
        wd.polygon(fill_pts, fill=tuple(c//10 for c in BRIGHT)+(60,))
        img = Image.alpha_composite(img, wov)
        d   = ImageDraw.Draw(img)
        line_pts = [(WX+int(i*WW/(n-1)), WY+WH-int(v/100*WH)) for i,v in enumerate(hist)]
        dim_w    = tuple(c//3 for c in BRIGHT)
        for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
            d.line([(x+ox, y+oy) for x,y in line_pts], fill=dim_w, width=1)
        d.line(line_pts, fill=BRIGHT, width=1)

    # ── STRIP INFERIOR ────────────────────────────────────────────────────────
    nc     = len(cores)
    sty    = H - 32
    bw_c   = max(6, min(16, (W-160)//max(nc,1)))
    gap    = max(2, (W-160-nc*bw_c)//max(nc-1,1))
    bx_s   = 80 + (W-160-(nc*bw_c+(nc-1)*gap))//2
    bovl   = Image.new('RGBA', (W, 32), (0,0,0,120))
    img.paste(bovl, (0, sty), bovl)
    d = ImageDraw.Draw(img)

    for i, cv in enumerate(cores):
        bx_i = bx_s + i*(bw_c+gap)
        bh   = max(4, int(24*cv/100))
        cc2  = _vc(cv)
        d.rectangle([bx_i, sty+26-bh, bx_i+bw_c, sty+26],
                    fill=tuple(c//3 for c in cc2))
        d.rectangle([bx_i, sty+26-bh, bx_i+bw_c, sty+26-bh+2], fill=cc2)

    _glow_text(d, 12, sty+6, f"{nc} CORES", Fm(15), DIM, 1)
    _right_glow(d, W-12, sty+6,
                f"LOAD {la[0]:.2f}  UP {uh}h{um:02d}m", Fm(15), DIM, 1)

    return img.convert('RGB')
