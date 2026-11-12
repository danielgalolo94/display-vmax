"""
Tema: NEBULA — Plasma vivo reactivo al sistema
Display landscape 960x480
Fondo de plasma procedural (demoscene-style) que CAMBIA DE COLOR
con la carga: azul-violeta en reposo → naranja-rojo bajo carga máxima.
Stats como texto luminoso sobre paneles semi-oscuros.
Sin gauges, sin brackets, sin HUD táctico — solo forma y luz.
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

# resolución interna del plasma (se escala 4× al final → muy rápido)
PW, PH = 240, 120

# ── Paleta dinámica ────────────────────────────────────────────────────────────
# El plasma usa un índice 0..255; los colores dependen de heat (0=frío, 1=caliente)
# Se precomputan dos tablas y se mezclan según cpu%

def _make_palette(heat: float) -> np.ndarray:
    """Devuelve tabla RGB 256×3. heat ∈ [0,1]."""
    t = np.linspace(0, 1, 256)
    cool = np.stack([
        (0.05 + 0.25*np.sin(t*math.pi*2 + 0.0)) * 255,   # R — casi nulo en frío
        (0.10 + 0.45*np.sin(t*math.pi*3 + 1.0)) * 255,   # G — teal/cian
        (0.20 + 0.60*np.sin(t*math.pi*1.5 + 2.1)) * 255, # B — azul dominante
    ], axis=1)
    hot = np.stack([
        (0.30 + 0.55*np.sin(t*math.pi*2 + 0.5)) * 255,   # R — naranja/rojo
        (0.05 + 0.25*np.sin(t*math.pi*4 + 3.2)) * 255,   # G — poco
        (0.05 + 0.15*np.sin(t*math.pi*1.8 + 1.8)) * 255, # B — poco
    ], axis=1)
    pal = np.clip(cool * (1.0 - heat) + hot * heat, 0, 255).astype(np.uint8)
    return pal

_PALETTE = _make_palette(0.0)
_LAST_HEAT = 0.0

def _update_palette(cpu: float) -> None:
    global _PALETTE, _LAST_HEAT
    target = cpu / 100.0
    # suavizado exponencial para que no salte
    _LAST_HEAT += (target - _LAST_HEAT) * 0.04
    _PALETTE = _make_palette(_LAST_HEAT)

# ── Plasma procedural ──────────────────────────────────────────────────────────
# Precalculamos las grillas estáticas de X e Y para no repetirlo cada frame
_xs = np.linspace(0, 2 * math.pi, PW, dtype=np.float32)
_ys = np.linspace(0, 2 * math.pi, PH, dtype=np.float32)
_X, _Y = np.meshgrid(_xs, _ys)
# distancia al centro normalizada
_CX, _CY = PW // 2, PH // 2
_xi = np.arange(PW, dtype=np.float32) - _CX
_yi = (np.arange(PH, dtype=np.float32) - _CY)[:, None]
_DIST = np.sqrt(_xi**2 + _yi**2) / (PW * 0.35)

def _plasma(t: float) -> Image.Image:
    """Genera un frame de plasma a resolución PW×PH y lo escala a W×H."""
    # cuatro capas de ondas que se mueven a distintas velocidades
    v  = np.sin(_X + t * 0.9)
    v += np.sin(_Y * 0.8 + t * 0.7)
    v += np.sin((_X + _Y) * 0.6 + t * 1.1)
    v += np.sin(_DIST * 5.5 - t * 1.4)
    # normalizar a índice 0..255
    v   = (v - v.min()) / (v.max() - v.min() + 1e-9)
    idx = (v * 255).astype(np.uint8)
    # colorear con la paleta activa
    rgb = _PALETTE[idx]          # PH × PW × 3
    small = Image.fromarray(rgb, mode='RGB')
    return small.resize((W, H), Image.BILINEAR)

# ── Sensores ──────────────────────────────────────────────────────────────────
def _mem():   return psutil.virtual_memory()

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
            import subprocess
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
        try: return psutil.disk_usage(m)
        except: pass
    return None

def _freq():
    try:    return psutil.cpu_freq()
    except: return None

import subprocess as _sp, threading as _th, time as _ti
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

# ── CPU history para waveform ─────────────────────────────────────────────────
_cpu_hist = [0.0] * 300

def _push_cpu(v):
    global _cpu_hist
    _cpu_hist = _cpu_hist[1:] + [float(v)]

# ── Disk I/O tracking ─────────────────────────────────────────────────────────
_dt  = [0, 0]
_dwr = [0] * 60   # write bytes/tick history
_drr = [0] * 60   # read bytes/tick history

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

# ── Partículas flotantes ───────────────────────────────────────────────────────
import random as _rnd_m
_rnd_m_inst = _rnd_m.Random(17)
_PARTS = [(
    _rnd_m_inst.uniform(0, W),           # x0
    _rnd_m_inst.uniform(0, H),           # y0
    _rnd_m_inst.uniform(-0.18, 0.18),    # drift x por frame
    _rnd_m_inst.uniform(0.20, 0.90),     # velocidad base hacia arriba
    _rnd_m_inst.randint(1, 2),           # tamaño
    _rnd_m_inst.uniform(0, 2*math.pi),   # fase oscilación
    _rnd_m_inst.uniform(0.40, 1.0),      # factor alpha
) for _ in range(42)]

_HN = socket.gethostname()[:18]

# ── Primitivas de texto con glow ───────────────────────────────────────────────
def _glow_text(d, x, y, txt, font, col, intensity=3):
    """Texto con halo suave: dibuja copias oscuras desplazadas primero."""
    dim = tuple(min(255, int(c * 0.18)) for c in col)
    for ox, oy in [(-intensity,0),(intensity,0),(0,-intensity),(0,intensity),
                   (-intensity,-intensity),(intensity,-intensity),
                   (-intensity,intensity),(intensity,intensity)]:
        d.text((x+ox, y+oy), txt, font=font, fill=dim)
    d.text((x, y), txt, font=font, fill=col)

def _ctr_glow(d, cx, y, txt, font, col, intensity=3):
    bb = d.textbbox((0,0), txt, font=font)
    _glow_text(d, cx - (bb[2]-bb[0])//2, y, txt, font, col, intensity)

def _right_glow(d, rx, y, txt, font, col, intensity=2):
    bb = d.textbbox((0,0), txt, font=font)
    _glow_text(d, rx - (bb[2]-bb[0]), y, txt, font, col, intensity)

# panel semi-transparente: dibuja un rectángulo oscuro semitransparente
def _dark_panel(d, x, y, w, h, alpha=185):
    ovl = Image.new('RGBA', (w, h), (0, 0, 0, alpha))
    return ovl   # caller hace img.paste(ovl, (x,y), ovl)

def _sparkline(d, x, y, w, h, data, col):
    if not any(data): return
    mx = max(data) or 1
    n  = len(data)
    pts = [(x + int(i*w/(n-1)), y+h - int(v/mx*h)) for i, v in enumerate(data)]
    if len(pts) > 1: d.line(pts, fill=col, width=1)

# ── Sparkline dual TX/RX ──────────────────────────────────────────────────────
def _net_spark(img, x, y, w, h, tx_data, rx_data, col_tx, col_rx):
    n = min(len(tx_data), len(rx_data))
    if n < 2:
        return ImageDraw.Draw(img)
    all_max = max(max(tx_data), max(rx_data), 1)
    half = h // 2 - 1
    mid  = y + half

    nov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    nd  = ImageDraw.Draw(nov)

    tx_pts = [(x + int(i*w/(n-1)), mid - int(tx_data[i]/all_max*half)) for i in range(n)]
    rx_pts = [(x + int(i*w/(n-1)), mid + int(rx_data[i]/all_max*half)) for i in range(n)]

    nd.polygon(tx_pts + [(x+w, mid), (x, mid)], fill=col_tx[:3] + (55,))
    nd.polygon(rx_pts + [(x+w, mid), (x, mid)], fill=col_rx[:3] + (38,))

    img_c = Image.alpha_composite(img, nov)
    img.paste(img_c)
    d2 = ImageDraw.Draw(img)

    d2.line([(x, mid), (x+w, mid)], fill=tuple(c//5 for c in col_tx), width=1)
    if any(tx_data): d2.line(tx_pts, fill=col_tx, width=1)
    if any(rx_data): d2.line(rx_pts, fill=col_rx, width=1)

    return d2


# ── Spinner de disco ──────────────────────────────────────────────────────────
def _disk_spinner(img, d, cx, cy, wr_now, rd_now, frame):
    """Disco giratorio que se activa con escritura (naranja) o lectura (cyan)."""
    writing = wr_now > 200_000          # umbral 200 KB/tick
    reading = rd_now > 200_000
    active  = writing or reading

    # color base: naranja=escritura, cyan=lectura, gris=idle
    if writing:
        col = (255, 130, 25)
    elif reading:
        col = (60,  200, 255)
    else:
        col = (70,  55,  40)

    dim   = tuple(c // 4 for c in col)
    glow  = tuple(min(255, c + 40) for c in col)

    R  = 34    # radio exterior del "plato"
    R2 = 22    # anillo medio
    R3 = 12    # anillo interior

    # halo suave cuando activo
    if active:
        hov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        hd2 = ImageDraw.Draw(hov)
        hd2.ellipse([cx-R-14, cy-R-14, cx+R+14, cy+R+14],
                    fill=tuple(c//5 for c in col) + (80,))
        merged = Image.alpha_composite(img.convert('RGBA'), hov)
        img.paste(merged.convert('RGB'))
        d = ImageDraw.Draw(img)

    # anillo exterior — gira lento (o rápido si activo)
    spd1 = 1.6 if active else 0.4
    a1   = int((frame * spd1) % 360)
    arc_len = 150 if active else 80
    d.arc([cx-R, cy-R, cx+R, cy+R],
          start=a1, end=a1 + arc_len, fill=col, width=3)
    d.arc([cx-R, cy-R, cx+R, cy+R],
          start=(a1 + 180) % 360, end=(a1 + 180 + arc_len//2) % 360,
          fill=dim, width=1)

    # anillo medio — gira en sentido contrario
    spd2 = 2.4 if active else 0.7
    a2   = int((360 - frame * spd2) % 360)
    d.arc([cx-R2, cy-R2, cx+R2, cy+R2],
          start=a2, end=a2 + 100, fill=col, width=2)
    d.arc([cx-R2, cy-R2, cx+R2, cy+R2],
          start=(a2 + 180) % 360, end=(a2 + 240) % 360,
          fill=dim, width=1)

    # anillo interior — más rápido aún
    spd3 = 3.5 if active else 1.1
    a3   = int((frame * spd3) % 360)
    d.arc([cx-R3, cy-R3, cx+R3, cy+R3],
          start=a3, end=a3 + 60, fill=glow, width=2)

    # spindle central
    sc = glow if active else dim
    d.ellipse([cx-4, cy-4, cx+4, cy+4], fill=sc)
    d.ellipse([cx-2, cy-2, cx+2, cy+2], fill=col)

    # arm de lectura/escritura (línea desde el centro hacia el borde)
    arm_a = math.radians((frame * (spd1 * 1.1)) % 360)
    ax    = cx + int(R * 0.85 * math.cos(arm_a))
    ay    = cy + int(R * 0.85 * math.sin(arm_a))
    d.line([(cx, cy), (ax, ay)], fill=col, width=1)

    # etiqueta debajo
    label = "WRITE" if writing else ("READ" if reading else "DISK")
    lcol  = col if active else dim
    bb    = d.textbbox((0, 0), label, font=Fm(13))
    d.text((cx - (bb[2]-bb[0])//2, cy + R + 5), label, font=Fm(13), fill=lcol)

    if active:
        rate = _fmt(wr_now if writing else rd_now)
        bb2  = d.textbbox((0, 0), rate, font=Fm(12))
        d.text((cx - (bb2[2]-bb2[0])//2, cy + R + 20), rate, font=Fm(12), fill=dim)

    return d


# ── Render ─────────────────────────────────────────────────────────────────────
def render(frame: int) -> Image.Image:
    if frame % 2 == 0:
        _update_net()
        _update_disk_io()
    _push_cpu(psutil.cpu_percent(interval=None))

    cores = psutil.cpu_percent(percpu=True, interval=None)
    cpu   = sum(cores) / len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gpu   = _gpu()
    gt    = _gtemp()
    disk  = _disk()
    freq  = _freq()
    now   = datetime.datetime.now()
    la    = os.getloadavg()
    tx_v  = _ntx[-1] if _ntx else 0
    rx_v  = _nrx[-1] if _nrx else 0
    uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um = divmod(int(uptime.total_seconds()) // 60, 60)

    # velocidad del plasma — se acelera con cpu
    t = frame * (0.018 + cpu * 0.00018)

    # actualizar paleta según carga
    _update_palette(cpu)

    # ── base: plasma ──────────────────────────────────────────────────────────
    img = _plasma(t).convert('RGBA')
    d   = ImageDraw.Draw(img)

    # ── velo oscuro central para legibilidad ──────────────────────────────────
    # vignette: bordes más brillantes, centro ligeramente atenuado
    veil = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    vd   = ImageDraw.Draw(veil)
    # franja central horizontal ligeramente oscura
    vd.rectangle([0, 0, W, H], fill=(0, 0, 0, 55))
    img = Image.alpha_composite(img, veil)
    d   = ImageDraw.Draw(img)

    # color dominante del plasma → determina el color del texto
    # frío (baja carga) → texto cyan/blanco; caliente → texto naranja/amarillo
    heat = _LAST_HEAT
    if heat < 0.35:
        TXT   = (210, 240, 255)   # blanco-azulado
        BRIGHT= (100, 220, 255)   # cyan brillante
        DIM   = (55,  120, 180)
        ACC   = (70,  180, 255)
    elif heat < 0.65:
        TXT   = (255, 240, 200)   # blanco-cálido
        BRIGHT= (255, 210, 80)    # dorado
        DIM   = (160, 110, 30)
        ACC   = (255, 170, 40)
    else:
        TXT   = (255, 220, 180)   # crema
        BRIGHT= (255, 130, 50)    # naranja
        DIM   = (180, 70,  20)
        ACC   = (255, 90,  40)

    WARN = (255, 200, 50)
    RED  = (255, 80,  60)
    def _vc(v):
        if v < 70: return BRIGHT
        if v < 90: return WARN
        return RED

    # ── PARTÍCULAS flotantes sobre el plasma ─────────────────────────────────
    p_spd = 0.28 + cpu * 0.009      # se aceleran con CPU
    p_ov  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pd2   = ImageDraw.Draw(p_ov)
    for x0, y0, dvx, vy, sz, ph, af in _PARTS:
        px = int((x0 + dvx * frame + sz * 9 * math.sin(ph + frame * 0.038)) % W)
        py = int((y0 - vy * p_spd * frame) % H)
        alp = int(af * (65 + 38 * math.sin(ph + frame * 0.065)))
        pd2.ellipse([px-sz, py-sz, px+sz, py+sz], fill=BRIGHT + (min(220, alp),))
    img = Image.alpha_composite(img, p_ov)
    d   = ImageDraw.Draw(img)

    # ── NÚMERO GRANDE DE CPU — centro absoluto de la pantalla ─────────────────
    # halo oscuro suave: elipse orgánica
    halo = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([W//2-185, H//2-135, W//2+185, H//2+125], fill=(0, 0, 0, 160))
    img  = Image.alpha_composite(img, halo)
    d    = ImageDraw.Draw(img)

    # anillo de temperatura: arco fino alrededor del número, cyan→rojo según temp
    if ct is not None:
        TR  = 178
        T_S, T_SPAN = -210, 240
        t_pct = min(ct, 100) / 100.0
        # color interpolado cyan→amarillo→rojo
        if t_pct < 0.5:
            tc_arc = (int(0   + 255*t_pct*2), int(210 - 50*t_pct*2), 255)
        else:
            tc_arc = (255, int(160 - 160*(t_pct-0.5)*2), int(255 - 255*(t_pct-0.5)*2))
        t_arc_end = int(T_SPAN * t_pct)
        dim_arc = tuple(c//4 for c in tc_arc)
        d.arc([W//2-TR, H//2-TR, W//2+TR, H//2+TR],
              start=T_S, end=T_S+T_SPAN, fill=dim_arc, width=2)
        if t_arc_end > 2:
            d.arc([W//2-TR, H//2-TR, W//2+TR, H//2+TR],
                  start=T_S, end=T_S+t_arc_end, fill=tc_arc, width=2)
            # dot al extremo del arco
            ta_end = math.radians(T_S + t_arc_end)
            d.ellipse([W//2 + int(TR*math.cos(ta_end))-4,
                       H//2 + int(TR*math.sin(ta_end))-4,
                       W//2 + int(TR*math.cos(ta_end))+4,
                       H//2 + int(TR*math.sin(ta_end))+4], fill=tc_arc)

    cc = _vc(cpu)
    _ctr_glow(d, W//2, H//2 - 115, f"{cpu:.0f}", Fb(160), cc,   7)
    _ctr_glow(d, W//2, H//2 +  72, "% CPU",      Fr(38),  DIM,  3)
    if ct is not None:
        _ctr_glow(d, W//2, H//2 + 110, f"{ct:.0f}°C", Fd(30), tc_arc, 2)

    # doble anillo de pulso
    pov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pd  = ImageDraw.Draw(pov)
    for ph, base_r, alpha in [(0.0, 130, 95), (math.pi, 165, 55)]:
        pulse_r = int(base_r + 30 * math.sin(frame * 0.10 + ph))
        pr_col  = tuple(min(255, c) for c in cc) + (alpha,)
        pd.ellipse([W//2 - pulse_r, H//2 - pulse_r,
                    W//2 + pulse_r, H//2 + pulse_r],
                   outline=pr_col, width=2)
    img = Image.alpha_composite(img, pov)
    d   = ImageDraw.Draw(img)

    # ── PANEL IZQUIERDO ───────────────────────────────────────────────────────
    LX, LW = 8, 222
    LY, LH = 12, H - 44
    # gradiente: opaco en el borde exterior, se evapora hacia el centro
    _la = (130 * np.maximum(0, 1 - (np.arange(LW, dtype=np.float32) / LW) ** 0.55)).astype(np.uint8)
    _lb = np.zeros((LH, LW, 4), dtype=np.uint8)
    _lb[:, :, 3] = _la[np.newaxis, :]
    lovl = Image.fromarray(_lb, 'RGBA')
    img.paste(lovl, (LX, LY), lovl)
    d = ImageDraw.Draw(img)

    d.line([(LX, LY), (LX, LY+LH)], fill=tuple(c//2 for c in BRIGHT), width=2)

    py = LY + 14

    def _row(label, val, col):
        nonlocal py
        d.text((LX+12, py), label, font=Fm(17), fill=DIM)
        _right_glow(d, LX+LW-10, py, val, Fo(17), col, 2)
        py += 24

    def _big_row(label, val, col):
        nonlocal py
        d.text((LX+12, py), label, font=Fr(22), fill=DIM)
        py += 22
        _glow_text(d, LX+12, py, val, Ft(68), col, 4)
        py += 76

    def _bar_row(pct, col):
        nonlocal py
        bw = LW - 24
        d.rectangle([LX+12, py, LX+12+bw, py+14], fill=(20, 20, 20, 200))
        fw = int(bw * pct / 100)
        if fw > 1:
            for i in range(fw):
                t_ = 0.3 + 0.7 * (i / max(fw, 1))
                d.line([(LX+12+i, py), (LX+12+i, py+14)],
                       fill=(min(255, int(col[0]*t_)), min(255, int(col[1]*t_)), min(255, int(col[2]*t_))))
            d.line([(LX+12+fw-1, py), (LX+12+fw-1, py+14)], fill=TXT, width=1)
        py += 20

    _big_row("MEMORY", f"{(mem.total-mem.available)/1024**3:.1f}G", _vc(mem.percent))
    _bar_row(mem.percent, _vc(mem.percent))
    _row("total",   f"{mem.total/1024**3:.0f}G",     TXT)
    _row("avail",   f"{mem.available/1024**3:.1f}G", BRIGHT)
    _row("used %",  f"{mem.percent:.0f}%",           _vc(mem.percent))
    py += 14

    if disk:
        _big_row("DISK", f"{disk.percent:.0f}%", _vc(disk.percent))
        _bar_row(disk.percent, _vc(disk.percent))
        _row("used",  f"{disk.used/1024**3:.0f}G",  TXT)
        _row("free",  f"{(disk.total-disk.used)/1024**3:.0f}G", BRIGHT)

    # ── PANEL DERECHO ─────────────────────────────────────────────────────────
    RW_ = 222
    RX  = W - 8 - RW_
    RY, RH = 12, H - 44
    # gradiente: transparente en el borde interior, opaco en el exterior derecho
    _ra = (130 * np.maximum(0, (np.arange(RW_, dtype=np.float32) / RW_) ** 0.55)).astype(np.uint8)
    _rb = np.zeros((RH, RW_, 4), dtype=np.uint8)
    _rb[:, :, 3] = _ra[np.newaxis, :]
    rovl = Image.fromarray(_rb, 'RGBA')
    img.paste(rovl, (RX, RY), rovl)
    d = ImageDraw.Draw(img)

    d.line([(RX+RW_, RY), (RX+RW_, RY+RH)], fill=tuple(c//2 for c in BRIGHT), width=2)

    py = RY + 14

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
        d.rectangle([RX+12, py, RX+12+bw, py+14], fill=(20, 20, 20, 200))
        fw = int(bw * pct / 100)
        if fw > 1:
            for i in range(fw):
                t_ = 0.3 + 0.7 * (i / max(fw, 1))
                d.line([(RX+12+i, py), (RX+12+i, py+14)],
                       fill=(min(255, int(col[0]*t_)), min(255, int(col[1]*t_)), min(255, int(col[2]*t_))))
            d.line([(RX+12+fw-1, py), (RX+12+fw-1, py+14)], fill=TXT, width=1)
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
    _rrow("load",    f"{la[0]:.2f}",   _vc(la[0] / max(psutil.cpu_count() or 4, 1) * 100))
    _rrow("uptime",  f"{uh}h{um:02d}m", TXT)
    if freq:
        _rrow("freq", f"{freq.current/1000:.2f}GHz", BRIGHT)

    # ── WAVEFORM CPU — ola de historia en el centro inferior ──────────────────
    WX  = LX + LW + 28           # empieza tras el panel izq (~258)
    WX2 = RX - 28                # termina antes del panel der (~710)
    WW  = WX2 - WX               # ~452px
    WY  = H - 88                 # y base de la ola
    WH  = 44                     # altura máxima de la ola
    hist = _cpu_hist[-WW:]       # un sample por pixel
    if len(hist) > 2:
        n = len(hist)
        # área rellena (fill bajo la línea) muy tenue
        fill_pts  = [(WX + int(i*WW/(n-1)), WY+WH - int(v/100*WH)) for i, v in enumerate(hist)]
        fill_pts += [(WX2, WY+WH), (WX, WY+WH)]
        wov = Image.new('RGBA', (W, H), (0,0,0,0))
        wd  = ImageDraw.Draw(wov)
        wd.polygon(fill_pts, fill=tuple(c//10 for c in BRIGHT) + (60,))
        img = Image.alpha_composite(img, wov)
        d   = ImageDraw.Draw(img)
        # línea principal con glow
        line_pts = [(WX + int(i*WW/(n-1)), WY+WH - int(v/100*WH)) for i, v in enumerate(hist)]
        dim_w    = tuple(c//3 for c in BRIGHT)
        for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
            off_pts = [(x+ox, y+oy) for x,y in line_pts]
            d.line(off_pts, fill=dim_w, width=1)
        d.line(line_pts, fill=BRIGHT, width=1)

    # ── DISCO SPINNER — flota en el plasma, zona inferior izquierda ───────────
    wr_now = _dwr[-1] if _dwr else 0
    rd_now = _drr[-1] if _drr else 0
    d = _disk_spinner(img, d, 310, H - 82, wr_now, rd_now, frame)

    # ── STRIP INFERIOR: núcleos como mini-barras ───────────────────────────────
    nc      = len(cores)
    strip_y = H - 32
    bw_c    = max(6, min(16, (W - 160) // max(nc, 1)))
    gap     = max(2, (W - 160 - nc * bw_c) // max(nc - 1, 1))
    bx_s    = 80 + (W - 160 - (nc * bw_c + (nc-1) * gap)) // 2
    bovl = Image.new('RGBA', (W, 32), (0, 0, 0, 120))
    img.paste(bovl, (0, strip_y), bovl)
    d = ImageDraw.Draw(img)

    for i, cv in enumerate(cores):
        bx_i = bx_s + i * (bw_c + gap)
        bh   = max(4, int(24 * cv / 100))
        cc2  = _vc(cv)
        d.rectangle([bx_i, strip_y + 26 - bh, bx_i + bw_c, strip_y + 26],
                    fill=tuple(c//3 for c in cc2))
        d.rectangle([bx_i, strip_y + 26 - bh, bx_i + bw_c, strip_y + 26 - bh + 2],
                    fill=cc2)

    _glow_text(d, 12, strip_y + 6, f"{nc} CORES", Fm(15), DIM, 1)
    _right_glow(d, W-12, strip_y+6,
                f"LOAD {la[0]:.2f}  UP {uh}h{um:02d}m", Fm(15), DIM, 1)

    return img.convert('RGB')
