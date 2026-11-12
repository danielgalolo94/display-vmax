"""
Tema: RYZEN 9 — AMD HUD rojo fuego
Display landscape 960×480
"""
import math, random, datetime, time as _time
import psutil, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os

W, H  = 960, 480
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASS  = os.path.join(_BASE, "assets")

# ── Fuentes ───────────────────────────────────────────────────────────────────
_FD     = os.path.join(_BASE, "fonts")
_F_TEKO = os.path.join(_FD, "Teko-Medium.ttf")
_F_BOLD = os.path.join(_FD, "Orbitron-Bold.ttf")        # números — rojo fuego AMD
_F_SEMI = os.path.join(_FD, "Rajdhani-SemiBold.ttf")    # labels
_F_MONO = os.path.join(_FD, "CaskaydiaMonoNF-SemiBold.ttf") # mono data
_F_FIRA = os.path.join(_FD, "FiraCodeNerdFont-Medium.ttf")  # técnico

def F(sz, style='teko'):
    p = {'teko': _F_TEKO, 'val': _F_BOLD, 'label': _F_SEMI,
         'mono': _F_MONO, 'fira': _F_FIRA}.get(style, _F_TEKO)
    try:    return ImageFont.truetype(p, sz)
    except: return ImageFont.load_default()

# ── Paleta AMD ────────────────────────────────────────────────────────────────
BG    = (6,    2,   2)    # casi negro tinte rojo
BG2   = (14,   4,   4)    # fondo ligeramente más claro
FIRE  = (237,  28,  36)   # rojo AMD #ED1C24
EMBER = (255, 108,   0)   # naranja AMD #FF6C00
GLOW  = (255, 170,  50)   # naranja claro / destello
DFIRE = (72,    8,   6)   # rojo oscuro (dim)
VDFIRE= (22,    3,   2)   # rojo muy oscuro
DIM   = (55,   14,  10)   # texto muy apagado
WHITE = (255, 232, 218)   # blanco cálido
GOOD  = (22,  210,  90)   # temperatura OK
WARN  = (255, 175,   0)   # temperatura media
CRIT  = (255,  40,  20)   # temperatura crítica

# ── Caché de assets ───────────────────────────────────────────────────────────
_CACHE: dict = {}

def _load_bg():
    if 'bg' not in _CACHE:
        try:
            raw  = Image.open(os.path.join(_ASS, 'ryzen_bg.jpg')).convert('RGB')
            iw, ih = raw.size
            scale = W / iw
            nh    = int(ih * scale)
            raw   = raw.resize((W, nh), Image.LANCZOS)
            top   = max(0, (nh - H) // 2)
            _CACHE['bg'] = raw.crop((0, top, W, top + H))
        except:
            _CACHE['bg'] = False
    return _CACHE['bg'] if _CACHE['bg'] else None

def _load_logo(fname, color, size):
    key = f'{fname}_{size[0]}'
    if key not in _CACHE:
        try:
            raw  = Image.open(os.path.join(_ASS, fname)).convert('L')
            inv  = ImageOps.invert(raw)
            logo = Image.new('RGBA', raw.size, (*color, 255))
            logo.putalpha(inv)
            _CACHE[key] = logo.resize(size, Image.LANCZOS)
        except:
            _CACHE[key] = False
    return _CACHE[key] if _CACHE[key] else None

# ── Métricas ──────────────────────────────────────────────────────────────────
_NET_ST = {'t': 0., 'sent': 0, 'recv': 0, 'ul': 0., 'dl': 0.}
_CPUNM  = None

def _cpu():   return psutil.cpu_percent(interval=None)
def _cpus():  return psutil.cpu_percent(interval=None, percpu=True)
def _mem():   return psutil.virtual_memory()
def _freq():
    try:   f = psutil.cpu_freq(); return f.current / 1000 if f else None
    except: return None
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal']:
            if k in t: return t[k][0].current
    except: return None
def _gpu():
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
def _vram():
    try:
        u = int(open('/sys/class/drm/card1/device/mem_info_vram_used').read())
        v = int(open('/sys/class/drm/card1/device/mem_info_vram_total').read())
        return u // (1024*1024), v // (1024*1024)
    except: return None, None
def _gsclk():
    try:
        for l in open('/sys/class/drm/card1/device/pp_dpm_sclk').read().split('\n'):
            if '*' in l: return int(l.split(':')[1].split('M')[0].strip())
    except: return None
def _net():
    global _NET_ST
    try:
        now = _time.time(); c = psutil.net_io_counters()
        dt  = now - _NET_ST['t']
        if dt > 0.05 and _NET_ST['t'] > 0:
            _NET_ST['ul'] = (c.bytes_sent - _NET_ST['sent']) / dt / 1024
            _NET_ST['dl'] = (c.bytes_recv - _NET_ST['recv']) / dt / 1024
        _NET_ST.update({'t': now, 'sent': c.bytes_sent, 'recv': c.bytes_recv})
        return max(0., _NET_ST['ul']), max(0., _NET_ST['dl'])
    except: return 0., 0.
def _fmtnet(k):
    if k < 1:    return "0.0 K"
    if k < 1024: return f"{k:.1f} K"
    return f"{k / 1024:.1f} M"
def _uptime():
    s = int(_time.time() - psutil.boot_time())
    h, r = divmod(s, 3600); m, sc = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{sc:02d}"
def _cpuname():
    global _CPUNM
    if _CPUNM is None:
        try:
            for line in open('/proc/cpuinfo'):
                if 'model name' in line:
                    nm = line.split(':')[1].strip()
                    for kw in ['Ryzen', 'Core', 'Threadripper', 'EPYC']:
                        if kw in nm:
                            p = nm.split(); i = p.index(kw)
                            _CPUNM = ' '.join(p[i:i+4]); return _CPUNM
                    _CPUNM = nm[:24]; return _CPUNM
        except: pass
        _CPUNM = 'RYZEN 9'
    return _CPUNM
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
    if t is None: return EMBER
    return GOOD if t < 65 else (WARN if t < 80 else CRIT)
def _vc(v): return EMBER if v < 70 else (WARN if v < 90 else CRIT)

# ── Helpers gráficos ──────────────────────────────────────────────────────────
def _glow(d, x, y, txt, sz, col, dim, style='teko'):
    f = F(sz, style)
    for dx, dy in [(-2, -1), (2, -1), (-2, 1), (2, 1), (0, -2), (0, 2)]:
        d.text((x + dx, y + dy), txt, font=f, fill=dim)
    d.text((x, y), txt, font=f, fill=col)

def _ctext(d, cx, y, txt, sz, col, dim=None, style='val'):
    f  = F(sz, style); bb = d.textbbox((0, 0), txt, font=f)
    xp = cx - (bb[2] - bb[0]) // 2
    if dim:
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            d.text((xp + dx, y + dy), txt, font=f, fill=dim)
    d.text((xp, y), txt, font=f, fill=col)

def _bar(d, x, y, w, h, pct, col, dim):
    d.rectangle([x-1, y-1, x+w+1, y+h+1], fill=(10, 2, 2), outline=dim)
    fw = int(w * min(pct, 100) / 100)
    for xi in range(fw):
        t = xi / max(fw, 1)
        # Gradiente de dim (rojo oscuro) a col (rojo/naranja vivo)
        c = (int(dim[0] + (col[0] - dim[0]) * t),
             int(dim[1] + (col[1] - dim[1]) * t),
             int(dim[2] + (col[2] - dim[2]) * t))
        d.line([(x + xi, y), (x + xi, y + h)], fill=c)
    if fw > 0:
        d.line([(x + fw - 1, y), (x + fw - 1, y + h)], fill=col)

def _corners(d, x, y, w, h, col, sz=12, lw=1):
    for ax, ay, bx, by, cx_, cy_ in [
        (x, y+sz, x, y, x+sz, y), (x+w-sz, y, x+w, y, x+w, y+sz),
        (x, y+h-sz, x, y+h, x+sz, y+h), (x+w-sz, y+h, x+w, y+h, x+w, y+h-sz)]:
        d.line([(ax, ay), (bx, by)], fill=col, width=lw)
        d.line([(bx, by), (cx_, cy_)], fill=col, width=lw)

def _panel(d, x, y, w, h, col=None, title=None, title_col=None):
    col = col or DFIRE; tc = title_col or EMBER
    _corners(d, x, y, w, h, col, sz=10, lw=1)
    d.line([(x+11, y), (x+w-11, y)],   fill=col, width=1)
    d.line([(x+11, y+h), (x+w-11, y+h)], fill=col, width=1)
    d.line([(x, y+11), (x, y+h-11)],   fill=col, width=1)
    d.line([(x+w, y+11), (x+w, y+h-11)], fill=col, width=1)
    if title:
        d.text((x + 13, y + 2), title, font=F(13, 'label'), fill=tc)

def _paste_logo(img, logo, x, y):
    if logo is not None:
        img.paste(logo, (x, y), logo)

# ── Gauge circular — arco rojo fuego ─────────────────────────────────────────
_GS = 150   # ángulo de inicio 150°, barrido 240° horario

def _gauge(img, cx, cy, r, pct, col, thick=9, frame=0,
           label='', val='', sub='', vcol=None, pulse=False, vsz=None):
    vc  = vcol or col
    deg = 240 * min(pct, 100) / 100
    end = (_GS + deg) % 360

    # Glow layer en rojo/naranja
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    if pct > 0.5:
        for rr, al in [(r+14, 12), (r+9, 30), (r+4, 55), (r, 80)]:
            bb = [cx-rr, cy-rr, cx+rr, cy+rr]
            gd.arc(bb, _GS, end, fill=(*col, al), width=thick + 4)
    if pulse:
        pa = int(30 + 20 * math.sin(frame * 0.14))
        rp = r + 22 + int(6 * math.sin(frame * 0.11))
        gd.arc([cx-rp, cy-rp, cx+rp, cy+rp], 0, 360, fill=(*col, pa), width=2)
    gl = gl.filter(ImageFilter.GaussianBlur(radius=7))
    b  = img.convert('RGBA'); b.alpha_composite(gl)
    img = b.convert('RGB'); d = ImageDraw.Draw(img)

    # Anillo exterior muy dim
    ro = r + 4
    d.arc([cx-ro, cy-ro, cx+ro, cy+ro], _GS, (_GS + 240) % 360, fill=VDFIRE, width=1)
    # Fondo arco (dim rojo oscuro)
    bb = [cx-r, cy-r, cx+r, cy+r]
    d.arc(bb, _GS, (_GS + 240) % 360, fill=DFIRE, width=thick)

    # Arco valor (segmentado, gradiente naranja→rojo)
    if pct > 0.5:
        seg_w = 27; gap = 3; s = _GS; rem = deg
        while rem > 0:
            sw  = min(seg_w, rem)
            e   = (s + sw) % 360
            # Gradiente: inicio naranja→rojo según posición
            t_g = 1 - (rem / deg)
            r_  = int(EMBER[0] + (col[0] - EMBER[0]) * t_g)
            g_  = int(EMBER[1] + (col[1] - EMBER[1]) * t_g)
            b_  = int(EMBER[2] + (col[2] - EMBER[2]) * t_g)
            d.arc(bb, s, e, fill=(r_, g_, b_), width=thick)
            s = (s + sw + gap) % 360; rem -= sw + gap

    # Ticks
    for ti in range(0, 241, 30):
        ang = math.radians(_GS + ti); maj = ti % 60 == 0
        r1, r2 = r + 5, r + (13 if maj else 8)
        d.line([(cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)),
                (cx + r2 * math.cos(ang), cy + r2 * math.sin(ang))],
               fill=(FIRE if ti <= deg else DIM), width=(2 if maj else 1))

    # Interior
    ri = r - thick - 4
    d.arc([cx-ri, cy-ri, cx+ri, cy+ri], 0, 360, fill=DFIRE, width=1)
    rf = r - thick - 8
    d.ellipse([cx-rf, cy-rf, cx+rf, cy+rf], fill=BG2)

    # Anillo pulsante interior
    if pulse:
        rp2 = int(rf * 0.88 + 3 * math.sin(frame * 0.2))
        d.arc([cx-rp2, cy-rp2, cx+rp2, cy+rp2], 0, 360, fill=DFIRE, width=1)

    # Textos centrados
    if label:
        _ctext(d, cx, cy - rf + 5, label, 14, EMBER, DFIRE, 'label')
    if val:
        sz_ = vsz or max(18, int(rf * 1.05))
        _ctext(d, cx, cy - sz_ // 2 - 4, val, sz_, vc, DFIRE, 'val')
    if sub:
        _ctext(d, cx, cy + rf - 20, sub, 13, DIM, None, 'label')
    return img

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    img = Image.new('RGB', (W, H), BG)

    # Fondo — wallpaper ryzen con overlay rojo muy leve
    bg = _load_bg()
    if bg:
        img.paste(bg, (0, 0))
        ov = Image.new('RGBA', (W, H), (*BG, 80))
        b  = img.convert('RGBA'); b.alpha_composite(ov)
        img = b.convert('RGB')
    else:
        d_ = ImageDraw.Draw(img)
        d_.rectangle([0, 0, W, H], fill=BG)

    d = ImageDraw.Draw(img)

    # Scanline roja animada
    sy = (frame * 4) % (H + 40) - 20
    for dy, st in [(0, 55), (1, 30), (-1, 30), (2, 12), (-2, 12)]:
        fy = sy + dy
        if 0 <= fy < H:
            d.line([(0, fy), (W, fy)],
                   fill=(min(255, st * 3), min(255, st // 2), 0), width=1)

    # ── Logos AMD ─────────────────────────────────────────────────────────────
    ryzen_logo = _load_logo('amd_ryzen_logo.png', FIRE, (190, 62))
    amd_logo   = _load_logo('amd_logo.png',       EMBER, (80, 32))
    _paste_logo(img, ryzen_logo, 8, 4)
    _paste_logo(img, amd_logo, 876, 4)
    d = ImageDraw.Draw(img)

    # ── Datos ─────────────────────────────────────────────────────────────────
    cpu_v  = _cpu()
    cpu_all= _cpus()
    mem    = _mem()
    ct     = _temp()
    freq   = _freq()
    gpu_v  = _gpu() or 0
    gt     = _gtemp()
    ul, dl = _net()
    vru, vrt = _vram()
    gsclk  = _gsclk()
    disks  = _disks()
    now    = datetime.datetime.now()
    cpu_nm = _cpuname()
    uptime = _uptime()
    ram_mb = (mem.total - mem.available) // (1024 * 1024)
    ram_gb = (mem.total - mem.available) / 1024**3
    tot_gb = mem.total / 1024**3

    # ══════════════════════════════════════════════════════════════════════════
    # GAUGES (centro: cx=476)
    # ══════════════════════════════════════════════════════════════════════════

    # CPU % — gauge grande, pulsante
    img = _gauge(img, 476, 228, 122, cpu_v, FIRE, thick=10, frame=frame,
                 label='CPU', val=f"{cpu_v:.0f}", sub='%',
                 pulse=True, vcol=GLOW)
    d = ImageDraw.Draw(img)

    # CPU GHz — pequeño izq
    fpct = (freq / 6.0 * 100) if freq else 0
    img  = _gauge(img, 270, 178, 60, fpct, EMBER, thick=7, frame=frame,
                  label='GHz', val=f"{freq:.1f}" if freq else '--',
                  sub='FREQ', vsz=28)
    d = ImageDraw.Draw(img)

    # CPU Temp — der arriba
    ctc = _tc(ct)
    img = _gauge(img, 668, 148, 66, (ct / 105 * 100) if ct else 0,
                 ctc, thick=7, frame=frame,
                 label='CPU°', val=f"{ct:.0f}" if ct else '--',
                 sub='TEMP', vcol=ctc)
    d = ImageDraw.Draw(img)

    # GPU % — der abajo
    gvc = _vc(gpu_v)
    img = _gauge(img, 678, 330, 66, gpu_v, gvc, thick=7, frame=frame,
                 label='GPU', val=f"{gpu_v:.0f}", sub='%', vcol=gvc)
    d = ImageDraw.Draw(img)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL IZQUIERDO
    # ══════════════════════════════════════════════════════════════════════════
    LX, LW = 6, 182

    _panel(d, LX, 72, LW, 110, title=' NETWORK')
    d.text((LX+10, 90),  'UL', font=F(14, 'label'), fill=DIM)
    _glow(d, LX+42, 86,  _fmtnet(ul), 22, EMBER, DFIRE, 'val')
    d.text((LX+10, 114), 'DL', font=F(14, 'label'), fill=DIM)
    _glow(d, LX+42, 110, _fmtnet(dl), 22, FIRE,  DFIRE, 'val')
    d.text((LX+10, 140), 'TOT', font=F(12, 'label'), fill=DIM)
    d.text((LX+42, 138), _fmtnet(ul + dl), font=F(16, 'val'), fill=DFIRE)

    _panel(d, LX, 190, LW, 78, title=' RAM')
    _glow(d, LX+10, 207, f"{ram_mb:,}", 30, FIRE, DFIRE, 'val')
    d.text((LX+10, 240), 'MB', font=F(12, 'label'), fill=DIM)
    d.text((LX+34, 238), f"{ram_gb:.1f}/{tot_gb:.0f}G", font=F(16, 'val'), fill=DFIRE)
    _bar(d, LX+10, 255, LW-20, 8, mem.percent, FIRE, DFIRE)

    # Cores mini-barras
    _panel(d, LX, 276, LW, 100, title=' CORES')
    if cpu_all:
        cores = cpu_all[:12]
        bw, bh, gap = 22, 36, 4
        col_count = 6 if len(cores) > 6 else len(cores)
        for i, pct in enumerate(cores):
            row = i // col_count; col_ = i % col_count
            bx_ = LX + 10 + col_ * (bw + gap)
            by_ = 290 + row * (bh + 6)
            bc  = _vc(pct)
            filled = int(bh * pct / 100)
            d.rectangle([bx_, by_, bx_+bw, by_+bh], fill=(10, 2, 2), outline=DFIRE)
            if filled > 0:
                d.rectangle([bx_, by_+bh-filled, bx_+bw, by_+bh], fill=bc)
            d.text((bx_+2, by_+2), f"{pct:.0f}", font=F(10, 'label'), fill=WHITE)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL DERECHO
    # ══════════════════════════════════════════════════════════════════════════
    RX, RW = 772, 182

    _panel(d, RX, 40, RW, 128, title=' DATE / TIME')
    d.text((RX+12, 58), now.strftime('%Y / %m / %d'), font=F(17, 'val'), fill=DFIRE)
    _glow(d, RX+8, 76, now.strftime('%H:%M'), 58, FIRE, DFIRE, 'teko')
    d.text((RX+12, 134), now.strftime(':%S'), font=F(20, 'val'), fill=DFIRE)
    d.text((RX+82, 137), now.strftime('%A')[:3].upper(), font=F(16, 'label'), fill=DIM)

    _panel(d, RX, 176, RW, 132, title=' GPU STATUS')
    if gt is not None:
        tc_ = _tc(gt)
        d.text((RX+12, 195), 'TEMP', font=F(13, 'label'), fill=DIM)
        _glow(d, RX+58, 190, f"{gt:.0f}°", 26, tc_, DFIRE, 'val')
    if gsclk:
        d.text((RX+12, 222), 'CLK',  font=F(13, 'label'), fill=DIM)
        _glow(d, RX+52, 218, f"{gsclk}", 26, EMBER, DFIRE, 'val')
        d.text((RX+108, 225), 'MHz', font=F(12, 'label'), fill=DIM)
    if vru is not None:
        d.text((RX+12, 250), 'VRAM', font=F(13, 'label'), fill=DIM)
        _glow(d, RX+65, 246, f"{vru}", 26, FIRE, DFIRE, 'val')
        d.text((RX+108, 252), f"/{vrt}M", font=F(13, 'label'), fill=DIM)
        _bar(d, RX+12, 278, RW-24, 8, vru / vrt * 100 if vrt else 0, FIRE, DFIRE)

    d.text((RX+12, 292), f"UP {uptime}", font=F(13, 'label'), fill=DIM)

    # ══════════════════════════════════════════════════════════════════════════
    # AMD RYZEN 9 BRANDING — bajo el gauge central
    # ══════════════════════════════════════════════════════════════════════════
    BY_B = 358
    # Líneas decorativas
    d.line([(195, BY_B), (757, BY_B)],   fill=DFIRE, width=1)
    d.line([(195, BY_B+1), (757, BY_B+1)], fill=VDFIRE, width=1)

    # Chevron AMD > centrado
    cx_ = 476
    for i, (x_off, y_off) in enumerate([(-14, 0), (-7, -7), (0, -14), (7, -7), (14, 0)]):
        col_c = EMBER if i < 2 else (FIRE if i == 2 else EMBER)
        d.ellipse([cx_+x_off-2, BY_B+12+y_off-2,
                   cx_+x_off+2, BY_B+12+y_off+2], fill=col_c)

    # "AMD  RYZEN 9" bicolor centrado
    bf   = F(38, 'teko')
    aw   = d.textbbox((0, 0), 'AMD  ', font=bf)[2]
    rw   = d.textbbox((0, 0), 'RYZEN 9', font=bf)[2]
    tot  = aw + rw; bx_ = cx_ - tot // 2
    for dx, dy in [(-2, -1), (2, -1), (-2, 1), (2, 1)]:
        d.text((bx_+dx,    BY_B+4+dy), 'AMD  ',   font=bf, fill=VDFIRE)
        d.text((bx_+aw+dx, BY_B+4+dy), 'RYZEN 9', font=bf, fill=VDFIRE)
    d.text((bx_,    BY_B+4), 'AMD  ',   font=bf, fill=EMBER)
    d.text((bx_+aw, BY_B+4), 'RYZEN 9', font=bf, fill=FIRE)

    _ctext(d, cx_, BY_B + 42, cpu_nm.upper(), 16, EMBER, VDFIRE, 'label')

    # ══════════════════════════════════════════════════════════════════════════
    # FRANJA INFERIOR — Discos
    # ══════════════════════════════════════════════════════════════════════════
    BY = 400
    d.line([(6, BY), (W-6, BY)], fill=DFIRE, width=1)

    disk_zones = [(8, 182), (770, 182)]
    for j, (mount, used, total, pct) in enumerate(disks[:2]):
        dx_, dw_ = disk_zones[j]
        dc  = _vc(pct)
        gb_u = used / 1024**3; gb_t = total / 1024**3
        _panel(d, dx_, BY+2, dw_, 72)
        d.text((dx_+10, BY+8), mount, font=F(15, 'label'), fill=DIM)
        _glow(d, dx_+10, BY+22, f"{pct:.0f}%", 30, dc, DFIRE, 'val')
        d.text((dx_+65, BY+27), f"{gb_u:.0f}/{gb_t:.0f}G", font=F(18, 'val'), fill=DFIRE)
        _bar(d, dx_+8, BY+57, dw_-16, 8, pct, dc, DFIRE)

    # Panel central inferior — frecuencia + uptime
    _panel(d, 390, BY+2, 184, 72, col=VDFIRE)
    if freq:
        _ctext(d, 476, BY+8,  f"{freq:.2f} GHz", 18, EMBER, DFIRE, 'val')
    _ctext(d, 476, BY+30, f"MEM {mem.percent:.0f}%", 15, FIRE, DFIRE, 'label')
    _bar(d, 398, BY+52, 168, 8, mem.percent, FIRE, DFIRE)

    # ══════════════════════════════════════════════════════════════════════════
    # MARCO GENERAL — rojo AMD
    # ══════════════════════════════════════════════════════════════════════════
    d.line([(0, 0),   (W, 0)],   fill=FIRE,  width=2)
    d.line([(0, 1),   (W, 1)],   fill=DFIRE, width=1)
    d.line([(0, H-1), (W, H-1)], fill=FIRE,  width=2)
    d.line([(0, H-2), (W, H-2)], fill=DFIRE, width=1)
    _corners(d, 0, 0, W-1, H-1, FIRE, sz=24, lw=2)

    # Divisores verticales
    for vx in [192, 762]:
        d.line([(vx, 40), (vx, H-82)], fill=DFIRE, width=1)
        for vy in [40, H//2, H-82]:
            d.ellipse([vx-3, vy-3, vx+3, vy+3], fill=FIRE)

    return img
