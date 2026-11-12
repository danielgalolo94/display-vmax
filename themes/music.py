"""
Tema: MUSIC VISUALIZER — 8 bandas retro 80s + panel datos PC
EQ izquierda (8 barras anchas), stats de PC a la derecha.
Display landscape 960x480
"""
import subprocess, threading, math, datetime, shutil, time
import numpy as np
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
import os
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

# fuentes: Orbitron Black (barras/nums) + Teko (labels EQ) + Rajdhani (stats PC)
_F_BIG  = os.path.join(_FD, "Orbitron-Black.ttf")
_F_TEKO = os.path.join(_FD, "Teko-Medium.ttf")
_F_RAJ  = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_MONO = os.path.join(_FD, "ShareTechMono.ttf")

def fnt(size):       # EQ labels + títulos
    try:    return ImageFont.truetype(_F_TEKO, size)
    except: return ImageFont.load_default()

def fnt_big(size):   # números grandes VU/barras
    try:    return ImageFont.truetype(_F_BIG, size)
    except: return fnt(size)

def fnt_raj(size):   # stats panel PC
    try:    return ImageFont.truetype(_F_RAJ, size)
    except: return fnt(size)

def fnt_mono(size):  # datos mono
    try:    return ImageFont.truetype(_F_MONO, size)
    except: return fnt(size)

# ── Layout EQ (izquierda) ────────────────────────────────────────────────────
EQ_W     = 560   # ancho del área EQ
EQ_TOP   = 32    # y inicio de barras
EQ_BOT   = 446   # y baseline de barras
MAX_BAR  = EQ_BOT - EQ_TOP   # ~414px

# ── Segmentos LED ─────────────────────────────────────────────────────────────
SEG_H   = 8
SEG_GAP = 2
STEP    = SEG_H + SEG_GAP   # 10px por LED
N_SEGS  = MAX_BAR // STEP   # ~41 LEDs

# ── Layout PC (derecha) ───────────────────────────────────────────────────────
PC_X  = 568   # inicio panel PC
PC_W  = W - PC_X   # 392px

# ── Etiquetas de bandas (ISO octave) ─────────────────────────────────────────
BAND_LABELS = ["SUB", "BASS", "L-MID", "MID", "U-MID", "PRES", "HIGH", "AIR"]

# ── Config audio ──────────────────────────────────────────────────────────────
N_BARS      = 8
SAMPLE_RATE = 48000
FFT_SIZE    = 4096
CHANNELS    = 2
BYTES_FRAME = 2 * CHANNELS

# ── Estado compartido ─────────────────────────────────────────────────────────
_lock     = threading.Lock()
_bars     = np.zeros(N_BARS)
_vu_l     = 0.0
_vu_r     = 0.0
_pk_l     = 0.0
_pk_r     = 0.0
_ok       = False
_src      = ""
_peaks    = np.zeros(N_BARS)   # peak hold (solo render)
_band_max = np.full(N_BARS, 0.04)  # máximo histórico por banda (AGC)

# ── Detectar monitor del sink activo ─────────────────────────────────────────
def _find_active_monitor():
    try:
        si = subprocess.run(['pactl','list','sink-inputs','short'],
                            capture_output=True, text=True, timeout=2).stdout
        active_sink_ids = set()
        for line in si.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                active_sink_ids.add(parts[1])
        if active_sink_ids:
            sinks = subprocess.run(['pactl','list','sinks','short'],
                                   capture_output=True, text=True, timeout=2).stdout
            for line in sinks.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0] in active_sink_ids:
                    return parts[1] + '.monitor'
        sources = subprocess.run(['pactl','list','sources','short'],
                                 capture_output=True, text=True, timeout=2).stdout
        for line in sources.splitlines():
            if 'monitor' in line and 'RUNNING' in line:
                return line.split()[1]
        for line in sources.splitlines():
            if 'monitor' in line:
                return line.split()[1]
    except Exception as e:
        print(f"[music] pactl: {e}")
    return None

# ── Hilo de captura ───────────────────────────────────────────────────────────
def _audio_thread():
    global _bars, _vu_l, _vu_r, _pk_l, _pk_r, _ok, _src

    smooth  = np.zeros(N_BARS)
    proc    = None
    cur_mon = None

    while True:
        mon = _find_active_monitor()
        if mon != cur_mon:
            if proc:
                try: proc.terminate()
                except: pass
                proc = None
            cur_mon = mon
            _src = mon or ""
            print(f"[music] monitor: {mon}")

        if not mon:
            _ok = False
            time.sleep(3)
            continue

        if proc is None or proc.poll() is not None:
            try:
                proc = subprocess.Popen(
                    ['parec',
                     f'--device={mon}',
                     '--format=s16le',
                     f'--rate={SAMPLE_RATE}',
                     '--channels=2',
                     '--latency-msec=40'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
                _ok = True
                smooth[:] = 0
                print(f"[music] parec arrancado en {mon}")
            except Exception as e:
                print(f"[music] no se pudo iniciar parec: {e}")
                _ok = False
                time.sleep(3)
                continue

        needed = FFT_SIZE * BYTES_FRAME
        try:
            raw = proc.stdout.read(needed)
        except Exception:
            raw = b''

        if len(raw) < needed:
            proc = None
            time.sleep(0.1)
            continue

        data   = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        stereo = data.reshape(-1, 2)
        L      = stereo[:, 0]
        R      = stereo[:, 1]

        rl = float(np.sqrt(np.mean(L**2)))
        rr = float(np.sqrt(np.mean(R**2)))

        mono = (L + R) * 0.5
        win  = mono * np.hanning(len(mono))
        fft  = np.abs(np.fft.rfft(win, n=FFT_SIZE))
        fft  = 20 * np.log10(np.maximum(fft, 1e-9))
        fft  = np.clip((fft + 90) / 90, 0, 1)
        fft  = fft ** 6.0   # curva extrema: máximo contraste entre bandas

        freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)
        bins  = np.logspace(np.log10(20), np.log10(20000), N_BARS + 1)
        b     = np.zeros(N_BARS)
        for i in range(N_BARS):
            mask = (freqs >= bins[i]) & (freqs < bins[i+1])
            if mask.any():
                b[i] = np.mean(fft[mask])

        # AGC por banda: normalizar cada frecuencia contra su propio máximo histórico
        # Así el bajo, los medios y los agudos tienen la misma escala relativa
        _band_max[:] = np.maximum(_band_max * 0.9996, b)  # max decae muy lento
        _band_max[:] = np.maximum(_band_max, 0.002)
        b_norm = b / _band_max   # 0..1 relativo a su propio historial

        smooth = np.where(b_norm > smooth,
                          b_norm * 0.85 + smooth * 0.15,   # ataque rápido
                          smooth * 0.50)                    # caída rápida y uniforme

        with _lock:
            _bars  = smooth.copy()
            _vu_l  = rl
            _vu_r  = rr
            _pk_l  = max(_pk_l * 0.88, rl)
            _pk_r  = max(_pk_r * 0.88, rr)

threading.Thread(target=_audio_thread, daemon=True).start()

# ── Playerctl ─────────────────────────────────────────────────────────────────
_song_cache = ("", "", 0.0)

def _get_song():
    global _song_cache
    title, artist, ts = _song_cache
    if time.monotonic() - ts < 2.0:
        return title, artist
    try:
        if shutil.which('playerctl'):
            t = subprocess.run(['playerctl','metadata','title'],
                               capture_output=True, text=True, timeout=1).stdout.strip()
            a = subprocess.run(['playerctl','metadata','artist'],
                               capture_output=True, text=True, timeout=1).stdout.strip()
        else:
            t = a = ""
    except:
        t = a = ""
    _song_cache = (t[:44], a[:32], time.monotonic())
    return t[:44], a[:32]

# ── Color LED por altura ──────────────────────────────────────────────────────
def _seg_col(frac):
    """0=abajo verde → 1=arriba rojo, estilo EQ retro clásico"""
    if frac < 0.55:
        t = frac / 0.55
        return (20, int(155 + t * 85), 30)           # verde oscuro → verde vivo
    elif frac < 0.78:
        t = (frac - 0.55) / 0.23
        return (int(t * 255), 230, 20)               # verde → amarillo
    elif frac < 0.92:
        t = (frac - 0.78) / 0.14
        return (255, int(230 - t * 160), 20)         # amarillo → naranja
    else:
        t = (frac - 0.92) / 0.08
        return (255, int(70 - t * 60), int(t * 150)) # naranja → rojo

# ── Helpers ───────────────────────────────────────────────────────────────────
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal', 'acpitz']:
            if k in t: return t[k][0].current
    except: pass
    return None

def _gpu_pct():
    try:
        r = subprocess.run(['cat', '/sys/class/drm/card1/device/gpu_busy_percent'],
                           capture_output=True, text=True, timeout=1)
        if r.returncode == 0: return int(r.stdout.strip())
    except: pass
    return None

def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu', 'nvidia', 'radeon']:
            if k in t: return t[k][0].current
    except: pass
    return None

def _val_col(v, warn=70, crit=90):
    if v < warn:  return (28, 185, 95)
    if v < crit:  return (215, 155, 15)
    return (215, 50, 50)

# ── Colores ───────────────────────────────────────────────────────────────────
BG      = (6, 8, 35)
BG_PC   = (9, 11, 44)
LINE    = (25, 35, 85)
TXT_DIM = (80, 100, 180)
TXT_BRT = (180, 200, 255)

def _gauge(d, x, y, w, h, pct, col):
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(18, 22, 65))
    fw = max(h, int(w * min(pct, 100) / 100))
    d.rounded_rectangle([x, y, x + fw, y + h], radius=h // 2, fill=col)

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    global _peaks
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    with _lock:
        bars = _bars.copy()

    no_signal = (not _ok) or bars.max() < 0.005
    if no_signal:
        t2 = frame * 0.05
        for i in range(N_BARS):
            bars[i] = max(0, (math.sin(t2 + i * 0.8) * 0.22 + 0.26) *
                             (math.sin(t2 * 0.5 + i * 0.4) * 0.18 + 0.52))

    bars = np.clip(bars, 0, 1)

    # Expansión de rango dinámico: el percentil 20 actúa como piso
    # → las bandas más bajas se aplanan y las altas se destacan
    if bars.max() > 0.12:
        floor = np.percentile(bars, 20) * 0.75
        bars  = np.clip((bars - floor) / max(1 - floor, 0.1), 0, 1)

    bars   = np.power(bars, 0.80)
    energy = float(bars.mean())

    for i in range(N_BARS):
        if bars[i] > _peaks[i]:
            _peaks[i] = bars[i]
        else:
            _peaks[i] = max(0, _peaks[i] - 0.010)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL IZQUIERDO — 8 barras EQ
    # ══════════════════════════════════════════════════════════════════════════
    bar_slot = EQ_W / N_BARS
    bw       = max(1, int(bar_slot) - 6)

    # Grid horizontal sutil
    for gy in range(EQ_TOP, EQ_BOT, STEP * 5):
        d.line([(0, gy), (EQ_W, gy)], fill=(14, 18, 55), width=1)

    for i, lvl in enumerate(bars):
        lvl      = min(float(lvl), 1.0)
        x        = int(i * bar_slot) + 3
        n_active = max(1, int(N_SEGS * lvl))

        for s in range(n_active):
            frac = s / max(N_SEGS - 1, 1)
            col  = _seg_col(frac)
            sy   = EQ_BOT - (s + 1) * STEP
            if sy < EQ_TOP: break
            d.rectangle([x, sy, x + bw, sy + SEG_H - 1], fill=col)
            hl = tuple(min(255, int(c * 1.4)) for c in col)
            d.line([(x, sy), (x + bw, sy)], fill=hl, width=1)

        # Peak dot
        pk = _peaks[i]
        if pk > 0.05:
            ps = min(N_SEGS - 1, int(N_SEGS * pk))
            py = EQ_BOT - (ps + 1) * STEP
            if py >= EQ_TOP:
                pcol   = _seg_col(ps / max(N_SEGS - 1, 1))
                bright = tuple(min(255, c + 110) for c in pcol)
                d.rectangle([x, py, x + bw, py + SEG_H - 1], fill=bright)

        # Etiqueta de banda debajo
        lx = x + bw // 2
        d.text((lx, EQ_BOT + 6), BAND_LABELS[i], font=fnt(13),
               fill=TXT_DIM, anchor='mt')

    # Línea baseline EQ
    d.line([(0, EQ_BOT), (EQ_W, EQ_BOT)], fill=LINE, width=1)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL DERECHO — datos PC
    # ══════════════════════════════════════════════════════════════════════════
    d.rectangle([PC_X, 0, W, H], fill=BG_PC)
    d.line([(PC_X, 0), (PC_X, H)], fill=LINE, width=1)

    now          = datetime.datetime.now()
    song, artist = _get_song()
    px           = PC_X + 14
    pw           = PC_W - 22   # ancho útil del panel

    # Canción / título
    song_lbl = song[:22] if song else ("MUSIC" if not no_signal else "SIN SEÑAL")
    d.text((px, 6),  song_lbl,             font=fnt(28), fill=TXT_BRT)
    d.text((px, 36), artist[:28] if artist else "", font=fnt(16), fill=TXT_DIM)

    # Reloj
    d.text((W - 10, 8), now.strftime("%H:%M"), font=fnt(28),
           fill=TXT_DIM, anchor='ra')
    d.text((W - 10, 36), now.strftime("%d/%m"), font=fnt(14),
           fill=(50, 70, 140), anchor='ra')

    d.line([(PC_X + 8, 60), (W - 8, 60)], fill=LINE, width=1)

    # Datos sistema
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    ct  = _temp()
    gpu = _gpu_pct()
    gt  = _gtemp()

    stats = [
        ("CPU", f"{cpu:.0f}%", _val_col(cpu),
         f"{ct:.0f}°C" if ct else ""),
        ("RAM", f"{(mem.total-mem.available)/1024**3:.1f}G", _val_col(mem.percent),
         f"{mem.percent:.0f}%"),
        ("GPU", f"{gpu:.0f}%" if gpu is not None else "—", _val_col(gpu or 0),
         f"{gt:.0f}°C" if gt else ""),
    ]

    sy = 68
    for label, val, col_v, sub in stats:
        # Label + sub
        d.text((px, sy),      label, font=fnt(16), fill=TXT_DIM)
        d.text((W - 10, sy),  sub,   font=fnt(16), fill=TXT_DIM, anchor='ra')
        # Valor grande
        d.text((px, sy + 16), val,   font=fnt(52), fill=col_v)
        # Gauge
        pct = cpu if label == "CPU" else (mem.percent if label == "RAM" else (gpu or 0))
        _gauge(d, px, sy + 70, pw, 10, pct, col_v)
        sy += 130
        d.line([(PC_X + 8, sy - 6), (W - 8, sy - 6)], fill=LINE, width=1)

    # Pulso de energía
    e_r   = max(4, int(4 + energy * 14))
    e_col = _seg_col(min(1.0, energy * 2.5))
    ex    = PC_X + PC_W // 2
    ey    = H - 20
    if frame % 5 < 4:
        d.ellipse([ex - e_r, ey - e_r, ex + e_r, ey + e_r], fill=e_col)

    return img
