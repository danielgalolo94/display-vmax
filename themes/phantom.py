"""
Tema: PHANTOM — White HUD para gabinete blanco
Display landscape 960x480
Fondo blanco puro, paneles con accent bars de color,
gauge doble arco (CPU + temp), elementos que emergen del fondo.
"""
import math, random, datetime, subprocess, threading, time, socket
import psutil
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 960, 480
import os
_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS = os.path.join(_BASE, "assets")
_FD   = os.path.join(_BASE, "fonts")

_F_ORB = os.path.join(_FD, "Orbitron-Black.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_DAT = os.path.join(_FD, "NotoSansMono-Bold.ttf")
_F_MON = os.path.join(_FD, "ShareTechMono.ttf")
_F_NRD = os.path.join(_FD, "FiraCodeNerdFont-Medium.ttf")

_FC = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(p, s)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Fo = lambda s: _fnt(_F_ORB, s)
Fr = lambda s: _fnt(_F_RAJ, s)
Fd = lambda s: _fnt(_F_DAT, s)
Fm = lambda s: _fnt(_F_MON, s)
Fn = lambda s: _fnt(_F_NRD, s)

# ── Paleta ────────────────────────────────────────────────────────────────────
WHITE = (250, 251, 255)
INK   = (14,  18,  30)
INK2  = (58,  66,  88)
INK3  = (128, 136, 158)
DIVL  = (208, 213, 228)
CY    = (0,   182, 232)
ORG   = (242, 108,   0)
GRN   = (12,  192,  90)
PUR   = (118,  56, 238)
WARN  = (238, 158,   0)
CRIT  = (220,  40,  40)

# ── Sensores ──────────────────────────────────────────────────────────────────
def _cores():
    try:    return psutil.cpu_percent(percpu=True, interval=None)
    except: return [0.0] * 4

def _mem():   return psutil.virtual_memory()

def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp','coretemp','cpu_thermal','acpitz']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _gpu():
    try:
        r = subprocess.run(['cat','/sys/class/drm/card1/device/gpu_busy_percent'],
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
    for mount in ['/home', '/']:
        try:
            d = psutil.disk_usage(mount)
            return d, mount
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

def _cpu_name():
    try:
        with open('/proc/cpuinfo') as f:
            for line in f:
                if 'model name' in line:
                    n = line.split(':')[1].strip()
                    n = n.replace('(TM)','').replace('(R)','').replace(' CPU','')
                    return ' '.join(n.split()[:4])[:22]
    except: pass
    return "CPU"

def _gpu_name():
    try:
        r = subprocess.run(['cat','/sys/class/drm/card1/device/product_name'],
                           capture_output=True, text=True, timeout=1)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:18]
    except: pass
    return "GPU"

def _vram():
    try:
        u = int(open('/sys/class/drm/card1/device/mem_info_vram_used').read().strip())
        t = int(open('/sys/class/drm/card1/device/mem_info_vram_total').read().strip())
        return u / 1024**3, t / 1024**3
    except: return None, None

_ni = {'iface': None, 'ip': None, 'ts': 0.0}

def _net_info():
    if time.time() - _ni['ts'] < 10:
        return _ni['iface'], _ni['ip']
    try:
        stats    = psutil.net_if_stats()
        addrs    = psutil.net_if_addrs()
        counters = psutil.net_io_counters(pernic=True)
        best, best_b = None, 0
        for iface, cnt in counters.items():
            if iface == 'lo': continue
            if not stats.get(iface) or not stats[iface].isup: continue
            total = cnt.bytes_sent + cnt.bytes_recv
            if total > best_b:
                best_b, best = total, iface
        if best and best in addrs:
            for addr in addrs[best]:
                if addr.family == socket.AF_INET:
                    _ni.update({'iface': best[:10], 'ip': addr.address, 'ts': time.time()})
                    return _ni['iface'], _ni['ip']
    except: pass
    _ni['ts'] = time.time()
    return _ni.get('iface'), _ni.get('ip')

_nt  = [0, 0]
_ntx = [0] * 40
_nrx = [0] * 40

_dt  = [0, 0]
_dwr = [0] * 40
_drr = [0] * 40

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

def _volt():
    try:
        r = subprocess.run(['sensors'], capture_output=True, text=True, timeout=2)
        for line in r.stdout.split('\n'):
            if 'Vcore' in line or 'vccp' in line.lower():
                for p in line.split():
                    try:
                        v = float(p.replace('V','').replace('+',''))
                        if 0.4 < v < 2.5: return v
                    except: pass
    except: pass
    return None

# ── Actualizaciones pendientes (async, caché 10 min) ──────────────────────────
_upd = {'count': None, 'checking': False, 'ts': 0.0}

def _bg_check_updates():
    try:
        r = subprocess.run(
            ['dnf', 'check-update', '-q', '--cacheonly'],
            capture_output=True, text=True, timeout=15
        )
        # exit 100 = hay updates, 0 = sin updates, 1 = error
        if r.returncode in (0, 100):
            lines = [l for l in r.stdout.strip().splitlines()
                     if l and not l.startswith('Obsoleting') and not l.startswith('Last')]
            _upd['count'] = len(lines)
        else:
            # Si el caché falló, intentar sin --cacheonly
            r2 = subprocess.run(
                ['dnf', 'list', 'updates', '-q'],
                capture_output=True, text=True, timeout=30
            )
            lines = [l for l in r2.stdout.strip().splitlines()
                     if l and not l.startswith('Last') and not l.startswith('Obsoleting')]
            _upd['count'] = max(0, len(lines) - 1)  # -1 por el header
    except Exception:
        _upd['count'] = None
    finally:
        _upd['checking'] = False
        _upd['ts'] = time.time()

def _get_updates():
    now = time.time()
    if not _upd['checking'] and (now - _upd['ts']) > 600:
        _upd['checking'] = True
        _upd['ts'] = now
        threading.Thread(target=_bg_check_updates, daemon=True).start()
    return _upd['count']

# ── Color helpers ─────────────────────────────────────────────────────────────
def _vc(v, w=70, c=90):
    if v < w: return CY
    if v < c: return WARN
    return CRIT

def _tc(t):
    if t is None: return CY
    if t < 65:   return CY
    if t < 80:   return WARN
    return CRIT

def _tc_cpu(t):
    """Color temperatura para barras sobre fondo blanco."""
    if t is None: return INK3
    if t < 65:   return CY
    if t < 80:   return WARN
    return CRIT

# ── Primitivas ────────────────────────────────────────────────────────────────
def _ctr(d, cx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _right(d, rx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((rx-(bb[2]-bb[0]), y), txt, font=font, fill=col)

def _section(d, x, y, accent, label):
    """Label de sección con accent bar izquierda de 3px."""
    d.rectangle([x, y, x+3, y+26], fill=accent)
    d.text((x+9, y+3), label, font=Fr(22), fill=INK2)

def _badge(d, x, y, txt, col):
    """Badge redondeado con texto blanco."""
    f  = Fd(19)
    bb = d.textbbox((0,0), txt, font=f)
    bw = bb[2]-bb[0]+14
    bh = 30
    d.rounded_rectangle([x,y,x+bw,y+bh], radius=4, fill=col)
    d.text((x+7, y+5), txt, font=f, fill=WHITE)
    return bw

def _temp_badge(d, x, y, temp, col):
    return _badge(d, x, y, f"{temp:.0f}C", col)

def _fan_icon(d, cx, cy, r, angle, col, n_blades=4):
    """Ventilador animado con aspas curvas."""
    for i in range(n_blades):
        a0 = angle + i * (2*math.pi/n_blades)
        # Cada aspa: polígono de 4 puntos simulando curvatura
        pts = []
        for t in [0, 0.25, 0.55, 0.85, 1.0]:
            da  = t * (math.pi/n_blades) * 1.6
            dr  = r * (0.18 + 0.82*t)
            pts.append((cx + dr*math.cos(a0+da), cy + dr*math.sin(a0+da)))
        # ala de vuelta
        for t in [0.9, 0.6, 0.3, 0.05]:
            da  = t * (math.pi/n_blades) * 1.6 - 0.35
            dr  = r * (0.18 + 0.45*t)
            pts.append((cx + dr*math.cos(a0+da), cy + dr*math.sin(a0+da)))
        d.polygon(pts, fill=col)
    # Eje central
    d.ellipse([cx-r*0.16,cy-r*0.16,cx+r*0.16,cy+r*0.16], fill=INK)
    d.ellipse([cx-r*0.07,cy-r*0.07,cx+r*0.07,cy+r*0.07], fill=WHITE)

def _distro_logo(d, x, y, size, distro_id):
    """Logo de la distribución dibujado con PIL."""
    if distro_id == 'fedora':
        # Logo Fedora: círculo azul + "f" estilizado blanco
        r    = size//2
        blue = (60, 110, 220)
        d.ellipse([x,y,x+size,y+size], fill=blue)
        # La "f" de Fedora: trazo vertical + trazo horizontal curvo
        fw  = int(size*0.28)
        fh  = int(size*0.55)
        fx  = x + size//2 - fw//2 + 2
        fy  = y + int(size*0.18)
        lw  = max(2, size//10)
        # Palo vertical
        d.line([(fx+fw//2, fy),(fx+fw//2, fy+fh)], fill=WHITE, width=lw)
        # Trazo horizontal
        d.line([(fx, fy+int(fh*0.42)),(fx+fw, fy+int(fh*0.42))], fill=WHITE, width=lw)
        # Remate superior redondeado (arco)
        arc_r = fw//2
        d.arc([fx, fy, fx+fw, fy+fw], start=180, end=0, fill=WHITE, width=lw)
    elif distro_id in ('ubuntu',):
        orange = (235, 84, 12)
        d.ellipse([x,y,x+size,y+size], fill=orange)
        d.text((x+size//2-8, y+size//2-12), "U", font=Fr(size), fill=WHITE)
    elif distro_id in ('debian',):
        red = (210, 40, 60)
        d.ellipse([x,y,x+size,y+size], fill=red)
        d.text((x+size//2-8, y+size//2-12), "D", font=Fr(size), fill=WHITE)
    elif distro_id in ('arch',):
        blue2 = (30, 140, 210)
        d.ellipse([x,y,x+size,y+size], fill=blue2)
        d.text((x+size//2-8, y+size//2-12), "A", font=Fr(size), fill=WHITE)
    else:
        d.ellipse([x,y,x+size,y+size], fill=INK2)
        d.text((x+size//2-6, y+size//2-10), distro_id[0].upper(), font=Fr(size), fill=WHITE)

def _get_distro():
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('ID='):
                    return line.split('=')[1].strip().strip('"').lower()
    except: pass
    return 'linux'

_DISTRO   = _get_distro()
_HOSTNAME = socket.gethostname()

# ── Circuit traces animadas (pre-computed) ────────────────────────────────────
import random as _rph
_TRACES_PH = [(_rph.Random(i*17+1).randint(0, W-1),
               _rph.Random(i*17+2).randint(0, H-1),
               _rph.Random(i*17+3).randint(20, 120),   # length
               bool(_rph.Random(i*17+4).random() > 0.5),  # horizontal
               i % 60)   # phase offset
              for i in range(30)]

# ── Logos reales (cargados una vez al inicio) ─────────────────────────────────
_logo_distro = None   # Fedora / Ubuntu / etc.
_logo_cpu    = None   # AMD Ryzen

def _prep_logos():
    global _logo_distro, _logo_cpu
    try:
        src = os.path.join(_ASSETS, f"{_DISTRO}_logo.png")
        if not os.path.exists(src):
            src = os.path.join(_ASSETS, "fedora_logo.png")
        img = Image.open(src).convert("RGBA")
        h = 40; w = int(img.width * h / img.height)
        _logo_distro = img.resize((w, h), Image.LANCZOS)
    except Exception:
        pass
    # AMD Ryzen: negro sobre blanco → negro sobre transparente; invertir a blanco para top bar oscuro
    try:
        img  = Image.open(os.path.join(_ASSETS, "amd_ryzen_logo.png")).convert("RGBA")
        gray = img.convert("L")
        inv  = ImageOps.invert(gray)
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        white.putalpha(inv)
        bbox = white.getbbox()          # bbox correcto después de invertir
        if bbox: white = white.crop(bbox)
        h = 32; w = int(white.width * h / white.height)
        _logo_cpu = white.resize((w, h), Image.LANCZOS)
    except Exception:
        pass

_prep_logos()

def _hbar(d, x, y, w, h, pct, col):
    """Barra con track gris, fill con gradiente y bright-line al final."""
    d.rectangle([x,y,x+w,y+h], fill=(215,219,232))
    fw = int(pct/100*w)
    if fw > 0:
        for i in range(fw):
            t = 0.55 + 0.45*(i/fw)
            d.line([(x+i,y),(x+i,y+h)],
                fill=(min(255,int(col[0]*t)), min(255,int(col[1]*t)), min(255,int(col[2]*t))))
        d.line([(x+fw-1,y),(x+fw-1,y+h)], fill=WHITE)

def _spark(d, x, y, w, h, data, col):
    if not any(data): return
    mx = max(data) or 1
    n  = len(data)
    pts = [(x + int(i*w/(n-1)), y+h - int(v/mx*h)) for i,v in enumerate(data)]
    if len(pts) > 1:
        d.line(pts, fill=col, width=1)

def _divider(d, x, y, w):
    d.line([(x,y),(x+w,y)], fill=DIVL, width=1)

# ── Gauge doble arco ──────────────────────────────────────────────────────────
def _gauge(d, cx, cy, r, cpu, temp):
    S, SPAN = -220, 260
    AW = 22        # ancho arco CPU
    TW = 10        # ancho arco temperatura
    IR = r - 12    # radio interior del arco CPU
    TR = IR-AW-10  # radio arco temperatura

    # Sombra del gauge (luz desde arriba-izquierda)
    for ox,oy,gr in [(8,10,185),(6,8,200),(4,6,215),(2,4,228)]:
        d.ellipse([cx-r+ox,cy-r+oy,cx+r+ox,cy+r+oy], fill=(gr,gr,gr+6))

    # Anillo exterior sutil
    d.ellipse([cx-r-2,cy-r-2,cx+r+2,cy+r+2], fill=(222,226,238))
    # Fondo del gauge — blanco puro
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=WHITE)

    # Ticks escala
    N = 26
    for i in range(N+1):
        a   = math.radians(S + SPAN*i/N)
        big = (i % (N//5) == 0)
        r1  = r - (14 if big else 6)
        r2  = r + 2
        x1,y1 = cx+r1*math.cos(a), cy+r1*math.sin(a)
        x2,y2 = cx+r2*math.cos(a), cy+r2*math.sin(a)
        d.line([(x1,y1),(x2,y2)], fill=(INK if big else DIVL), width=(2 if big else 1))
        if big and 0 < i < N:
            pv = int(100*i/N)
            nf = Fm(14)
            nb = d.textbbox((0,0), str(pv), font=nf)
            nx = cx+(r+16)*math.cos(a)-(nb[2]-nb[0])//2
            ny = cy+(r+16)*math.sin(a)-(nb[3]-nb[1])//2
            d.text((nx,ny), str(pv), font=nf, fill=INK3)

    # ── Pista arco CPU ─────────────────────────────────────────────────────────
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+SPAN, fill=(208,212,226), width=AW)

    # Arco CPU
    arc_cpu = int(SPAN * max(cpu, 3) / 100)
    cpu_col  = ORG if cpu < 90 else CRIT
    # Halo tenue
    halo = tuple(min(255, c+160) for c in cpu_col)
    d.arc([cx-IR-5,cy-IR-5,cx+IR+5,cy+IR+5],
          start=S, end=S+arc_cpu, fill=halo, width=AW+12)
    # Arco principal
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+arc_cpu, fill=cpu_col, width=AW)
    # Bright line interna (efecto vidrio)
    d.arc([cx-IR+AW//2-2,cy-IR+AW//2-2,cx+IR-AW//2+2,cy+IR-AW//2+2],
          start=S, end=S+arc_cpu, fill=WHITE, width=2)
    # Dot punta
    tip_a = math.radians(S + arc_cpu)
    tx,ty = cx+IR*math.cos(tip_a), cy+IR*math.sin(tip_a)
    d.ellipse([tx-9,ty-9,tx+9,ty+9], fill=(235,238,248), outline=INK, width=2)
    d.ellipse([tx-4,ty-4,tx+4,ty+4], fill=INK)

    # ── Pista arco temperatura ─────────────────────────────────────────────────
    d.arc([cx-TR,cy-TR,cx+TR,cy+TR], start=S, end=S+SPAN, fill=(210,215,228), width=TW)
    if temp is not None:
        arc_t  = int(SPAN * min(temp, 100) / 100)
        tcol   = _tc(temp)
        d.arc([cx-TR,cy-TR,cx+TR,cy+TR], start=S, end=S+arc_t, fill=tcol, width=TW)

    # ── Fondo interior + número ────────────────────────────────────────────────
    NR = TR - TW - 10
    d.ellipse([cx-NR,cy-NR,cx+NR,cy+NR], fill=WHITE)

    vs   = f"{cpu:.0f}"
    fsz  = 96 if len(vs) < 3 else 80
    vf   = Fo(fsz)
    bb   = d.textbbox((0,0), vs, font=vf)
    tw2, th = bb[2]-bb[0], bb[3]-bb[1]
    vx   = cx - tw2//2 - bb[0]
    vy   = cy - th//2  - bb[1] - 8
    d.text((vx, vy), vs, font=vf, fill=INK)
    # %
    d.text((cx+tw2//2+3, vy+fsz//2+4), "%", font=Fr(26), fill=INK2)
    # label
    _ctr(d, cx, cy+NR-26, "CPU LOAD", Fr(18), INK2)

    # Leyenda de arcos
    d.text((cx-r+8, cy-10), "CPU%", font=Fm(18), fill=cpu_col)


# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    if frame % 2 == 0:
        _update_net()
        _update_disk_io()

    img = Image.new('RGB', (W, H), WHITE)
    d   = ImageDraw.Draw(img)

    # Dot grid
    for x in range(20, W, 32):
        for y in range(20, H, 32):
            d.point((x, y), fill=(218, 222, 234))

    # Trazos de circuito animados — azul claro sobre fondo blanco
    for tx, ty, tlen, horiz, phase in _TRACES_PH:
        t_phase = (frame + phase) % 40
        if t_phase < 20:
            alpha = int(t_phase * 3)
        else:
            alpha = int((40 - t_phase) * 3)
        alpha = min(alpha, 35)
        if alpha < 5:
            continue
        col = (alpha, alpha + 10, min(255, alpha + 30))
        if horiz:
            d.line([(tx, ty), (tx + tlen, ty)], fill=col, width=1)
        else:
            d.line([(tx, ty), (tx, ty + tlen)], fill=col, width=1)

    # Leer datos
    cores  = _cores()
    cpu    = sum(cores)/len(cores) if cores else 0.0
    mem    = _mem()
    ct     = _temp()
    gpu    = _gpu()
    gt     = _gtemp()
    disk, disk_mount = _disk()
    freq   = _freq()
    fan    = _fan()
    volt   = _volt()
    now    = datetime.datetime.now()
    pulse  = abs(math.sin(frame * 0.09))
    cpu_nm = _cpu_name()
    gpu_nm = _gpu_name() if gpu is not None else "GPU"

    # ── TOP BAR (60px) ────────────────────────────────────────────────────────
    TB = 60
    d.rectangle([0,0,W,TB], fill=INK)
    # Línea accent inferior
    d.rectangle([0,TB-2,W,TB], fill=CY)

    # Dot parpadeante + hostname
    blink = CY if (frame % 14) < 9 else (0, 80, 110)
    d.ellipse([12,10,28,26], fill=blink, outline=(0,130,180), width=1)
    d.text((36, 7),  _HOSTNAME[:18].upper(), font=Fr(24), fill=(232,238,252))
    d.text((36, 32), cpu_nm,                  font=Fr(20), fill=(140,155,190))

    # Logo distro → izquierda del reloj | Logo CPU → derecha del reloj
    if _logo_distro:
        ly = (TB - _logo_distro.height) // 2
        lx = W//2 - _logo_distro.width - 100
        img.paste(_logo_distro, (lx, ly), _logo_distro)
    if _logo_cpu:
        ly = (TB - _logo_cpu.height) // 2
        img.paste(_logo_cpu, (W//2 + 100, ly), _logo_cpu)

    # Hora central — grande
    ts  = now.strftime("%H:%M:%S")
    tf  = Fo(28)
    tb2 = d.textbbox((0,0), ts, font=tf)
    _ctr(d, W//2, 14, ts, tf, CY)
    _ctr(d, W//2, 42, now.strftime("%a %d/%m/%Y"), Fr(16), (110,125,165))

    # Actualizaciones — derecha del top bar
    upd_count = _get_updates()
    if upd_count is None and _upd['checking']:
        d.text((W-130, 10), "checking",   font=Fm(13), fill=(60,75,110))
        d.text((W-130, 28), "updates...", font=Fm(13), fill=(60,75,110))
    elif upd_count and upd_count > 0:
        alert_col = WARN if upd_count < 20 else CRIT
        glow = tuple(min(255, c//2) for c in alert_col)
        if (frame % 16) < 12:
            d.rectangle([W-157, 2, W-5, TB-2], fill=glow)
        d.rectangle([W-154, 4, W-8, TB-4], fill=(20, 24, 45))
        d.rectangle([W-154, 4, W-8, TB-4], outline=alert_col, width=2)
        _ctr(d, W-81, 8,  str(upd_count), Fo(26), alert_col)
        _ctr(d, W-81, 38, "UPDATES",       Fr(14), alert_col)
    elif upd_count == 0:
        _badge(d, W-90, 16, "✓ al día", GRN)
    else:
        d.text((W-100, 22), "updates N/A", font=Fm(12), fill=(55,68,100))

    # ── LAYOUT ───────────────────────────────────────────────────────────────
    # Sin bottom bar → UB = H. Gauge más espacio vertical.
    UY = TB + 5   # = 65
    UB = H        # = 480  (sin bottom bar)
    LX, LW = 12, 190
    RX, RW = W-12-190, 190
    MX  = LX+LW+6
    MW  = RX-MX-6
    GCX = MX + MW//2
    GCY = UY + 190   # = 255  (más centrado con el espacio ganado)
    GR  = 162        # más grande sin bottom bar

    # ── GAUGE ─────────────────────────────────────────────────────────────────
    _gauge(d, GCX, GCY, GR, cpu, ct)

    # Líneas decorativas horizontales desde el gauge al borde del centro
    ga_l = GCX - GR - 6
    ga_r = GCX + GR + 6
    d.line([(MX+4, GCY),(ga_l, GCY)], fill=DIVL, width=1)
    d.line([(ga_r, GCY),(MX+MW-4, GCY)], fill=DIVL, width=1)
    d.ellipse([ga_l-3,GCY-3,ga_l+3,GCY+3], fill=INK3)
    d.ellipse([ga_r-3,GCY-3,ga_r+3,GCY+3], fill=INK3)

    # ── Reloj — línea compacta bajo el gauge (ya está en el top bar) ─────────
    # Solo fecha para no repetir hora
    CLK_Y = GCY + GR + 10
    _ctr(d, GCX, CLK_Y+4, now.strftime("%A  %d / %m / %Y"), Fr(17), INK3)

    # ── PANEL IZQUIERDO ───────────────────────────────────────────────────────
    py = UY

    # CPU
    _section(d, LX, py, CY, "CPU")
    cc = ORG if cpu >= 70 else INK
    d.text((LX+9, py+28), f"{cpu:.1f}%", font=Fo(46), fill=cc)
    if ct is not None:
        _temp_badge(d, LX+LW-66, py+30, ct, _tc(ct))
    if freq:
        d.text((LX+9, py+78), f"{freq.current/1000:.2f} GHz", font=Fd(17), fill=INK3)
    _hbar(d, LX+9, py+96, LW-18, 12, cpu, CY if cpu<70 else ORG)
    py += 108
    _divider(d, LX, py, LW)
    py += 6

    # MEMORIA
    _section(d, LX, py, GRN, "MEMORIA")
    ram = (mem.total-mem.available)/1024**3
    tot = mem.total/1024**3
    rc  = GRN if mem.percent < 80 else WARN
    d.text((LX+9, py+28), f"{ram:.1f}G", font=Fo(42), fill=rc)
    _right(d, LX+LW-4, py+44, f"/{tot:.0f}G", Fd(16), INK3)
    _hbar(d, LX+9, py+76, LW-18, 12, mem.percent, GRN)
    d.text((LX+9, py+92), f"{mem.percent:.0f}%  {ram:.1f}/{tot:.0f} GB", font=Fm(16), fill=INK3)
    py += 106
    _divider(d, LX, py, LW)
    py += 6

    # DISCO
    _section(d, LX, py, ORG, f"DISCO  {disk_mount}")
    if disk:
        dc  = ORG if disk.percent < 80 else CRIT
        dg  = disk.used/1024**3
        dt  = disk.total/1024**3
        d.text((LX+9, py+28), f"{dg:.0f}G", font=Fo(36), fill=dc)
        _right(d, LX+LW-4, py+42, f"/{dt:.0f}G", Fd(15), INK3)
        _hbar(d, LX+9, py+72, LW-18, 12, disk.percent, ORG)
        d.text((LX+9, py+88), f"{disk.percent:.0f}%  libre: {dt-dg:.0f}G", font=Fm(16), fill=INK3)
        py += 100
    else:
        d.text((LX+9, py+28), "N/A", font=Fo(30), fill=INK3)
        py += 52
    _divider(d, LX, py, LW)
    py += 6

    # RED
    _section(d, LX, py, PUR, "RED")
    tx_v = _ntx[-1]; rx_v = _nrx[-1]
    iface, ip = _net_info()
    d.text((LX+9, py+28), f"UP {_fmt(tx_v)}/s", font=Fd(20), fill=PUR)
    d.text((LX+9, py+52), f"DL {_fmt(rx_v)}/s", font=Fd(20), fill=INK3)

    # ── PANEL DERECHO ─────────────────────────────────────────────────────────
    py = UY

    # GPU
    _section(d, RX, py, CY, "GPU")
    vu, vt = _vram()
    if gpu is not None:
        gc  = CY if gpu < 70 else WARN
        d.text((RX+9, py+28), f"{gpu:.1f}%", font=Fo(42), fill=gc)
        if gt is not None:
            _temp_badge(d, RX+RW-66, py+30, gt, _tc(gt))
        _hbar(d, RX+9, py+76, RW-18, 12, gpu, CY)
        if vu is not None:
            d.text((RX+9, py+92), f"VRAM {vu:.1f}/{vt:.0f}G", font=Fm(16), fill=INK3)
        else:
            d.text((RX+9, py+92), gpu_nm, font=Fm(16), fill=INK3)
    else:
        d.text((RX+9, py+28), "--", font=Fo(36), fill=INK3)
        d.text((RX+9, py+68), "sin GPU detectada", font=Fm(16), fill=INK3)
    py += 108
    _divider(d, RX, py, RW)
    py += 6

    # DISCO IO
    _section(d, RX, py, ORG, "DISCO IO")
    wr_now  = _dwr[-1]
    rd_now  = _drr[-1]
    writing = wr_now > 500_000
    wr_col  = (ORG if (frame % 8) < 5 else WARN) if writing else INK2
    d.text((RX+9, py+28), f"WR {_fmt(wr_now)}", font=Fo(30), fill=wr_col)
    d.text((RX+9, py+60), f"RD {_fmt(rd_now)}", font=Fd(18), fill=INK3)
    if writing and (frame % 8) < 5:
        d.ellipse([RX+RW-20, py+56, RX+RW-2, py+74],
                  fill=tuple(min(255, c+160) for c in ORG))
        d.ellipse([RX+RW-17, py+59, RX+RW-5, py+71], fill=ORG)
    else:
        d.ellipse([RX+RW-17, py+59, RX+RW-5, py+71], fill=DIVL)
    py += 82
    _divider(d, RX, py, RW)
    py += 6

    # FAN + temperatura CPU
    _section(d, RX, py, PUR, "FAN")
    rpm_known  = fan is not None
    spin_speed = fan/1200 if rpm_known else 0.4
    fan_angle  = frame * 0.1 * spin_speed * math.pi
    fan_col    = PUR if not rpm_known else (CY if fan < 2500 else WARN if fan < 3500 else CRIT)
    fan_sz     = 34

    _fan_icon(d, RX+RW-fan_sz-6, py+38, fan_sz, fan_angle, fan_col)

    if rpm_known:
        fc = CY if fan < 2500 else WARN if fan < 3500 else CRIT
        d.text((RX+9, py+28), str(fan), font=Fo(34), fill=fc)
        d.text((RX+9, py+66), "RPM", font=Fr(22), fill=INK3)
        if ct is not None:
            d.text((RX+9, py+88), f"CPU {ct:.1f}C", font=Fd(16), fill=_tc(ct))
    else:
        if ct is not None:
            tc2 = _tc(ct)
            d.text((RX+9, py+26), f"{ct:.1f}", font=Fo(38), fill=tc2)
            d.text((RX+9, py+66), "°C  CPU", font=Fr(22), fill=INK3)
            _hbar(d, RX+9, py+88, RW-fan_sz*2-20, 8, min(ct, 100), tc2)
        else:
            d.text((RX+9, py+28), "sin sensor", font=Fm(16), fill=INK3)
    py += 102
    _divider(d, RX, py, RW)
    py += 6

    # SISTEMA (load avg + uptime combinados)
    _section(d, RX, py, GRN, "SISTEMA")
    la  = os.getloadavg()
    nc  = psutil.cpu_count() or 4
    lc  = GRN if la[0] < nc*0.7 else WARN if la[0] < nc else CRIT
    d.text((RX+9,      py+28), f"{la[0]:.2f}", font=Fo(28), fill=lc)
    d.text((RX+9+68,   py+32), f"{la[1]:.2f}", font=Fd(18), fill=INK2)
    d.text((RX+9+118,  py+32), f"{la[2]:.2f}", font=Fd(18), fill=INK3)
    d.text((RX+9,      py+52), "1m",  font=Fm(14), fill=lc)
    d.text((RX+9+68,   py+52), "5m",  font=Fm(14), fill=INK3)
    d.text((RX+9+118,  py+52), "15m", font=Fm(14), fill=INK3)
    uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um = divmod(int(uptime.total_seconds())//60, 60)
    d.text((RX+9, py+70), f"{uh}h {um:02d}m", font=Fo(22), fill=INK)

    return img
