"""
Tema: RYZEN — AMD HUD cyberpunk
Display landscape 960×480
"""
import math, random, datetime, time as _time
import psutil, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

W, H = 960, 480
_BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Wallpaper HUD (cacheado) ──────────────────────────────────────────────────
_WP_PATH  = os.path.join(_BASE, "assets", "ryzen_bg.jpg")
_WP_CACHE = None

def _load_wp():
    global _WP_CACHE
    if _WP_CACHE is None:
        try:
            raw = Image.open(_WP_PATH).convert('RGB')
            iw, ih = raw.size
            # Escalar al ancho completo 960px y centrar verticalmente
            scale = W / iw
            nh    = int(ih * scale)
            raw   = raw.resize((W, nh), Image.LANCZOS)
            top   = (nh - H) // 2
            _WP_CACHE = raw.crop((0, top, W, top + H))
        except Exception:
            _WP_CACHE = False
    return _WP_CACHE if _WP_CACHE else None

# ── Fuentes ───────────────────────────────────────────────────────────────────
_FD     = os.path.join(_BASE, "fonts")
_F_TEKO = os.path.join(_FD, "Teko-Medium.ttf")
_F_ORB  = os.path.join(_FD, "Orbitron-Bold.ttf")    # números — AMD gaming
_F_RAJ  = os.path.join(_FD, "Rajdhani-SemiBold.ttf")# labels limpios
_F_FIRA = os.path.join(_FD, "FiraCodeNerdFont-Medium.ttf")  # datos técnicos
_F_MONO = os.path.join(_FD, "CaskaydiaMonoNF-SemiBold.ttf") # mono

def _fnt(size, style='teko'):
    paths = {'teko': _F_TEKO, 'val': _F_ORB, 'label': _F_RAJ,
             'mono': _F_MONO, 'fira': _F_FIRA}
    try:   return ImageFont.truetype(paths.get(style, _F_TEKO), size)
    except:
        try:   return ImageFont.truetype(_F_TEKO, size)
        except: return ImageFont.load_default()

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = (3,    6,  16)
BG2    = (7,   11,  24)
CYAN   = (0,   218, 255)
CYAN2  = (0,   160, 200)
DCYAN  = (0,    52,  72)
VDCYAN = (0,    14,  26)
PINK   = (255,  12, 188)
DPINK  = (80,    4,  62)
GREEN  = (0,   210, 128)
ORA    = (255, 152,  20)
RED    = (255,  45,  45)
WHITE  = (200, 240, 255)
DIM    = (0,    45,  65)
# AMD branding
AMD_R  = (220,  38,   0)
AMD_O  = (255,  90,  10)
AMD_D  = (80,   14,   0)

# ── Métricas ──────────────────────────────────────────────────────────────────
_NET_ST  = {'t': 0.0, 'sent': 0, 'recv': 0, 'ul': 0.0, 'dl': 0.0}
_CPU_NM  = None

def _cpu_pct(): return psutil.cpu_percent(interval=None)
def _mem():     return psutil.virtual_memory()
def _cpu_freq():
    try:
        f = psutil.cpu_freq()
        return f.current / 1000 if f else None
    except: return None
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal']:
            if k in t: return t[k][0].current
    except: return None
def _gpu_pct():
    try:
        r = subprocess.run(['cat', '/sys/class/drm/card1/device/gpu_busy_percent'],
                           capture_output=True, text=True, timeout=1)
        return int(r.stdout.strip()) if r.returncode == 0 else None
    except: return None
def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu', 'nvidia', 'radeon']:
            if k in t: return t[k][0].current
    except: return None
def _gpu_vram():
    try:
        u = int(open('/sys/class/drm/card1/device/mem_info_vram_used').read())
        v = int(open('/sys/class/drm/card1/device/mem_info_vram_total').read())
        return u // (1024*1024), v // (1024*1024)
    except: return None, None
def _net():
    global _NET_ST
    try:
        now = _time.time(); c = psutil.net_io_counters()
        dt  = now - _NET_ST['t']
        if dt > 0.05 and _NET_ST['t'] > 0:
            _NET_ST['ul'] = (c.bytes_sent - _NET_ST['sent']) / dt / 1024
            _NET_ST['dl'] = (c.bytes_recv - _NET_ST['recv']) / dt / 1024
        _NET_ST.update({'t': now, 'sent': c.bytes_sent, 'recv': c.bytes_recv})
        return max(0.0, _NET_ST['ul']), max(0.0, _NET_ST['dl'])
    except: return 0.0, 0.0
def _fmt_net(kbs):
    if kbs < 1:    return "0.0 K"
    if kbs < 1024: return f"{kbs:.1f} K"
    return f"{kbs/1024:.1f} M"
def _cpu_name():
    global _CPU_NM
    if _CPU_NM is None:
        try:
            for line in open('/proc/cpuinfo'):
                if 'model name' in line:
                    nm = line.split(':')[1].strip()
                    for kw in ['Ryzen', 'Core', 'Threadripper', 'EPYC']:
                        if kw in nm:
                            p = nm.split(); i = p.index(kw)
                            _CPU_NM = ' '.join(p[i:i+4]); return _CPU_NM
                    _CPU_NM = nm[:22]; return _CPU_NM
        except: pass
        _CPU_NM = 'RYZEN'
    return _CPU_NM
def _disks():
    seen, res = set(), []
    for p in psutil.disk_partitions(all=False):
        if p.mountpoint in {'/', '/home'} and p.mountpoint not in seen:
            seen.add(p.mountpoint)
            try:
                u = psutil.disk_usage(p.mountpoint)
                res.append((p.mountpoint, u.used, u.total, u.percent))
            except: pass
    return sorted(res)
def _tc(t):
    if t is None: return CYAN
    return GREEN if t < 65 else (ORA if t < 80 else RED)
def _vc(v):
    return CYAN if v < 70 else (ORA if v < 90 else RED)

# ── Grid hexagonal (pre-calculado) ────────────────────────────────────────────
_HR   = 26
_HH   = _HR * math.sqrt(3)
_HW   = _HR * 2
_HEXS = []
random.seed(13)
for _row in range(-1, int(H / _HH) + 3):
    for _col in range(-1, int(W / (_HW * 0.75)) + 3):
        _hx = _col * _HW * 0.75
        _hy = _row * _HH + (_HH / 2 if _col % 2 else 0)
        _pts = tuple((_hx + _HR * math.cos(math.radians(60*i)),
                      _hy + _HR * math.sin(math.radians(60*i))) for i in range(6))
        _lit  = random.random() < 0.04   # hexágono destacado
        _HEXS.append((_pts, _lit))

# ── Circuit traces (estáticos) ─────────────────────────────────────────────────
random.seed(99)
_TRACES = []
for _ in range(18):
    x = random.randint(20, W-20); y = random.randint(20, H-20)
    steps = [('H' if random.random() > 0.5 else 'V', random.randint(30, 160))
             for _ in range(random.randint(2, 4))]
    _TRACES.append((x, y, steps))

# ── Fondo ─────────────────────────────────────────────────────────────────────
def _draw_bg(img, d, frame):
    # Wallpaper HUD como base
    wp = _load_wp()
    if wp:
        img.paste(wp, (0, 0))
        # Overlay muy leve para uniformizar el fondo (deja el wallpaper visible)
        ov = Image.new('RGBA', (W, H), (3, 6, 16, 60))
        base = img.convert('RGBA'); base.alpha_composite(ov)
        img_new = base.convert('RGB')
        img.paste(img_new)
    else:
        d.rectangle([0, 0, W, H], fill=BG)
        for pts, lit in _HEXS:
            d.polygon(pts, outline=(0, 28, 46) if lit else (0, 14, 24))

    # Scanline animada encima del wallpaper
    sy = (frame * 4) % (H + 40) - 20
    for dy, strength in [(0, 55), (1, 30), (-1, 30), (2, 12), (-2, 12)]:
        fy = sy + dy
        if 0 <= fy < H:
            col = (0, min(255, strength * 2), min(255, strength * 3))
            d.line([(0, fy), (W, fy)], fill=col, width=1)

# ── Decoración de esquinas y marcos ───────────────────────────────────────────
def _corners(d, x, y, w, h, col, size=14, width=2):
    segs = [(x, y+size, x, y, x+size, y),
            (x+w-size, y, x+w, y, x+w, y+size),
            (x, y+h-size, x, y+h, x+size, y+h),
            (x+w-size, y+h, x+w, y+h, x+w, y+h-size)]
    for ax, ay, bx, by, cx_, cy_ in segs:
        d.line([(ax, ay), (bx, by)], fill=col, width=width)
        d.line([(bx, by), (cx_, cy_)], fill=col, width=width)

def _panel(d, x, y, w, h, col=None, title=None, title_col=None, title_size=15):
    col = col or DCYAN; tc = title_col or CYAN
    _corners(d, x, y, w, h, col, size=12, width=1)
    d.line([(x+13, y), (x+w-13, y)], fill=col, width=1)
    d.line([(x+13, y+h), (x+w-13, y+h)], fill=col, width=1)
    d.line([(x, y+13), (x, y+h-13)], fill=col, width=1)
    d.line([(x+w, y+13), (x+w, y+h-13)], fill=col, width=1)
    if title:
        tf = _fnt(title_size, 'label')
        d.text((x+16, y+3), title, font=tf, fill=tc)

def _glow_text(d, x, y, text, size, col, dim, style='teko'):
    f = _fnt(size, style)
    for dx, dy in [(-2,-1),(2,-1),(-2,1),(2,1),(0,-2),(0,2),(-1,-2),(1,-2)]:
        d.text((x+dx, y+dy), text, font=f, fill=dim)
    d.text((x, y), text, font=f, fill=col)

def _center_text(d, cx, y, text, size, col, dim=None, style='val'):
    f   = _fnt(size, style)
    bb  = d.textbbox((0, 0), text, font=f)
    tw  = bb[2] - bb[0]
    xp  = cx - tw // 2
    if dim:
        for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            d.text((xp+dx, y+dy), text, font=f, fill=dim)
    d.text((xp, y), text, font=f, fill=col)

def _hbar(d, x, y, w, h, pct, col, dim):
    d.rectangle([x-1, y-1, x+w+1, y+h+1], fill=(5, 10, 22), outline=dim)
    fw = int(w * min(pct, 100) / 100)
    for xi in range(fw):
        t = xi / max(fw, 1)
        r_ = int(dim[0] + (col[0]-dim[0]) * t)
        g_ = int(dim[1] + (col[1]-dim[1]) * t)
        b_ = int(dim[2] + (col[2]-dim[2]) * t)
        d.line([(x+xi, y), (x+xi, y+h)], fill=(r_, g_, b_))
    if fw > 0:
        d.line([(x+fw-1, y), (x+fw-1, y+h)], fill=col)
        d.line([(x+fw-2, y), (x+fw-2, y+h)], fill=col)  # doble borde derecho

# ── Gauge circular ────────────────────────────────────────────────────────────
_GS, _GE = 150, 30    # start=150° end=30° → 240° barrido horario

def _gauge(img, cx, cy, r, pct, col, frame=0, thick=9,
           label='', val_txt='', sub_txt='', val_col_ov=None,
           pulse=False, anim_col=None, val_sz=None):
    vc    = val_col_ov or col
    end_a = (_GS + _GE_sweep(pct)) % 360

    # ── Glow layer ──
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    if pct > 0.5:
        for rr, al in [(r+10, 20), (r+6, 40), (r+2, 65), (r, 90)]:
            bb = [cx-rr, cy-rr, cx+rr, cy+rr]
            gd.arc(bb, _GS, end_a, fill=(*col, al), width=thick+4)
    if pulse:
        pa = int(30 + 20 * math.sin(frame * 0.15))
        outer = r + 18 + int(6 * math.sin(frame * 0.12))
        bb_p  = [cx-outer, cy-outer, cx+outer, cy+outer]
        gd.arc(bb_p, 0, 360, fill=(*(anim_col or col), pa), width=2)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=6))
    base = img.convert('RGBA'); base.alpha_composite(glow)
    img  = base.convert('RGB');  d = ImageDraw.Draw(img)

    # ── Anillo exterior decorativo ──
    ro = r + 3
    d.arc([cx-ro, cy-ro, cx+ro, cy+ro], _GS, (_GS+240)%360, fill=VDCYAN, width=1)

    # ── Arco fondo (dim, 240°) ──
    bb = [cx-r, cy-r, cx+r, cy+r]
    d.arc(bb, _GS, (_GS+240)%360, fill=DCYAN, width=thick)

    # ── Arco valor ──
    if pct > 0.5:
        # segmentos con gap cada 30° para efecto de ticks
        seg_start = _GS
        seg_total = _GE_sweep(pct)
        seg_w     = 27     # grados por segmento
        gap       = 3      # grados de gap entre segmentos
        deg = 0
        while deg < seg_total:
            s = (seg_start + deg) % 360
            e_deg = min(seg_w, seg_total - deg)
            if e_deg > 1:
                e = (s + e_deg) % 360
                d.arc(bb, s, e, fill=col, width=thick)
            deg += seg_w + gap

    # ── Ticks ──
    for ti in range(0, 241, 30):
        ang  = math.radians(_GS + ti)
        is_major = ti % 60 == 0
        r1, r2 = r+4, r+12 if is_major else r+8
        xi1 = cx + r1 * math.cos(ang); yi1 = cy + r1 * math.sin(ang)
        xi2 = cx + r2 * math.cos(ang); yi2 = cy + r2 * math.sin(ang)
        d.line([(xi1, yi1), (xi2, yi2)],
               fill=CYAN if ti <= _GE_sweep(pct) else DIM, width=2 if is_major else 1)

    # ── Anillo interior + relleno ──
    ri = r - thick - 5
    d.arc([cx-ri, cy-ri, cx+ri, cy+ri], 0, 360, fill=DCYAN, width=1)
    rf = r - thick - 9
    d.ellipse([cx-rf, cy-rf, cx+rf, cy+rf], fill=BG2)

    # ── Anillo pulsante ──
    if pulse:
        rp = int(rf * 0.90 + 3 * math.sin(frame * 0.18))
        d.arc([cx-rp, cy-rp, cx+rp, cy+rp], 0, 360,
              fill=(*(anim_col or CYAN), ), width=1)
        d.arc([cx-rp+2, cy-rp+2, cx+rp-2, cy+rp-2], 0, 360,
              fill=DCYAN, width=1)

    # ── Textos ──
    if label:
        _center_text(d, cx, cy - rf + 8, label, 14, CYAN2, DCYAN, 'label')
    if val_txt:
        vsz  = val_sz if val_sz else max(18, int(rf * 1.05))
        _center_text(d, cx, cy - vsz//2 - 4, val_txt, vsz, vc, DCYAN, 'val')
    if sub_txt:
        _center_text(d, cx, cy + rf - 22, sub_txt, 13, DIM, None, 'label')

    return img

def _GE_sweep(pct):
    return 240 * min(pct, 100) / 100

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)
    _draw_bg(img, d, frame)

    # ── Datos ──────────────────────────────────────────────────────────────────
    cpu      = _cpu_pct()
    mem      = _mem()
    ct       = _temp()
    gpu      = _gpu_pct()
    gt       = _gtemp()
    freq     = _cpu_freq()
    ul, dl   = _net()
    vru, vrt = _gpu_vram()
    disks    = _disks()
    now      = datetime.datetime.now()
    ram_mb   = (mem.total-mem.available) // (1024*1024)
    cpu_nm   = _cpu_name()
    gpu_v    = gpu if gpu is not None else 0

    # ══════════════════════════════════════════════════════════════════════════
    # GAUGES
    # ══════════════════════════════════════════════════════════════════════════

    # CPU % — gauge grande, centro, pulsante
    img = _gauge(img, 418, 212, 138, cpu, CYAN, frame=frame, thick=10,
                 label='CPU', val_txt=f"{cpu:.0f}", sub_txt='%',
                 pulse=True, anim_col=CYAN)
    d = ImageDraw.Draw(img)

    # CPU GHz — pequeño, izq
    freq_pct = (freq / 6.0 * 100) if freq else 0
    img = _gauge(img, 262, 168, 66, freq_pct, CYAN, frame=frame, thick=7,
                 label='GHz', val_txt=f"{freq:.1f}" if freq else '--',
                 sub_txt='FREQ', val_col_ov=CYAN, val_sz=30)
    d = ImageDraw.Draw(img)

    # CPU temp — der arriba
    img = _gauge(img, 622, 132, 74, (ct / 105 * 100) if ct else 0,
                 _tc(ct), frame=frame, thick=8,
                 label='CPU°', val_txt=f"{ct:.0f}" if ct else '--',
                 sub_txt='TEMP', val_col_ov=_tc(ct))
    d = ImageDraw.Draw(img)

    # GPU % — der abajo
    gvc = _vc(gpu_v)
    img = _gauge(img, 622, 328, 74, gpu_v, gvc, frame=frame, thick=8,
                 label='GPU', val_txt=f"{gpu_v:.0f}", sub_txt='%',
                 val_col_ov=gvc)
    d = ImageDraw.Draw(img)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL IZQUIERDO
    # ══════════════════════════════════════════════════════════════════════════
    LX, LW = 6, 178
    _panel(d, LX, 6, LW, 132, title='  NETWORK', title_size=14)
    y0 = 28
    for icon, val in [('UL', _fmt_net(ul)), ('DL', _fmt_net(dl))]:
        d.text((LX+12, y0), icon, font=_fnt(16, 'label'), fill=DIM)
        _glow_text(d, LX+50, y0-3, val, 24, CYAN, DCYAN, 'val')
        y0 += 36
    d.text((LX+12, y0+2), 'TOTAL:', font=_fnt(13, 'label'), fill=DIM)
    d.text((LX+64, y0), _fmt_net(ul + dl), font=_fnt(17, 'val'), fill=DCYAN)

    _panel(d, LX, 146, LW, 108, title='  RAM', title_size=14)
    _glow_text(d, LX+12, 166, f"{ram_mb:,}", 34, CYAN, DCYAN, 'val')
    d.text((LX+12, 202), 'MB USED', font=_fnt(13, 'label'), fill=DIM)
    _hbar(d, LX+10, 218, LW-20, 10, mem.percent, CYAN, DCYAN)
    d.text((LX+10, 232), f"{(mem.total-mem.available)//1024//1024//1024:.1f}G / {mem.total//1024//1024//1024:.0f}G",
           font=_fnt(14, 'val'), fill=DIM)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL DERECHO
    # ══════════════════════════════════════════════════════════════════════════
    RX, RW = 772, 182

    _panel(d, RX, 6, RW, 138, title='  DATE / TIME', title_size=14)
    d.text((RX+12, 28), now.strftime('%Y / %m / %d'), font=_fnt(18, 'val'), fill=DCYAN)
    _glow_text(d, RX+8, 50, now.strftime('%H:%M'), 64, CYAN, DCYAN, 'teko')
    d.text((RX+12, 116), now.strftime(':%S'), font=_fnt(22, 'val'), fill=DCYAN)
    d.text((RX+80, 120), now.strftime('%A')[:3].upper(), font=_fnt(18, 'label'), fill=DIM)

    _panel(d, RX, 152, RW, 110, title='  GPU STATUS', title_size=14)
    if gt is not None:
        tc_ = _tc(gt)
        d.text((RX+12, 172), 'TEMP', font=_fnt(14, 'label'), fill=DIM)
        _glow_text(d, RX+58, 167, f"{gt:.0f}°", 30, tc_, DCYAN, 'val')
    if vru is not None:
        _glow_text(d, RX+12, 204, f"{vru:,}", 30, PINK, DPINK, 'val')
        d.text((RX+12, 234), f"/ {vrt:,} MB  VRAM", font=_fnt(13, 'label'), fill=DIM)
    else:
        d.text((RX+12, 200), 'N / A', font=_fnt(22, 'val'), fill=DIM)

    # ══════════════════════════════════════════════════════════════════════════
    # AMD RYZEN 9 BRANDING — bajo el gauge central
    # ══════════════════════════════════════════════════════════════════════════
    BY_AMD = 356
    d.line([(196, BY_AMD), (640, BY_AMD)], fill=AMD_D, width=1)
    d.line([(196, BY_AMD+1), (640, BY_AMD+1)], fill=(40, 8, 0), width=1)

    # "AMD  RYZEN 9" centrado en la zona central (x 196..640 → cx=418)
    brand = 'AMD  RYZEN 9'
    bf    = _fnt(36, 'teko')
    bbb   = d.textbbox((0, 0), brand, font=bf)
    bw    = bbb[2] - bbb[0]
    bx    = 418 - bw // 2
    # "AMD" en naranja, "RYZEN 9" en rojo
    amd_f  = _fnt(36, 'teko')
    amd_bb = d.textbbox((0, 0), 'AMD  ', font=amd_f)
    aw     = amd_bb[2] - amd_bb[0]
    for dx, dy in [(-2,-1),(2,-1),(-2,1),(2,1)]:
        d.text((bx+dx, BY_AMD+3+dy), 'AMD  ', font=amd_f, fill=AMD_D)
        d.text((bx+aw+dx, BY_AMD+3+dy), 'RYZEN 9', font=amd_f, fill=AMD_D)
    d.text((bx, BY_AMD+3), 'AMD  ', font=amd_f, fill=AMD_O)
    d.text((bx+aw, BY_AMD+3), 'RYZEN 9', font=amd_f, fill=AMD_R)

    # CPU model debajo, más pequeño
    _center_text(d, 418, BY_AMD + 40, cpu_nm.upper(), 17, AMD_O, AMD_D, 'label')

    # ══════════════════════════════════════════════════════════════════════════
    # FRANJA INFERIOR — Discos
    # ══════════════════════════════════════════════════════════════════════════
    BY = 402
    d.line([(6, BY-2), (W-6, BY-2)], fill=DCYAN, width=1)

    disk_zones = [(8, 186), (572, 952)]
    for j, (mount, used, total, pct) in enumerate(disks[:2]):
        dx, dw = disk_zones[j][0], disk_zones[j][1] - disk_zones[j][0]
        dc = _vc(pct)
        gb_u = used  / 1024**3
        gb_t = total / 1024**3
        _panel(d, dx, BY, dw, 70, col=DCYAN, title=f' {mount}', title_size=13)
        _glow_text(d, dx+14, BY+18, f"{pct:.0f}%", 30, dc, DCYAN, 'val')
        d.text((dx+68, BY+24), f"{gb_u:.0f}/{gb_t:.0f}G", font=_fnt(18, 'val'), fill=DCYAN)
        _hbar(d, dx+12, BY+52, dw-22, 9, pct, dc, DCYAN)

    # ══════════════════════════════════════════════════════════════════════════
    # MARCO GENERAL
    # ══════════════════════════════════════════════════════════════════════════
    # Líneas neon top/bottom
    d.line([(0, 0), (W, 0)],     fill=CYAN,  width=2)
    d.line([(0, 1), (W, 1)],     fill=DCYAN, width=1)
    d.line([(0, H-1), (W, H-1)], fill=CYAN,  width=2)
    d.line([(0, H-2), (W, H-2)], fill=DCYAN, width=1)
    # Esquinas grandes
    _corners(d, 0, 0, W-1, H-1, CYAN, size=22, width=2)

    # Divisores verticales (entre paneles y centro)
    for vx in [192, 768]:
        d.line([(vx, 8), (vx, H-8)], fill=DCYAN, width=1)
        # Nodo en puntos
        for vy in [8, H//2, H-8]:
            d.ellipse([vx-3, vy-3, vx+3, vy+3], fill=CYAN)

    return img
