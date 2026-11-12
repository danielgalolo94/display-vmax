#!/usr/bin/env python3
"""
XYZ Display Engine - Carga temas dinámicamente y envía al display
Uso: python3 display-engine.py [tema]
"""
import sys, os, time, signal, importlib.util, threading, select, glob
import usb.core, usb.util, io
import psutil
from PIL import Image

VID, PID   = 0x33c3, 0xf101
IDLE_SECS  = 30 * 60          # 30 minutos → reposo
EVENT_SZ   = 24               # struct input_event en Linux 64-bit
PREV_FILE  = os.path.join(os.path.expanduser("~"), ".local", "share",
                           "xyz-display", "theme_before_repose")

def _input_devices():
    """Devuelve rutas de eventos de teclado y mouse."""
    devs = set()
    bp = "/dev/input/by-path/"
    try:
        for name in os.listdir(bp):
            if any(k in name for k in ("kbd", "mouse", "event-kbd")):
                target = os.readlink(os.path.join(bp, name))
                devs.add(os.path.join("/dev/input", os.path.basename(target)))
    except: pass
    # fallback: todos los event devices
    if not devs:
        devs = set(glob.glob("/dev/input/event[0-9]*"))
    return list(devs)

def start_idle_watcher(theme_file, prev_file):
    last_activity = [time.monotonic()]
    in_repose     = [False]

    def _watcher():
        fds = []
        for path in _input_devices():
            try:
                fds.append(open(path, "rb"))
            except PermissionError:
                pass

        if not fds:
            print("[idle] Sin acceso a /dev/input — watcher desactivado.")
            return

        print(f"[idle] Monitoreando {len(fds)} dispositivo(s). "
              f"Reposo a los {IDLE_SECS//60} min de inactividad.")

        while True:
            readable, _, _ = select.select(fds, [], [], 1.0)
            if readable:
                for f in readable:
                    try: f.read(EVENT_SZ)
                    except: pass
                last_activity[0] = time.monotonic()

                # Si estábamos en reposo, despertar
                if in_repose[0]:
                    try:
                        with open(prev_file) as pf:
                            prev = pf.read().strip()
                        with open(theme_file, "w") as tf:
                            tf.write(prev)
                        print(f"[idle] Actividad detectada → volviendo a '{prev}'")
                    except Exception as e:
                        print(f"[idle] Error al despertar: {e}")
                    in_repose[0] = False

            idle = time.monotonic() - last_activity[0]
            if idle >= IDLE_SECS and not in_repose[0]:
                try:
                    with open(theme_file) as tf:
                        current = tf.read().strip()
                    if current != "repose":
                        os.makedirs(os.path.dirname(prev_file), exist_ok=True)
                        with open(prev_file, "w") as pf:
                            pf.write(current)
                        with open(theme_file, "w") as tf:
                            tf.write("repose")
                        print(f"[idle] {idle/60:.0f} min inactivo → reposo "
                              f"(guardando '{current}')")
                except Exception as e:
                    print(f"[idle] Error al entrar en reposo: {e}")
                in_repose[0] = True

    threading.Thread(target=_watcher, daemon=True, name="idle-watcher").start()
EP_OUT   = 0x02
IFACE    = 1

THEMES_DIR = os.path.join(os.path.dirname(__file__), "themes")
_STATE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "xyz-display")
THEME_FILE = os.path.join(_STATE_DIR, "theme")

def load_theme(name):
    path = os.path.join(THEMES_DIR, f"{name}.py")
    if not os.path.exists(path):
        print(f"Tema '{name}' no encontrado en {THEMES_DIR}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(f"Tema cargado: {name}")
    return mod

def connect():
    # Desatar cdc_acm del dispositivo si está enganchado
    import glob
    for iface_path in glob.glob("/sys/bus/usb/devices/*:*"):
        dev_path = os.path.dirname(iface_path)
        vendor_file = os.path.join(dev_path, "idVendor")
        if os.path.exists(vendor_file):
            try:
                if open(vendor_file).read().strip() == "33c3":
                    base = os.path.basename(iface_path)
                    os.system(f"echo '{base}' > /sys/bus/usb/drivers/cdc_acm/unbind 2>/dev/null")
            except Exception:
                pass

    # En Windows hace falta indicar el backend libusb (DLL de libusb-package)
    backend = None
    try:
        import libusb_package
        import usb.backend.libusb1 as _lb
        backend = _lb.get_backend(find_library=lambda x: libusb_package.find_library(x))
    except Exception:
        pass
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    if not dev:
        print("Display USB no encontrado"); sys.exit(1)
    for iface in [0,1]:
        try:
            if dev.is_kernel_driver_active(iface):
                dev.detach_kernel_driver(iface)
        except: pass
    try:
        dev.set_configuration()
    except usb.core.USBError:
        pass
    usb.util.claim_interface(dev, IFACE)
    return dev

def main():
    theme_name = sys.argv[1] if len(sys.argv) > 1 else "starwars"
    theme = load_theme(theme_name)

    dev   = connect()
    frame = 0
    running = True

    os.makedirs(_STATE_DIR, exist_ok=True)
    with open(THEME_FILE, 'w') as f: f.write(theme_name)
    start_idle_watcher(THEME_FILE, PREV_FILE)

    def stop(sig, _):
        nonlocal running; running = False
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    psutil.cpu_percent(interval=None)
    print(f"Display activo: {theme_name}. Ctrl+C para salir.")

    while running:
        # Cambio de tema en caliente
        try:
            with open(THEME_FILE) as f:
                new_name = f.read().strip()
            if new_name != theme_name:
                theme_name = new_name
                theme = load_theme(theme_name)
                frame = 0
                print(f"Cambiando a tema: {theme_name}")
        except: pass

        try:
            img = theme.render(frame)
            
            # Normalizamos: el hardware espera un buffer portrait de 480x960.
            # Como la pantalla está montada físicamente a 90° CCW, para que se vea 
            # de forma apaisada (landscape) y al derecho, debemos procesar una imagen 
            # de 960x480 con una transposición específica.
            
            # Si el tema es vertical (480x960), lo estiramos a horizontal para que
            # al rotarlo quede "al derecho" en el gabinete.
            if img.width == 480 and img.height == 960:
                img = img.resize((960, 480), Image.Resampling.LANCZOS)
                
            # Si es (o ahora es) 960x480, aplicamos el giro para el hardware
            if img.width == 960 and img.height == 480:
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).transpose(Image.Transpose.TRANSPOSE)
            
            # Garantizamos que lo que sale al USB sea siempre 480x960
            if img.width != 480 or img.height != 960:
                img = img.resize((480, 960), Image.Resampling.LANCZOS)
                
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=88)
            dev.write(EP_OUT, buf.getvalue(), timeout=5000)
            frame += 1
        except usb.core.USBError as e:
            print(f"USB error: {e} — reintentando...")
            time.sleep(2)
            try: dev = connect()
            except: pass
        except Exception as e:
            print(f"Error render: {e}")

        time.sleep(0.2)   # 5 fps

    usb.util.release_interface(dev, IFACE)
    print(f"Detenido. {frame} frames.")

if __name__ == '__main__':
    main()
