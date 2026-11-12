"""
Tema: HUD — Blue tactical display
Display landscape 960×480 · fuentes grandes para pantalla 5.5"
"""
import math, datetime, time as _time, os
import psutil, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 960, 480
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Fondo HUD (cacheado) ───────────────────────────────────────────────────────
_BG_CACHE = None
def _load_bg():
    global _BG_CACHE
    if _BG_CACHE is None:
        try:
            raw = Image.open(os.path.join(_BASE, 'assets', 'hud_bg2.png')).convert('RGB')
            iw, ih = raw.size
            scale  = W / iw
            nh     = int(ih * scale)
            raw    = raw.resize((W, nh), Image.LANCZOS)
            top    = max(0, (nh - H) // 2)
            _BG_CACHE = raw.crop((0, top, W, top + H))
        except:
            _BG_CACHE = False
    return _BG_CACHE if _BG_CACHE else None

# ── Fuentes ────────────────────────────────────────────────────────────────────
_FD = os.path.join(_BASE, "fonts")
_F = {
    'num':   os.path.join(_FD, "Orbitron-Black.ttf"),    # números grandes
    'orb':   os.path.join(_FD, "Orbitron-Bold.ttf"),     # títulos / valores
    'raj':   os.path.join(_FD, "Rajdhani-SemiBold.ttf"), # labels
    'mono':  os.path.join(_FD, "ShareTechMono.ttf"),     # datos mono
    'teko':  os.path.join(_FD, "Teko-Medium.ttf"),       # fallback
}

_FCACHE: dict = {}
def F(sz, style='orb'):
    key = f"{style}_{sz}"
    if key in _FCACHE: return _FCACHE[key]
    for p in [_F.get(style, _F['teko']), _F['teko']]:
        try:
            f = ImageFont.truetype(p, sz)
            _FCACHE[key] = f
            return f
        except: continue
    return ImageFont.load_default()

# ── Paleta azul HUD ────────────────────────────────────────────────────────────
BG     = (2,   8,  16)
BG2    = (4,  12,  24)
BLUE   = (0, 170, 255)   # azul primario
BBLUE  = (0,  90, 160)   # azul medio
DBLUE  = (0,  42,  80)   # azul oscuro (barras bg)
VDBLUE = (0,  15,  37)   # azul muy oscuro
DIM    = (106,170, 200)   # texto dim #6aaac8
WHITE  = (255,255, 255)   # texto blanco
OR     = (255,140,   0)   # naranja — medio/warn
RE     = (255, 51,   0)   # rojo — crítico

# ── Métricas ───────────────────────────────────────────────────────────────────
_NET_ST = {'t':0.,'sent':0,'recv':0,'ul':0.,'dl':0.}

def _cpu():   return psutil.cpu_percent(interval=None)
def _cpus():  return psutil.cpu_percent(interval=None, percpu=True)
def _mem():   return psutil.virtual_memory()
def _freq():
    try: f = psutil.cpu_freq(); return f.current/1000 if f else None
    except: return None
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp','coretemp','cpu_thermal']:
            if k in t: return t[k][0].current
    except: return None
def _gpu():
    try:
        r = subprocess.run(['cat','/sys/class/drm/card1/device/gpu_busy_percent'],
                           capture_output=True, text=True, timeout=1)
        return int(r.stdout.strip()) if r.returncode==0 else None
    except: return None
def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu','nvidia','radeon']:
            if k in t: return t[k][0].current
    except: return None
def _vram():
    try:
        u = int(open('/sys/class/drm/card1/device/mem_info_vram_used').read())
        v = int(open('/sys/class/drm/card1/device/mem_info_vram_total').read())
        return u//(1024*1024), v//(1024*1024)
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
        _NET_ST.update({'t':now,'sent':c.bytes_sent,'recv':c.bytes_recv})
        return max(0.,_NET_ST['ul']), max(0.,_NET_ST['dl'])
    except: return 0., 0.
def _fmtnet(k):
    if k < 1:    return "0.0 KB/s"
    if k < 1024: return f"{k:.1f} KB/s"
    return f"{k/1024:.1f} MB/s"
def _uptime():
    s = int(_time.time() - psutil.boot_time())
    h,r = divmod(s,3600); m,sc = divmod(r,60)
    return f"{h:02d}:{m:02d}:{sc:02d}"
def _disks():
    seen,res = set(),[]
    for p in psutil.disk_partitions(all=False):
        if p.mountpoint in {'/','/home'} and p.mountpoint not in seen:
            seen.add(p.mountpoint)
            try:
                u = psutil.disk_usage(p.mountpoint)
                res.append((p.mountpoint, u.used, u.total, u.percent))
            except: pass
    return sorted(res)
def _cpuname():
    try:
        for line in open('/proc/cpuinfo'):
            if 'model name' in line:
                nm = line.split(':')[1].strip()
                for kw in ['Ryzen','Core','Threadripper','EPYC']:
                    if kw in nm:
                        p = nm.split(); i = p.index(kw)
                        return ' '.join(p[i:i+4])
                return nm[:28]
    except: pass
    return 'CPU'
def _vc(v):  return RE if v >= 90 else (OR if v >= 70 else BLUE)
def _tc(t):  return RE if t is None else (RE if t >= 85 else (OR if t >= 70 else BLUE))

# ── Helpers gráficos ───────────────────────────────────────────────────────────
def _glow_layer(size, draw_fn, radius=6):
    gl = Image.new('RGBA', size, (0,0,0,0))
    gd = ImageDraw.Draw(gl)
    draw_fn(gd)
    return gl.filter(ImageFilter.GaussianBlur(radius=radius))

def _alpha_paste(base, layer):
    b = base.convert('RGBA')
    b.alpha_composite(layer)
    return b.convert('RGB')

def _bar(d, x, y, w, h, pct, col, bg=DBLUE):
    d.rectangle([x,y,x+w,y+h], fill=bg, outline=VDBLUE)
    fw = int(w * min(pct,100)/100)
    if fw > 2:
        for xi in range(fw):
            t = xi/max(fw,1)
            c = tuple(int(VDBLUE[i] + (col[i]-VDBLUE[i])*t) for i in range(3))
            d.line([(x+xi,y+1),(x+xi,y+h-1)], fill=c)

def _text_c(d, cx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _text_r(d, rx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((rx-(bb[2]-bb[0]), y), txt, font=font, fill=col)

def _corners_hud(d, x, y, w, h, col, sz=22, inner=8, lw=2):
    """Doble bracket en cada esquina."""
    pts = [
        # TL
        [(x,y+sz),(x,y),(x+sz,y)],
        [(x,y+inner),(x,y),(x+inner,y)],
        # TR
        [(x+w-sz,y),(x+w,y),(x+w,y+sz)],
        [(x+w-inner,y),(x+w,y),(x+w,y+inner)],
        # BL
        [(x,y+h-sz),(x,y+h),(x+sz,y+h)],
        [(x,y+h-inner),(x,y+h),(x+inner,y+h)],
        # BR
        [(x+w-sz,y+h),(x+w,y+h),(x+w,y+h-sz)],
        [(x+w-inner,y+h),(x+w,y+h),(x+w-inner,y+h)],
    ]
    for i,pts3 in enumerate(pts):
        lwidth = lw if i%2==0 else 1
        alpha  = 255 if i%2==0 else 100
        c = tuple(list(col)+[alpha]) if len(col)==3 else col
        for j in range(len(pts3)-1):
            d.line([pts3[j], pts3[j+1]], fill=col, width=lwidth)

def _tick_marks(d, col):
    """Ticks laterales del frame."""
    ticks_l = [(158,10,False),(190,16,True),(222,8,False),(240,20,True),(258,8,False),(290,16,True),(322,10,False)]
    for y_,ln,maj in ticks_l:
        c = col if maj else tuple(int(v*.5) for v in col)
        lw = 2 if maj else 1
        d.line([(0,y_),(ln,y_)], fill=c, width=lw)
        d.line([(W,y_),(W-ln,y_)], fill=c, width=lw)

def _side_notch(d, col):
    """Diamond pip en centro del lado."""
    cx,cy = 0,240
    d.polygon([(cx,cy-5),(cx+5,cy),(cx,cy+5),(cx-5,cy)], fill=col)
    cx2 = W
    d.polygon([(cx2,cy-5),(cx2-5,cy),(cx2,cy+5),(cx2+5,cy)], fill=col)

def _top_notch(d, col):
    """Centro del borde superior e inferior — diamond + líneas con gap."""
    # top
    xl,xr,yp = 366,594,0
    d.line([(72,0),(xl,0)], fill=col, width=2)
    d.line([(xr,0),(888,0)], fill=col, width=2)
    # notch lines
    pts_t = [(xl,0),(xl+32,0),(xl+50,18),(xr-50,18),(xr-32,0),(xr,0)]
    for i in range(len(pts_t)-1):
        d.line([pts_t[i],pts_t[i+1]], fill=col, width=2)
    # diamond
    d.polygon([(480,2),(485,8),(480,14),(475,8)], fill=col)
    # bottom
    d.line([(72,H),(xl,H)], fill=col, width=2)
    d.line([(xr,H),(888,H)], fill=col, width=2)
    pts_b = [(xl,H),(xl+32,H),(xl+50,H-18),(xr-50,H-18),(xr-32,H),(xr,H)]
    for i in range(len(pts_b)-1):
        d.line([pts_b[i],pts_b[i+1]], fill=col, width=2)
    d.polygon([(480,H-2),(485,H-8),(480,H-14),(475,H-8)], fill=col)

def _side_panels(d, col):
    """Pequeños rectángulos decorativos en los bordes."""
    boxes_l = [(2,78,54,18),(2,100,54,8),(2,112,54,8),(2,310,54,18),(2,332,54,8)]
    boxes_r = [(W-56,78,54,18),(W-56,100,54,8),(W-56,112,54,8),(W-56,310,54,18),(W-56,332,54,8)]
    alpha = tuple(int(v*.35) for v in col)
    fill  = tuple(int(v*.06) for v in col)
    for bx,by,bw,bh in boxes_l+boxes_r:
        d.rectangle([bx,by,bx+bw,by+bh], fill=fill, outline=alpha)

def _side_segments(d, col):
    """Segmentos laterales con gap central."""
    dim = tuple(int(v*.55) for v in col)
    d.line([(0,72),(0,190)], fill=col, width=2)
    d.line([(0,190),(0,290)], fill=dim, width=1)
    d.line([(0,290),(0,408)], fill=col, width=2)
    d.line([(W,72),(W,190)], fill=col, width=2)
    d.line([(W,190),(W,290)], fill=dim, width=1)
    d.line([(W,290),(W,408)], fill=col, width=2)

def _sub_lines(d, col):
    dim = tuple(int(v*.25) for v in col)
    d.line([(72,42),(366,42)], fill=dim, width=1)
    d.line([(594,42),(888,42)], fill=dim, width=1)
    d.line([(72,332),(888,332)], fill=tuple(int(v*.15) for v in col), width=1)
    d.line([(72,462),(888,462)], fill=dim, width=1)

# ── Gauge circular azul ────────────────────────────────────────────────────────
_GS = 150   # inicio 150°, barrido 240°

def _gauge(img, cx, cy, r, pct, frame, col=BLUE, thick=14):
    deg = 240 * min(pct,100) / 100
    end = (_GS + deg) % 360

    # capa glow
    def _draw_glow(gd):
        if pct > 1:
            for rr,al in [(r+12,10),(r+7,28),(r+2,50)]:
                bb = [cx-rr,cy-rr,cx+rr,cy+rr]
                gd.arc(bb, _GS, end, fill=(*col,al), width=thick+4)
    gl = _glow_layer((W,H), _draw_glow, radius=8)
    img = _alpha_paste(img, gl)
    d = ImageDraw.Draw(img)

    # track dim
    bb = [cx-r,cy-r,cx+r,cy+r]
    d.arc(bb, _GS, (_GS+240)%360, fill=DBLUE, width=thick)

    # rotating dashed ring (externo)
    ang_step = 360/48
    r_ring = r + 8
    for i in range(48):
        if i % 3 == 0: continue
        a1 = math.radians(frame*2 + i*ang_step)
        a2 = math.radians(frame*2 + (i+.7)*ang_step)
        x1 = cx + r_ring*math.cos(a1); y1 = cy + r_ring*math.sin(a1)
        x2 = cx + r_ring*math.cos(a2); y2 = cy + r_ring*math.sin(a2)
        d.line([(x1,y1),(x2,y2)], fill=tuple(int(v*.25) for v in col), width=1)

    # rotating dashed ring (interno)
    r_ring2 = r - thick - 6
    for i in range(32):
        if i % 4 == 0: continue
        a1 = math.radians(-frame*1.5 + i*360/32)
        a2 = math.radians(-frame*1.5 + (i+.6)*360/32)
        x1 = cx + r_ring2*math.cos(a1); y1 = cy + r_ring2*math.sin(a1)
        x2 = cx + r_ring2*math.cos(a2); y2 = cy + r_ring2*math.sin(a2)
        d.line([(x1,y1),(x2,y2)], fill=tuple(int(v*.2) for v in col), width=1)

    # arc valor — gradiente blanco→azul→naranja según pct
    if pct > 0.5:
        seg = 20; gap = 2; s = _GS; rem = deg
        while rem > 0:
            sw = min(seg, rem)
            e  = (s + sw) % 360
            t  = 1 - rem/deg
            if pct < 70:
                r_ = int(200 + (col[0]-200)*t)
                g_ = int(200 + (col[1]-200)*t)
                b_ = int(255 + (col[2]-255)*t)
            elif pct < 90:
                r_ = int(col[0] + (OR[0]-col[0])*((pct-70)/20))
                g_ = int(col[1] + (OR[1]-col[1])*((pct-70)/20))
                b_ = int(col[2] + (OR[2]-col[2])*((pct-70)/20))
            else:
                r_ = RE[0]; g_ = RE[1]; b_ = RE[2]
            d.arc(bb, s, e, fill=(r_,g_,b_), width=thick)
            s = (s+sw+gap)%360; rem -= sw+gap

    # ticks
    for ti in range(0,241,30):
        ang = math.radians(_GS+ti); maj = ti%60==0
        r1,r2 = r+2, r+(12 if maj else 7)
        c_ = col if ti<=deg else tuple(int(v*.25) for v in col)
        d.line([(cx+r1*math.cos(ang),cy+r1*math.sin(ang)),
                (cx+r2*math.cos(ang),cy+r2*math.sin(ang))],
               fill=c_, width=(2 if maj else 1))

    # sweep line
    sw_ang = math.radians(frame * 3)
    d.line([(cx, cy),
            (cx + (r-thick-2)*math.cos(sw_ang),
             cy + (r-thick-2)*math.sin(sw_ang))],
           fill=(*col, 120), width=1)

    # inner circle
    ri = r - thick - 4
    d.ellipse([cx-ri,cy-ri,cx+ri,cy+ri], fill=BG2, outline=tuple(int(v*.2) for v in col))

    # crosshair
    d.line([(cx-20,cy),(cx+20,cy)], fill=(*col,60), width=1)
    d.line([(cx,cy-20),(cx,cy+20)], fill=(*col,60), width=1)
    d.ellipse([cx-4,cy-4,cx+4,cy+4], outline=(*col,80), width=1)

    return img

# ── Render ─────────────────────────────────────────────────────────────────────
def render(frame):
    # ── Fondo ────────────────────────────────────────────────────────────────────
    wp = _load_bg()
    if wp:
        img = wp.copy()
        # overlay azul semitransparente — deja el fondo visible
        ov = Image.new('RGBA', (W, H), (2, 8, 28, 140))
        base = img.convert('RGBA'); base.alpha_composite(ov)
        img  = base.convert('RGB')
    else:
        img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    # grid sobre el fondo
    for x in range(0, W, 40):
        d.line([(x,0),(x,H)], fill=(0,40,80), width=1)
    for y in range(0, H, 40):
        d.line([(0,y),(W,y)], fill=(0,40,80), width=1)

    # scanline animada
    sy = (frame * 5) % (H+20) - 10
    for dy,al in [(0,35),(1,18),(-1,18),(2,7),(-2,7)]:
        fy = sy+dy
        if 0 <= fy < H:
            d.line([(0,fy),(W,fy)], fill=(0, al*3, al*5), width=1)

    # ── datos ─────────────────────────────────────────────
    cpu_all= _cpus()
    cpu_v  = sum(cpu_all)/len(cpu_all) if cpu_all else 0
    mem    = _mem()
    ct     = _temp()
    freq   = _freq()
    gpu_v  = _gpu() or 0
    gt     = _gtemp()
    ul,dl  = _net()
    vru,vrt= _vram()
    gsclk  = _gsclk()
    disks  = _disks()
    now    = datetime.datetime.now()
    cpu_nm = _cpuname()
    uptime = _uptime()
    ram_gb = (mem.total-mem.available)/1024**3
    tot_gb = mem.total/1024**3
    procs  = len(psutil.pids())

    # layout constants
    TOP = 42
    BOT_Y = 332
    BOT_H = 148
    LW = 210   # left col width
    RX = W-210 # right col x

    # ══════════════════════════════════════════════════════
    # GAUGE CENTRAL — cx=480, cy=210, r=125
    # ══════════════════════════════════════════════════════
    img = _gauge(img, 480, (TOP+BOT_Y)//2, 120, cpu_v, frame, col=_vc(cpu_v))
    d   = ImageDraw.Draw(img)

    # texto del gauge
    cx_g = 480
    cy_g = (TOP+BOT_Y)//2
    r_g  = 120

    _text_c(d, cx_g, cy_g-78, "SYSTEM LOAD", F(16,'raj'), DIM)
    big_col = _vc(cpu_v)
    _text_c(d, cx_g, cy_g-40, f"{cpu_v:.0f}", F(90,'num'), big_col)
    _text_c(d, cx_g, cy_g+36, "%", F(18,'orb'), DIM)

    # sub stats bajo el gauge
    _text_c(d, cx_g-80, cy_g+56, "FREQ",    F(18,'raj'), DIM)
    _text_c(d, cx_g-80, cy_g+72, f"{freq:.1f}G" if freq else "--", F(18,'orb'), WHITE)
    _text_c(d, cx_g,    cy_g+56, "TEMP",    F(18,'raj'), DIM)
    _text_c(d, cx_g,    cy_g+72, f"{ct:.0f}°C" if ct else "--", F(18,'orb'), _tc(ct))
    _text_c(d, cx_g+80, cy_g+56, "CORES",   F(18,'raj'), DIM)
    _text_c(d, cx_g+80, cy_g+72, str(len(cpu_all)), F(18,'orb'), WHITE)

    # ══════════════════════════════════════════════════════
    # COLUMNA IZQUIERDA
    # ══════════════════════════════════════════════════════
    x0,y0 = 14, TOP+8

    # CPU LOAD
    d.text((x0, y0), "CPU LOAD", font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    y0 += 16
    d.line([(x0,y0),(LW-10,y0)], fill=DBLUE, width=1)
    y0 += 4

    cc = _vc(cpu_v)
    _text_c(d, LW//2, y0, f"{cpu_v:.0f}%", F(72,'num'), cc)
    y0 += 76
    _bar(d, x0, y0, LW-24, 6, cpu_v, cc)
    y0 += 10
    d.text((x0, y0), f"{freq:.2f} GHz" if freq else "--", font=F(17,'raj'), fill=DIM)
    _text_r(d, LW-14, y0, f"{ct:.0f}°C" if ct else "--", F(20,'orb'), _tc(ct))
    y0 += 22

    # CORES
    d.text((x0, y0), "CORES", font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    y0 += 16
    d.line([(x0,y0),(LW-10,y0)], fill=DBLUE, width=1)
    y0 += 4

    cores = (cpu_all or [])[:16]
    if cores:
        bw = (LW-24-2*(len(cores)-1))//len(cores)
        bh = 38
        for i,p in enumerate(cores):
            bx_ = x0 + i*(bw+2)
            bc  = _vc(p)
            filled = int(bh*p/100)
            d.rectangle([bx_,y0,bx_+bw,y0+bh], fill=VDBLUE, outline=DBLUE)
            if filled>0:
                d.rectangle([bx_,y0+bh-filled,bx_+bw,y0+bh], fill=bc)
    y0 += 44

    # MEMORY
    d.text((x0,y0), "MEMORY", font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    y0 += 16
    d.line([(x0,y0),(LW-10,y0)], fill=DBLUE, width=1)
    y0 += 4

    mc = _vc(mem.percent)
    d.text((x0,y0), f"{ram_gb:.1f}", font=F(48,'num'), fill=WHITE)
    _text_r(d, LW-14, y0+14, f"/ {tot_gb:.0f} GB", F(17,'mono'), DIM)
    y0 += 52
    _bar(d, x0, y0, LW-24, 5, mem.percent, mc)
    y0 += 8
    d.text((x0,y0), f"{mem.percent:.0f}%  SWAP {mem.total//1024**3 - mem.available//1024**3:.0f}G", font=F(15,'raj'), fill=DIM)

    # ══════════════════════════════════════════════════════
    # COLUMNA DERECHA
    # ══════════════════════════════════════════════════════
    rx0,ry0 = RX+14, TOP+8

    # GPU LOAD
    d.text((rx0,ry0), "GPU LOAD", font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    ry0 += 16
    d.line([(rx0,ry0),(W-14,ry0)], fill=DBLUE, width=1)
    ry0 += 4

    gc_ = _vc(gpu_v)
    _text_c(d, RX + (W-RX)//2, ry0, f"{gpu_v:.0f}%", F(72,'num'), gc_)
    ry0 += 76
    _bar(d, rx0, ry0, W-RX-28, 6, gpu_v, gc_)
    ry0 += 10
    d.text((rx0,ry0), f"{gsclk} MHz" if gsclk else "--", font=F(17,'raj'), fill=DIM)
    _text_r(d, W-14, ry0, f"{gt:.0f}°C" if gt else "--", F(20,'orb'), _tc(gt))
    ry0 += 22

    # VRAM
    d.text((rx0,ry0), "VRAM", font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    ry0 += 16
    d.line([(rx0,ry0),(W-14,ry0)], fill=DBLUE, width=1)
    ry0 += 4

    if vru is not None:
        d.text((rx0,ry0), f"{vru}", font=F(36,'num'), fill=WHITE)
        _text_r(d, W-14, ry0+8, f"/ {vrt} MB", F(17,'raj'), DIM)
        ry0 += 40
        _bar(d, rx0, ry0, W-RX-28, 5, vru/vrt*100 if vrt else 0, BLUE)
        ry0 += 8
        d.text((rx0,ry0), f"{vru*100//vrt if vrt else 0}%  ·  CLK {gsclk} MHz" if gsclk else f"{vru*100//vrt if vrt else 0}%", font=F(15,'raj'), fill=DIM)
        ry0 += 18
    else:
        d.text((rx0,ry0), "N/A", font=F(22,'orb'), fill=DIM)
        ry0 += 28

    # STORAGE
    d.text((rx0,ry0), "STORAGE", font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    ry0 += 16
    d.line([(rx0,ry0),(W-14,ry0)], fill=DBLUE, width=1)
    ry0 += 4

    for mnt,used,total,pct in disks[:2]:
        dc_ = _vc(pct)
        lbl = "/" if mnt=="/" else "/home"
        d.text((rx0,ry0), lbl, font=F(17,'raj'), fill=DIM)
        _text_r(d, W-14,ry0, f"{pct:.0f}%", F(15,'orb'), dc_)
        ry0 += 16
        _bar(d, rx0,ry0, W-RX-28, 4, pct, dc_)
        ry0 += 8

    # ══════════════════════════════════════════════════════
    # FRANJA INFERIOR
    # ══════════════════════════════════════════════════════
    by = BOT_Y + 9
    bw4 = (W-4)//4

    # NETWORK
    bx = 14
    d.text((bx,by), "NETWORK", font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    by += 16
    d.line([(bx,by),(bw4-10,by)], fill=DBLUE, width=1); by += 4
    d.text((bx,by), "UP", font=F(18,'raj'), fill=DIM)
    _text_r(d, bw4-10,by, _fmtnet(ul), F(22,'orb'), WHITE); by += 20
    _bar(d, bx,by,bw4-24,5, min(ul/500*100,100), BLUE); by += 9
    d.text((bx,by), "DL", font=F(18,'raj'), fill=DIM)
    _text_r(d, bw4-10,by, _fmtnet(dl), F(22,'orb'), WHITE); by += 20
    _bar(d, bx,by,bw4-24,5, min(dl/500*100,100), BLUE); by += 9
    d.text((bx,by+2), "LAT", font=F(18,'raj'), fill=DIM)
    _text_r(d, bw4-10,by+2, "12 ms", F(22,'orb'), BLUE)

    # UPTIME
    ux = bw4+10
    _text_c(d, ux+85, BOT_Y+12, "UPTIME", F(19,'raj'), tuple(int(v*.65) for v in BLUE))
    _text_c(d, ux+85, BOT_Y+30, uptime, F(36,'num'), WHITE)
    _text_c(d, ux+85, BOT_Y+68, "HH:MM:SS", F(17,'raj'), DIM)

    # PROCESSES
    px = bw4*2+10
    _text_c(d, px+80, BOT_Y+12, "PROCESSES", F(19,'raj'), tuple(int(v*.65) for v in BLUE))
    _text_c(d, px+80, BOT_Y+28, str(procs), F(48,'num'), WHITE)
    _text_c(d, px+80, BOT_Y+78, "RUNNING", F(18,'raj'), DIM)

    # SYSTEM
    sx = bw4*3+14
    d.text((sx, BOT_Y+9),  "SYSTEM",     font=F(18,'raj'), fill=tuple(int(v*.65) for v in BLUE))
    d.line([(sx,BOT_Y+25),(W-14,BOT_Y+25)], fill=DBLUE, width=1)
    d.text((sx, BOT_Y+28), "OS",         font=F(18,'raj'), fill=DIM)
    d.text((sx+40,BOT_Y+28), cpu_nm[:16], font=F(16,'raj'), fill=WHITE)
    d.text((sx, BOT_Y+46), "KERNEL",     font=F(18,'raj'), fill=DIM)
    try:
        import platform
        kv = platform.release()[:12]
    except: kv = "---"
    d.text((sx+60,BOT_Y+46), kv,          font=F(16,'mono'), fill=WHITE)
    d.text((sx, BOT_Y+64), "SWAP",       font=F(18,'raj'), fill=DIM)
    d.text((sx+48,BOT_Y+64), f"{mem.total/1024**3-mem.available/1024**3:.1f} GB", font=F(22,'orb'), fill=BLUE)
    # status dot
    blink_on = (frame // 15) % 2 == 0
    dot_col = (0,220,80) if blink_on else (0,80,30)
    d.ellipse([sx,BOT_Y+84,sx+8,BOT_Y+92], fill=dot_col)
    d.text((sx+12,BOT_Y+83), "NOMINAL", font=F(18,'raj'), fill=DIM)

    # ══════════════════════════════════════════════════════
    # STATUS BAR (muy abajo)
    # ══════════════════════════════════════════════════════
    sb = H-18
    d.line([(0,sb),(W,sb)], fill=DBLUE, width=1)
    d.text((14,sb+2), f"CPU {cpu_v:.0f}% {ct:.0f}C  RAM {mem.percent:.0f}% {ram_gb:.1f}G  GPU {gpu_v:.0f}% {(gt or 0):.0f}C", font=F(18,'raj'), fill=DIM)
    center_txt = "SYS MONITOR  FEDORA 44"
    _text_c(d, W//2, sb+2, center_txt, F(17,'mono'), tuple(int(v*.3) for v in BLUE))
    net_txt = f"/ {disks[0][3]:.0f}%  /home {disks[1][3]:.0f}%  NET U:{_fmtnet(ul)} D:{_fmtnet(dl)}" if len(disks)>=2 else ""
    _text_r(d, W-14, sb+2, net_txt, F(18,'raj'), DIM)

    # ══════════════════════════════════════════════════════
    # HUD FRAME OVERLAY (glow layer)
    # ══════════════════════════════════════════════════════
    pulse_col = tuple(int(BLUE[i] * (.7 + .3*math.sin(frame*0.08))) for i in range(3))

    def _draw_frame(fd):
        _corners_hud(fd, 0, 0, W-1, H-1, pulse_col, sz=22, inner=8, lw=2)
        _side_segments(fd, pulse_col)
        _top_notch(fd, pulse_col)
        _tick_marks(fd, pulse_col)
        _side_panels(fd, BLUE)
        _sub_lines(fd, BLUE)
        _side_notch(fd, pulse_col)

    frame_gl = _glow_layer((W,H), _draw_frame, radius=4)
    img = _alpha_paste(img, frame_gl)
    d   = ImageDraw.Draw(img)
    _draw_frame(d)   # draw sharp on top

    # divisores de columnas
    dim_blue = tuple(int(v*.2) for v in BLUE)
    d.line([(LW,TOP),(LW,BOT_Y)], fill=dim_blue, width=1)
    d.line([(RX,TOP),(RX,BOT_Y)], fill=dim_blue, width=1)
    d.line([(bw4,BOT_Y),(bw4,H)], fill=dim_blue, width=1)
    d.line([(bw4*2,BOT_Y),(bw4*2,H)], fill=dim_blue, width=1)
    d.line([(bw4*3,BOT_Y),(bw4*3,H)], fill=dim_blue, width=1)

    return img
