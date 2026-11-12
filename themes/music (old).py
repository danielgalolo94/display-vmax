"""
Tema: MUSIC VISUALIZER — captura real del audio del sistema
Detecta dinámicamente qué sink PipeWire está activo (HDMI, analógico, etc.)
y captura su monitor con parec.
Display landscape 960x480
"""
import subprocess, threading, math, datetime, shutil, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H  = 960, 480
import os
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT  = os.path.join(_BASE, "fonts", "Teko-Medium.ttf")

def fnt(size):
    try:    return ImageFont.truetype(FONT, size)
    except: return ImageFont.load_default()

BG    = (4,   4,  10)
DIM   = (22,  28,  45)
WHITE = (220, 230, 255)
CYAN  = (0,  200, 255)
DCYAN = (0,   40,  70)

N_BARS      = 64
SAMPLE_RATE = 48000
FFT_SIZE    = 4096
CHANNELS    = 2
BYTES_FRAME = 2 * CHANNELS   # s16le

# ── Estado compartido ─────────────────────────────────────────────────────────
_lock  = threading.Lock()
_bars  = np.zeros(N_BARS)
_wave  = np.zeros(256)
_vu_l  = 0.0
_vu_r  = 0.0
_pk_l  = 0.0
_pk_r  = 0.0
_ok    = False
_src   = ""

# ── Detectar monitor del sink activo ─────────────────────────────────────────
def _find_active_monitor():
    """
    Sigue el sink donde está reproduciendo audio en este momento.
    1. sink-inputs → qué sink está en uso
    2. sinks short  → nombre del sink → + '.monitor'
    Fallback: cualquier fuente monitor en estado RUNNING.
    """
    try:
        # ¿Qué sinks tienen entradas activas?
        si = subprocess.run(['pactl','list','sink-inputs','short'],
                            capture_output=True, text=True, timeout=2).stdout
        active_sink_ids = set()
        for line in si.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                active_sink_ids.add(parts[1])

        if active_sink_ids:
            # Obtener nombre del sink
            sinks = subprocess.run(['pactl','list','sinks','short'],
                                   capture_output=True, text=True, timeout=2).stdout
            for line in sinks.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0] in active_sink_ids:
                    return parts[1] + '.monitor'

        # Fallback: monitor RUNNING
        sources = subprocess.run(['pactl','list','sources','short'],
                                 capture_output=True, text=True, timeout=2).stdout
        for line in sources.splitlines():
            if 'monitor' in line and 'RUNNING' in line:
                return line.split()[1]

        # Último recurso: cualquier monitor
        for line in sources.splitlines():
            if 'monitor' in line:
                return line.split()[1]
    except Exception as e:
        print(f"[music] pactl: {e}")
    return None

# ── Hilo de captura ────────────────────────────────────────────────────────────
def _audio_thread():
    global _bars, _wave, _vu_l, _vu_r, _pk_l, _pk_r, _ok, _src

    smooth  = np.zeros(N_BARS)
    proc    = None
    cur_mon = None

    while True:
        # Detectar monitor activo (se re-evalúa si cambia el sink)
        mon = _find_active_monitor()

        if mon != cur_mon:
            # Matar proceso anterior si cambió la fuente
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
            # (Re)arrancar parec
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

        # Leer un bloque
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

        # FFT logarítmica en dB
        mono = (L + R) * 0.5
        win  = mono * np.hanning(len(mono))
        fft  = np.abs(np.fft.rfft(win, n=FFT_SIZE))
        fft  = 20 * np.log10(np.maximum(fft, 1e-9))
        fft  = np.clip((fft + 80) / 80, 0, 1)

        freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)
        bins  = np.logspace(np.log10(20), np.log10(20000), N_BARS + 1)
        b     = np.zeros(N_BARS)
        for i in range(N_BARS):
            mask = (freqs >= bins[i]) & (freqs < bins[i+1])
            if mask.any():
                b[i] = np.max(fft[mask])

        # Suavizado: subida rápida, caída lenta
        smooth = np.where(b > smooth,
                          b * 0.65 + smooth * 0.35,
                          smooth * 0.80)

        # Waveform decimada
        step = max(1, len(mono) // 256)
        wv   = mono[::step][:256]

        with _lock:
            _bars = smooth.copy()
            if len(wv) == 256:
                _wave = wv.copy()
            _vu_l = rl
            _vu_r = rr
            _pk_l = max(_pk_l * 0.88, rl)
            _pk_r = max(_pk_r * 0.88, rr)

        # Re-verificar sink cada ~5 segundos por si cambió el audio
        # (cada iteración son ~85ms, 60 iteraciones ≈ 5s)
        # No hay delay aquí — el read() ya bloquea ~85ms

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

# ── Color de barra ────────────────────────────────────────────────────────────
def _bar_col(idx, total, level):
    r = idx / total
    if r < 0.25:
        col = (0, int(120 + r*4*135), 255)
    elif r < 0.5:
        t2 = (r-0.25)*4; col = (0, 255, int(255-t2*255))
    elif r < 0.75:
        t2 = (r-0.5)*4;  col = (int(t2*255), 255, 0)
    else:
        t2 = (r-0.75)*4; col = (255, int(255-t2*210), 0)
    br = 0.15 + level * 0.85
    return tuple(int(c * br) for c in col), tuple(int(c * br * 0.18) for c in col)

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    with _lock:
        bars = _bars.copy()
        wave = _wave.copy()
        vl   = _vu_l;  vr  = _vu_r
        pkl  = _pk_l;  pkr = _pk_r

    energy   = float(bars.mean())
    now      = datetime.datetime.now()
    song, artist = _get_song()

    no_signal = (not _ok) or bars.max() < 0.005
    if no_signal:
        t = frame * 0.07
        for i in range(N_BARS):
            bars[i] = max(0, (math.sin(t + i*0.28)*0.35 + 0.38) *
                            (math.sin(t*0.6 + i*0.18)*0.25 + 0.55))
        vl = vr = max(0, math.sin(t)*0.3 + 0.3)
        pkl = pkr = 0.6
        wave = np.array([math.sin(t*3 + i*0.12)*0.5 for i in range(256)])

    # ── Info superior (0..88px) ───────────────────────────────────────────────
    INFO_H = 88
    for y in range(INFO_H):
        a2 = int(12 + (1 - y/INFO_H)**2 * 30)
        d.line([(0,y),(W,y)], fill=(a2//3, a2//2, a2))

    if song:
        d.text((14, 6),  song,   font=fnt(48), fill=WHITE)
        d.text((14, 56), artist, font=fnt(26), fill=(100,130,180))
    else:
        d.text((14, 8), "MUSIC VISUALIZER", font=fnt(52), fill=CYAN)
        status = "sin señal — audio en " + (_src.replace('alsa_output.','').replace('.monitor','')[:30] if _src else "?") if no_signal else "silencio"
        d.text((14, 60), status, font=fnt(20), fill=DIM)

    d.text((W-182, 8),  now.strftime("%H:%M"),    font=fnt(48), fill=(50,65,95))
    d.text((W-152, 56), now.strftime("%d/%m/%Y"), font=fnt(22), fill=DIM)

    # Barra de energía
    ew = int(energy * W * 1.8)
    d.line([(0,INFO_H-2),(W,INFO_H-2)], fill=(12,18,32), width=2)
    d.line([(0,INFO_H-2),(min(W,ew),INFO_H-2)], fill=CYAN, width=2)

    # ── Ecualizador (88..368px) ───────────────────────────────────────────────
    EQ_T = INFO_H + 4
    EQ_B = 368
    EQ_H = EQ_B - EQ_T

    bar_w = W // N_BARS
    gap   = max(1, bar_w // 5)
    bw    = bar_w - gap

    for pct in [25, 50, 75, 100]:
        gy = EQ_B - int(EQ_H * pct / 100)
        d.line([(0,gy),(W,gy)], fill=(10,14,24))

    for i, lvl in enumerate(bars):
        x   = i * bar_w
        bh  = max(2, int(EQ_H * min(lvl, 1.0)))
        col, col_dim = _bar_col(i, N_BARS, lvl)

        d.rectangle([x, EQ_B-bh, x+bw, EQ_B], fill=col_dim)
        bright_h = max(2, bh*2//5)
        d.rectangle([x, EQ_B-bh, x+bw, EQ_B-bh+bright_h], fill=col)
        d.line([(x,EQ_B-bh),(x+bw,EQ_B-bh)], fill=(180,200,220), width=1)

        rh = min(bh//6, 18)
        for ri in range(rh):
            alpha = 1.0 - ri/rh
            rc = tuple(int(c*alpha*0.22) for c in col)
            d.line([(x, EQ_B+ri+1),(x+bw, EQ_B+ri+1)], fill=rc)

    d.line([(0,EQ_B),(W,EQ_B)], fill=(30,40,60))

    # ── Waveform + VU (368..480px) ────────────────────────────────────────────
    WV_T  = EQ_B + 4
    WV_B  = H - 14
    WV_H  = WV_B - WV_T
    WV_CY = WV_T + WV_H // 2

    for y in range(WV_T, H):
        d.line([(0,y),(W-180,y)], fill=(4,5,12))

    if len(wave) == 256:
        step_x = (W-184) / 256
        pts = [(int(i*step_x), int(WV_CY - wave[i]*(WV_H//2-4))) for i in range(256)]
        for i in range(len(pts)-1):
            seg_col = _bar_col(i*N_BARS//256, N_BARS, abs(float(wave[i])))[0]
            d.line([pts[i], pts[i+1]], fill=seg_col, width=2)

    d.line([(0,WV_CY),(W-184,WV_CY)], fill=(18,24,40))

    # Etiquetas de frecuencia
    for li, lbl in enumerate(["20","50","100","200","500","1k","2k","5k","10k","20k"]):
        xi = li * (N_BARS//10) * bar_w + 2
        d.text((xi, EQ_B+2), lbl, font=fnt(13), fill=(35,50,75))

    # ── VU Meters (derecha) ───────────────────────────────────────────────────
    VU_X  = W - 175
    VU_W  = 75
    VU_T2 = WV_T - 2
    VU_B2 = WV_B
    VU_H2 = VU_B2 - VU_T2

    def vu_chan(cx, level, peak, label):
        N   = 20
        sh  = max(2, (VU_H2-N)//N)
        act = int(level*N)
        pk  = int(peak*N)
        d.text((cx+VU_W//2-7, VU_T2-18), label, font=fnt(16), fill=DIM)
        for si in range(N):
            sy = VU_B2-(si+1)*(sh+1)
            r2 = si/N
            on  = (0,200,80) if r2<0.60 else (255,190,0) if r2<0.85 else (255,40,40)
            off = tuple(c//7 for c in on)
            d.rectangle([cx,sy,cx+VU_W-2,sy+sh], fill=on if si<act else off)
        if 0 < pk < N:
            psy = VU_B2-(pk+1)*(sh+1)
            d.rectangle([cx,psy,cx+VU_W-2,psy+sh], fill=(240,245,255))
        db  = 20*math.log10(max(level,1e-9))
        d.text((cx, VU_B2+2), f"{db:.0f}dB" if db>-40 else "-∞", font=fnt(13), fill=(40,65,90))

    vu_chan(VU_X,         vl, pkl, "L")
    vu_chan(VU_X+VU_W+4, vr, pkr, "R")

    # Fuente activa (pie de página)
    if _src:
        label = _src.replace('alsa_output.','').replace('.pci-','').replace('.monitor','')
        d.text((14, H-14), label[:50], font=fnt(13), fill=(20,28,45))

    return img
