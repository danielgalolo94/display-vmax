"""
Tema: PHANTOM GLASS — Glassmorphism HUD
Display landscape 960x480
Fondo degradado oscuro, paneles de vidrio esmerilado,
gauge de anillo de cristal con refracción lumínica.
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

# ── Semantic Color System ────────────────────────────────────────────────────
S_BG_TOP  = (5,   4,  25)
S_BG_BOT  = (12, 10,  38)

T_PRI     = (238, 241, 255)
T_SEC     = (165, 175, 220)
T_TRT     = (95,  105, 158)

A_CPU     = (0,   210, 255)
A_MEM     = (45,  235, 145)
A_DISK    = (255, 185, 55)
A_NET     = (140, 85,  255)
A_GPU     = (0,   210, 255)
A_IO      = (255, 185, 55)
A_FAN     = (140, 85,  255)

S_GOOD    = A_MEM
S_WARN    = (255, 200, 40)
S_CRIT    = (255, 60,  60)
S_INFO    = A_CPU

GL_BASE   = (18,  16,  48)
GL_DARK   = (24,  22,  55)
GL_EDGE   = (58,  53,  108)
GL_TOP    = (108, 103, 168)
GL_SHADOW = (6,   5,   22)
GL_ACCENT = (80,  75,  140)

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

_upd = {'count': None, 'checking': False, 'ts': 0.0}

def _bg_check_updates():
    try:
        r = subprocess.run(
            ['dnf', 'check-update', '-q', '--cacheonly'],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode in (0, 100):
            lines = [l for l in r.stdout.strip().splitlines()
                     if l and not l.startswith('Obsoleting') and not l.startswith('Last')]
            _upd['count'] = len(lines)
        else:
            r2 = subprocess.run(
                ['dnf', 'list', 'updates', '-q'],
                capture_output=True, text=True, timeout=30
            )
            lines = [l for l in r2.stdout.strip().splitlines()
                     if l and not l.startswith('Last') and not l.startswith('Obsoleting')]
            _upd['count'] = max(0, len(lines) - 1)
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

# ── Status color helpers ─────────────────────────────────────────────────────
def _status_from_val(v, warn=70, crit=90, col_g=S_GOOD, col_w=S_WARN, col_c=S_CRIT):
    if v < warn: return col_g
    if v < crit: return col_w
    return col_c

def _status_from_temp(t):
    if t is None: return S_INFO
    if t < 65:   return S_GOOD
    if t < 80:   return S_WARN
    return S_CRIT

# ── Glass primitives ─────────────────────────────────────────────────────────
def _glass_panel(d, x, y, w, h, r=12):
    d.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=GL_BASE)
    d.rounded_rectangle([x, y, x+w, y+h], radius=r,
                        outline=GL_EDGE, width=1)
    d.line([(x+r//2, y+1), (x+w-r//2, y+1)], fill=GL_TOP, width=1)
    d.line([(x+1, y+r//2), (x+1, y+h-r//2)], fill=GL_ACCENT, width=1)
    d.line([(x+r//2, y+h-1), (x+w-r//2, y+h-1)], fill=GL_SHADOW, width=1)

def _glass_highlight(im, d, x, y, w, h, r=12):
    grad = Image.new('RGBA', (w//2, h//2), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(min(w//2, h//2)):
        a = max(0, 35 - int(i * 1.5))
        gd.ellipse([-i, -i, w//2+i, h//2+i], fill=(255, 255, 255, a))
    im.paste(grad, (x, y), grad)

def _light_leak(d, frame):
    for i in range(4):
        ox = (frame * 1.5 + i * 280 + i * 70) % (W + 200) - 100
        alpha = 6 + 3 * abs(math.sin(frame * 0.015 + i * 1.2))
        for step in range(80):
            x = ox + step * 2.5
            y = int(step * 0.6) + 40
            if 0 <= x < W and 0 <= y < H:
                decay = max(0, 1 - step / 80)
                a = int(alpha * decay)
                col = (
                    min(255, int(120 + 30 * abs(math.sin(i * 1.3)))),
                    min(255, int(100 + 40 * abs(math.sin(i * 1.7)))),
                    min(255, int(200 + 55 * abs(math.sin(i * 2.1)))),
                )
                d.line([(x, max(0, y-40)), (x, min(H-1, y+40))],
                       fill=(col[0]//2, col[1]//2, col[2]//2), width=2)
                d.line([(x, max(0, y-20)), (x, min(H-1, y+20))],
                       fill=(col[0], col[1], col[2]), width=1)

def _light_leak_horizontal(d, frame):
    for i in range(2):
        x = (frame * 0.7 + i * 500) % (W + 100) - 50
        for step in range(100):
            y = int(step * 0.8)
            if 0 <= x < W and 0 <= y < H:
                decay = max(0, 1 - step / 100)
                a = int(15 * decay)
                d.line([(x, y), (x+30, y)], fill=(255, 255, 255, a), width=1)

# ── Drawing helpers ──────────────────────────────────────────────────────────
def _ctr(d, cx, y, txt, font, fill):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=fill)

def _right(d, rx, y, txt, font, fill):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((rx-(bb[2]-bb[0]), y), txt, font=font, fill=fill)

def _section(d, x, y, suffix_y, accent, label):
    d.rectangle([x, y, x+3, y+26], fill=accent)
    d.text((x+9, y+3), label, font=Fr(22), fill=T_SEC)

def _badge(d, x, y, txt, col):
    f  = Fd(19)
    bb = d.textbbox((0,0), txt, font=f)
    bw = bb[2]-bb[0]+16
    bh = 30
    d.rounded_rectangle([x, y, x+bw, y+bh], radius=5,
                        fill=(col[0]//6, col[1]//6, col[2]//6))
    d.rounded_rectangle([x, y, x+bw, y+bh], radius=5,
                        outline=col, width=1)
    d.text((x+8, y+5), txt, font=f, fill=col)
    return bw

def _hbar(d, x, y, w, h, pct, col):
    d.rounded_rectangle([x, y, x+w, y+h], radius=h//2, fill=(28, 26, 60))
    fw = int(pct/100*w)
    if fw > 0:
        glow = tuple(min(255, c//3) for c in col)
        d.rounded_rectangle([x, y, x+fw, y+h], radius=h//2, fill=glow)
        d.rounded_rectangle([x, y, x+fw, y+h], radius=h//2, fill=col)
        d.line([(x+fw-1, y+1), (x+fw-1, y+h-1)], fill=(255, 255, 255, 60), width=1)

def _spark(d, x, y, w, h, data, col):
    if not any(data): return
    mx = max(data) or 1
    n  = len(data)
    pts = [(x + int(i*w/(n-1)), y+h - int(v/mx*h)) for i,v in enumerate(data)]
    if len(pts) > 1:
        d.line(pts, fill=col, width=1)

def _divider(d, x, y, w):
    d.line([(x,y),(x+w,y)], fill=(38, 36, 75), width=1)

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

import random as _rph
_TRACES = [(_rph.Random(i*17+1).randint(0, W-1),
            _rph.Random(i*17+2).randint(0, H-1),
            _rph.Random(i*17+3).randint(20, 120),
            bool(_rph.Random(i*17+4).random() > 0.5),
            i % 60)
           for i in range(24)]

_LOGO_DISTRO = None
_LOGO_CPU    = None

def _draw_distro_icon(size=36):
    with open('/etc/os-release') as f:
        distro_id = 'linux'
        for line in f:
            if line.startswith('ID='):
                distro_id = line.split('=')[1].strip().strip('"').lower()
                break
    src_path = os.path.join(_ASSETS, f"{distro_id}_logo.png")
    if os.path.exists(src_path):
        try:
            img = Image.open(src_path).convert("RGBA")
            h = size; w = int(img.width * h / img.height)
            return img.resize((w, h), Image.LANCZOS)
        except:
            pass
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = size // 2
    if distro_id in ('arch',):
        blue = (23, 147, 209)
        r = size // 2 - 1
        pts = []
        for i in range(6):
            a = math.radians(-90 + i * 60)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=blue)
        d.text((cx-6, cy-8), "A", font=Fo(size//2+2), fill=(255, 255, 255))
    else:
        d.ellipse([2, 2, size-2, size-2], fill=GL_ACCENT)
        d.text((cx-5, cy-8), distro_id[0].upper(), font=Fo(size//2), fill=(255, 255, 255))
    return img

def _prep_logos():
    global _LOGO_DISTRO, _LOGO_CPU
    _LOGO_DISTRO = _draw_distro_icon(36)
    try:
        img  = Image.open(os.path.join(_ASSETS, "amd_ryzen_logo.png")).convert("RGBA")
        gray = img.convert("L")
        inv  = ImageOps.invert(gray)
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        white.putalpha(inv)
        bbox = white.getbbox()
        if bbox: white = white.crop(bbox)
        h = 28; w = int(white.width * h / white.height)
        _LOGO_CPU = white.resize((w, h), Image.LANCZOS)
    except: pass

_prep_logos()

# ── Gauge ────────────────────────────────────────────────────────────────────
def _gauge(d, cx, cy, r, cpu, temp):
    S, SPAN = -220, 260
    AW = 22
    TW = 10
    IR = r - 12
    TR = IR - AW - 10

    r_bg = r + 20
    d.ellipse([cx-r_bg, cy-r_bg, cx+r_bg, cy+r_bg], fill=(12, 10, 38))
    for i in range(6):
        s = r_bg - 1 - i
        d.ellipse([cx-s, cy-s, cx+s, cy+s],
                  fill=(15+2*i, 13+2*i, 42+3*i))

    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(10, 8, 34))
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(48, 46, 95, 60), width=1)

    N = 26
    for i in range(N+1):
        a   = math.radians(S + SPAN*i/N)
        big = (i % (N//5) == 0)
        r1  = r - (12 if big else 5)
        r2  = r + 2
        x1,y1 = cx+r1*math.cos(a), cy+r1*math.sin(a)
        x2,y2 = cx+r2*math.cos(a), cy+r2*math.sin(a)
        tick_col = T_SEC if big else (48, 46, 88)
        d.line([(x1,y1),(x2,y2)], fill=tick_col, width=(2 if big else 1))
        if big and 0 < i < N:
            pv = int(100*i/N)
            nf = Fm(11)
            nb = d.textbbox((0,0), str(pv), font=nf)
            nx = cx+(r+15)*math.cos(a)-(nb[2]-nb[0])//2
            ny = cy+(r+15)*math.sin(a)-(nb[3]-nb[1])//2
            d.text((nx,ny), str(pv), font=nf, fill=T_TRT)

    track_col = (26, 24, 58)
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+SPAN, fill=track_col, width=AW)

    arc_cpu = int(SPAN * max(cpu, 3) / 100)
    cpu_col = A_CPU if cpu < 90 else S_CRIT
    for gr in [IR+8, IR+4, IR]:
        gw = AW + (IR+8-gr)*3
        ga = max(15, 35 - (IR+8-gr)*5)
        d.arc([cx-gr, cy-gr, cx+gr, cy+gr],
              start=S, end=S+arc_cpu,
              fill=(cpu_col[0]//3, cpu_col[1]//3, cpu_col[2]//3, ga), width=gw)
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR],
          start=S, end=S+arc_cpu, fill=cpu_col, width=AW)
    d.arc([cx-IR+AW//2-2,cy-IR+AW//2-2,cx+IR-AW//2+2,cy+IR-AW//2+2],
          start=S, end=S+arc_cpu, fill=(255, 255, 255, 60), width=2)

    tip_a = math.radians(S + arc_cpu)
    tx,ty = cx+IR*math.cos(tip_a), cy+IR*math.sin(tip_a)
    for gt, ga in [(13, 25), (9, 50), (5, 80)]:
        d.ellipse([tx-gt, ty-gt, tx+gt, ty+gt],
                  fill=(cpu_col[0]//4, cpu_col[1]//4, cpu_col[2]//4, ga))
    d.ellipse([tx-9, ty-9, tx+9, ty+9],
              fill=(20, 18, 52), outline=cpu_col, width=2)
    d.ellipse([tx-4, ty-4, tx+4, ty+4], fill=cpu_col)

    d.arc([cx-TR,cy-TR,cx+TR,cy+TR], start=S, end=S+SPAN, fill=track_col, width=TW)
    if temp is not None:
        arc_t = int(SPAN * min(temp, 100) / 100)
        tcol  = _status_from_temp(temp)
        d.arc([cx-TR-2,cy-TR-2,cx+TR+2,cy+TR+2],
              start=S, end=S+arc_t, fill=(tcol[0]//2, tcol[1]//2, tcol[2]//2, 40), width=TW+4)
        d.arc([cx-TR,cy-TR,cx+TR,cy+TR],
              start=S, end=S+arc_t, fill=tcol, width=TW)

    NR = TR - TW - 10
    d.ellipse([cx-NR, cy-NR, cx+NR, cy+NR], fill=(14, 12, 40))
    d.ellipse([cx-NR, cy-NR, cx+NR, cy+NR], outline=(48, 46, 95, 40), width=1)

    vs   = f"{cpu:.0f}"
    fsz  = 96 if len(vs) < 3 else 80
    vf   = Fo(fsz)
    bb   = d.textbbox((0,0), vs, font=vf)
    tw2, th = bb[2]-bb[0], bb[3]-bb[1]
    vx   = cx - tw2//2 - bb[0]
    vy   = cy - th//2  - bb[1] - 8
    for off in [(2,2),(-2,2),(2,-2),(-2,-2)]:
        d.text((vx+off[0], vy+off[1]), vs, font=vf,
               fill=(cpu_col[0]//6, cpu_col[1]//6, cpu_col[2]//6))
    d.text((vx, vy), vs, font=vf, fill=T_PRI)
    d.text((cx+tw2//2+3, vy+fsz//2+4), "%", font=Fr(26), fill=T_SEC)
    _ctr(d, cx, cy+NR-26, "CPU LOAD", Fr(18), T_SEC)
    d.text((cx-r+8, cy-10), "CPU", font=Fm(9), fill=cpu_col)
    if temp is not None:
        d.text((cx-TR+4, cy-6), "TEMP", font=Fm(8), fill=_status_from_temp(temp))

# ── Panel helpers ────────────────────────────────────────────────────────────
_SECT_GAP = 4
_SECT_TOP = 8

def _draw_cpu_section(d, x, w, py, cpu, freq, ct):
    _section(d, x+8, py+_SECT_TOP, py, A_CPU, "CPU")
    cc = _status_from_val(cpu, 70, 90, T_PRI, S_WARN, S_CRIT)
    d.text((x+17, py+36), f"{cpu:.1f}%", font=Fo(46), fill=cc)
    y2 = py + 86
    if freq:
        d.text((x+17, y2), f"{freq.current/1000:.2f} GHz", font=Fd(17), fill=T_TRT)
    if ct is not None:
        _right(d, x+w-12, y2, f"{ct:.1f}C", font=Fd(17), fill=_status_from_temp(ct))
    _hbar(d, x+17, py+104, w-34, 10, cpu, A_CPU if cpu<70 else S_WARN)
    return py + 120

def _draw_mem_section(d, x, w, py, mem):
    _section(d, x+8, py+_SECT_TOP, py, A_MEM, "MEMORIA")
    ram = (mem.total-mem.available)/1024**3
    tot = mem.total/1024**3
    rc = _status_from_val(mem.percent, 80, 95, A_MEM, S_WARN, S_CRIT)
    d.text((x+17, py+28), f"{ram:.1f}G", font=Fo(42), fill=rc)
    _right(d, x+w-12, py+44, f"/{tot:.0f}G", Fd(16), T_TRT)
    _hbar(d, x+17, py+76, w-34, 10, mem.percent, A_MEM)
    d.text((x+17, py+92), f"{mem.percent:.0f}%  {ram:.1f}/{tot:.0f} GB", font=Fm(16), fill=T_TRT)
    return py + 108

def _draw_disk_section(d, x, w, py, disk, disk_mount):
    _section(d, x+8, py+_SECT_TOP, py, A_DISK, f"DISCO  {disk_mount}")
    if disk:
        dc = _status_from_val(disk.percent, 80, 95, A_DISK, S_WARN, S_CRIT)
        dg  = disk.used/1024**3
        dt  = disk.total/1024**3
        d.text((x+17, py+28), f"{dg:.0f}G", font=Fo(36), fill=dc)
        _right(d, x+w-12, py+42, f"/{dt:.0f}G", Fd(15), T_TRT)
        _hbar(d, x+17, py+72, w-34, 10, disk.percent, A_DISK)
        d.text((x+17, py+88), f"{disk.percent:.0f}%  libre: {dt-dg:.0f}G", font=Fm(16), fill=T_TRT)
        py += 100
    else:
        d.text((x+17, py+28), "N/A", font=Fo(30), fill=T_TRT)
        py += 52
    return py

def _draw_net_section(d, x, w, py):
    _section(d, x+8, py+_SECT_TOP, py, A_NET, "RED")
    tx_v = _ntx[-1]; rx_v = _nrx[-1]
    iface, ip = _net_info()
    d.text((x+17, py+28), f"UP {_fmt(tx_v)}/s", font=Fd(20), fill=A_NET)
    d.text((x+17, py+52), f"DL {_fmt(rx_v)}/s", font=Fd(20), fill=T_TRT)
    return py + 80

def _draw_gpu_section(d, x, w, py, gpu, gpu_nm, gt):
    _section(d, x+8, py+_SECT_TOP, py, A_GPU, "GPU")
    vu, vt = _vram()
    if gpu is not None:
        gc = _status_from_val(gpu, 70, 90, A_GPU, S_WARN, S_CRIT)
        d.text((x+17, py+36), f"{gpu:.1f}%", font=Fo(42), fill=gc)
        _hbar(d, x+17, py+84, w-34, 10, gpu, A_GPU)
        y_info = py + 96
        if vu is not None:
            d.text((x+17, y_info), f"VRAM {vu:.1f}/{vt:.0f}G", font=Fm(16), fill=T_TRT)
        else:
            d.text((x+17, y_info), gpu_nm, font=Fm(16), fill=T_TRT)
        if gt is not None:
            _right(d, x+w-12, y_info, f"{gt:.1f}C", font=Fd(16), fill=_status_from_temp(gt))
    else:
        d.text((x+17, py+36), "--", font=Fo(36), fill=T_TRT)
        d.text((x+17, py+76), "sin GPU detectada", font=Fm(16), fill=T_TRT)
    return py + 118

def _draw_io_section(d, x, w, py, frame):
    _section(d, x+8, py+_SECT_TOP, py, A_IO, "DISCO IO")
    wr_now  = _dwr[-1]
    rd_now  = _drr[-1]
    writing = wr_now > 500_000
    wr_col  = (A_IO if (frame % 8) < 5 else S_WARN) if writing else T_SEC
    d.text((x+17, py+28), f"WR {_fmt(wr_now)}", font=Fo(30), fill=wr_col)
    d.text((x+17, py+60), f"RD {_fmt(rd_now)}", font=Fd(18), fill=T_TRT)
    if writing and (frame % 8) < 5:
        d.ellipse([x+w-20, py+56, x+w-2, py+74],
                  fill=(A_IO[0]//3, A_IO[1]//3, A_IO[2]//3))
        d.ellipse([x+w-17, py+59, x+w-5, py+71], fill=A_IO)
    else:
        d.ellipse([x+w-17, py+59, x+w-5, py+71], fill=(38, 36, 75))
    return py + 82

def _draw_fan_section(d, x, w, py, fan, ct, frame):
    _section(d, x+8, py+_SECT_TOP, py, A_FAN, "FAN")
    rpm_known  = fan is not None
    spin_speed = fan/1200 if rpm_known else 0.4
    fan_angle  = frame * 0.1 * spin_speed * math.pi
    fan_col    = A_FAN if not rpm_known else (A_CPU if fan < 2500 else S_WARN if fan < 3500 else S_CRIT)
    fan_sz     = 34
    _fan_icon(d, x+w-fan_sz-14, py+40, fan_sz, fan_angle, fan_col)
    if rpm_known:
        fc = A_CPU if fan < 2500 else S_WARN if fan < 3500 else S_CRIT
        d.text((x+17, py+28), str(fan), font=Fo(34), fill=fc)
        d.text((x+17, py+66), "RPM", font=Fr(22), fill=T_TRT)
        if ct is not None:
            d.text((x+17, py+88), f"CPU {ct:.1f}C", font=Fd(16), fill=_status_from_temp(ct))
    else:
        if ct is not None:
            tc2 = _status_from_temp(ct)
            d.text((x+17, py+26), f"{ct:.1f}", font=Fo(38), fill=tc2)
            d.text((x+17, py+66), "°C  CPU", font=Fr(22), fill=T_TRT)
            _hbar(d, x+17, py+88, w-fan_sz*2-28, 8, min(ct, 100), tc2)
        else:
            d.text((x+17, py+28), "sin sensor", font=Fm(16), fill=T_TRT)
    return py + 102

def _draw_sys_section(d, x, w, py):
    _section(d, x+8, py+_SECT_TOP, py, S_GOOD, "SISTEMA")
    la  = os.getloadavg()
    nc  = psutil.cpu_count() or 4
    lc  = S_GOOD if la[0] < nc*0.7 else S_WARN if la[0] < nc else S_CRIT
    d.text((x+17,      py+28), f"{la[0]:.2f}", font=Fo(28), fill=lc)
    d.text((x+17+68,   py+32), f"{la[1]:.2f}", font=Fd(18), fill=T_SEC)
    d.text((x+17+118,  py+32), f"{la[2]:.2f}", font=Fd(18), fill=T_TRT)
    d.text((x+17,      py+52), "1m",  font=Fm(14), fill=lc)
    d.text((x+17+68,   py+52), "5m",  font=Fm(14), fill=T_TRT)
    d.text((x+17+118,  py+52), "15m", font=Fm(14), fill=T_TRT)
    return py + 78

# ── Fan icon ─────────────────────────────────────────────────────────────────
def _fan_icon(d, cx, cy, r, angle, col, n_blades=4):
    for i in range(n_blades):
        a0 = angle + i * (2*math.pi/n_blades)
        pts = []
        for t in [0, 0.25, 0.55, 0.85, 1.0]:
            da  = t * (math.pi/n_blades) * 1.6
            dr  = r * (0.18 + 0.82*t)
            pts.append((cx + dr*math.cos(a0+da), cy + dr*math.sin(a0+da)))
        for t in [0.9, 0.6, 0.3, 0.05]:
            da  = t * (math.pi/n_blades) * 1.6 - 0.35
            dr  = r * (0.18 + 0.45*t)
            pts.append((cx + dr*math.cos(a0+da), cy + dr*math.sin(a0+da)))
        glow = tuple(min(255, c//3) for c in col)
        d.polygon(pts, fill=glow)
        d.polygon(pts, fill=col)
    d.ellipse([cx-r*0.16,cy-r*0.16,cx+r*0.16,cy+r*0.16], fill=(38, 33, 75))
    d.ellipse([cx-r*0.07,cy-r*0.07,cx+r*0.07,cy+r*0.07], fill=A_CPU)

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    if frame % 2 == 0:
        _update_net()
        _update_disk_io()

    img = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(img)

    for y in range(H):
        t = y / H
        r = int(S_BG_TOP[0] + (S_BG_BOT[0]-S_BG_TOP[0]) * t)
        g = int(S_BG_TOP[1] + (S_BG_BOT[1]-S_BG_TOP[1]) * t)
        b = int(S_BG_TOP[2] + (S_BG_BOT[2]-S_BG_TOP[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    for x in range(24, W, 32):
        for y in range(24, H, 32):
            d.point((x, y), fill=(48, 44, 88) if (x+y) % 64 == 0 else (42, 38, 78))

    _light_leak(d, frame)
    _light_leak_horizontal(d, frame)

    for tx, ty, tlen, horiz, phase in _TRACES:
        t_phase = (frame + phase) % 40
        if t_phase < 20:
            alpha = int(t_phase * 2)
        else:
            alpha = int((40 - t_phase) * 2)
        alpha = min(alpha, 25)
        if alpha < 3: continue
        col = (alpha, alpha, alpha + 15)
        if horiz:
            d.line([(tx, ty), (tx + tlen, ty)], fill=col, width=1)
        else:
            d.line([(tx, ty), (tx, ty + tlen)], fill=col, width=1)

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

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    TB = 60
    _glass_panel(d, 0, 0, W, TB, r=0)
    d.rectangle([0, TB-2, W, TB], fill=(A_CPU[0]//3, A_CPU[1]//3, A_CPU[2]//3))
    d.rectangle([0, TB-1, W, TB], fill=A_CPU)

    blink = A_CPU if (frame % 14) < 9 else (0, 50, 80)
    d.ellipse([12, 10, 28, 26], fill=blink, outline=(0, 130, 200, 80), width=1)
    d.text((36, 7),  _HOSTNAME[:18].upper(), font=Fr(24), fill=T_PRI)
    d.text((36, 32), cpu_nm,                  font=Fr(20), fill=T_SEC)

    if _LOGO_DISTRO:
        ly = (TB - _LOGO_DISTRO.height) // 2
        lx = W//2 - _LOGO_DISTRO.width - 100
        img.paste(_LOGO_DISTRO, (lx, ly), _LOGO_DISTRO)
    if _LOGO_CPU:
        ly = (TB - _LOGO_CPU.height) // 2
        img.paste(_LOGO_CPU, (W//2 + 100, ly), _LOGO_CPU)

    ts = now.strftime("%H:%M:%S")
    _ctr(d, W//2, 14, ts, Fo(28), A_CPU)
    _ctr(d, W//2, 42, now.strftime("%a %d/%m/%Y"), Fr(16), T_TRT)

    upd_count = _get_updates()
    if upd_count is None and _upd['checking']:
        d.text((W-130, 10), "checking",   font=Fm(13), fill=T_TRT)
        d.text((W-130, 28), "updates...", font=Fm(13), fill=T_TRT)
    elif upd_count and upd_count > 0:
        alert_col = S_WARN if upd_count < 20 else S_CRIT
        glow_c = tuple(min(255, c//3) for c in alert_col)
        if (frame % 16) < 12:
            d.rectangle([W-157, 2, W-5, TB-2], fill=glow_c)
        d.rectangle([W-154, 4, W-8, TB-4], fill=(14, 12, 40))
        d.rectangle([W-154, 4, W-8, TB-4], outline=alert_col, width=2)
        _ctr(d, W-81, 8,  str(upd_count), Fo(26), alert_col)
        _ctr(d, W-81, 38, "UPDATES",       Fr(14), alert_col)
    elif upd_count == 0:
        _badge(d, W-90, 16, "OK", S_GOOD)
    else:
        d.text((W-100, 22), "updates N/A", font=Fm(12), fill=T_TRT)

    # ── LAYOUT ───────────────────────────────────────────────────────────────
    UY = TB + 5
    LX, LW = 10, 200
    RX, RW = W-10-200, 200
    MX  = LX+LW+6
    MW  = RX-MX-6
    GCX = MX + MW//2
    GCY = UY + 190
    GR  = 162

    _gauge(d, GCX, GCY, GR, cpu, ct)

    ga_l = GCX - GR - 6
    ga_r = GCX + GR + 6
    d.line([(MX+4, GCY), (ga_l, GCY)], fill=(38, 36, 75), width=1)
    d.line([(ga_r, GCY), (MX+MW-4, GCY)], fill=(38, 36, 75), width=1)
    d.ellipse([ga_l-3, GCY-3, ga_l+3, GCY+3], fill=T_TRT)
    d.ellipse([ga_r-3, GCY-3, ga_r+3, GCY+3], fill=T_TRT)

    CLK_Y = GCY + GR + 10
    _ctr(d, GCX, CLK_Y+4, now.strftime("%A  %d / %m / %Y"), Fr(17), T_TRT)

    # ── PANEL IZQUIERDO ───────────────────────────────────────────────────────
    PH = H - UY - 4
    py = UY
    _glass_panel(d, LX, py, LW, PH, r=10)
    _glass_highlight(img, d, LX, py, LW, PH, r=10)

    if volt is not None:
        d.text((LX+LW-48, py+4), f"{volt:.3f}V", font=Fm(12), fill=T_TRT)

    py = _draw_cpu_section(d, LX, LW, py, cpu, freq, ct)
    _divider(d, LX+8, py, LW-16)
    py += _SECT_GAP

    py = _draw_mem_section(d, LX, LW, py, mem)
    _divider(d, LX+8, py, LW-16)
    py += _SECT_GAP

    py = _draw_disk_section(d, LX, LW, py, disk, disk_mount)
    _divider(d, LX+8, py, LW-16)
    py += _SECT_GAP

    py = _draw_net_section(d, LX, LW, py)

    # ── PANEL DERECHO ─────────────────────────────────────────────────────────
    py = UY
    _glass_panel(d, RX, py, RW, PH, r=10)
    _glass_highlight(img, d, RX, py, RW, PH, r=10)

    py = _draw_gpu_section(d, RX, RW, py, gpu, gpu_nm, gt)
    _divider(d, RX+8, py, RW-16)
    py += _SECT_GAP

    py = _draw_io_section(d, RX, RW, py, frame)
    _divider(d, RX+8, py, RW-16)
    py += _SECT_GAP

    py = _draw_fan_section(d, RX, RW, py, fan, ct, frame)
    _divider(d, RX+8, py, RW-16)
    py += _SECT_GAP

    py = _draw_sys_section(d, RX, RW, py)

    return img
