"""
Display VMAX en un solo proceso: el motor (display-engine.py) en el hilo
principal y el icono de la bandeja en un hilo aparte.
Si se cierra el icono ("Salir"), se apaga el motor con el mismo cierre limpio
que usa display-engine.py (libera el USB).
Uso: pythonw display_todo.pyw [tema]     (por defecto: vmax)
"""
import os, sys, signal, threading, importlib.util
import pystray
from PIL import Image, ImageDraw

BASE   = os.path.dirname(os.path.abspath(__file__))
THEMES = os.path.join(BASE, "themes")
STATE  = os.path.join(os.path.expanduser("~"), ".local", "share", "xyz-display", "theme")

def list_themes():
    out = []
    for f in sorted(os.listdir(THEMES)):
        if f.endswith(".py"):
            name = f[:-3]
            if not name.startswith("_") and "(" not in name:
                out.append(name)
    return out

def current():
    try:
        with open(STATE) as f:
            return f.read().strip()
    except Exception:
        return ""

def set_theme(name):
    # el motor relee este archivo en cada frame: cambio en caliente
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        f.write(name)

def make_icon_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 60, 60], radius=12, fill=(4, 12, 26, 255),
                        outline=(0, 232, 255, 255), width=3)
    d.arc([14, 14, 50, 50], 135, 405, fill=(0, 232, 255, 255), width=5)
    d.ellipse([27, 27, 37, 37], fill=(255, 176, 0, 255))
    return img

def run_tray():
    def theme_item(name):
        def on_pick(icon, item):
            set_theme(name)
        def is_checked(item):
            return current() == name
        return pystray.MenuItem(name, on_pick, checked=is_checked, radio=True)

    def on_quit(icon, item):
        icon.stop()
        # cierre limpio del motor: mismo camino que Ctrl+C
        signal.raise_signal(signal.SIGINT)

    menu = pystray.Menu(
        pystray.MenuItem("Tema", pystray.Menu(*[theme_item(t) for t in list_themes()])),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir (apaga display e icono)", on_quit),
    )
    icon = pystray.Icon("vmax_display", make_icon_image(), "Display VMAX", menu)
    icon.run()

def main():
    theme = sys.argv[1] if len(sys.argv) > 1 else "vmax"
    # cargar el motor sin ejecutar su main()
    spec = importlib.util.spec_from_file_location(
        "display_engine", os.path.join(BASE, "display-engine.py"))
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)

    threading.Thread(target=run_tray, daemon=True, name="tray").start()

    sys.argv = ["display-engine.py", theme]
    engine.main()   # bloquea hasta el cierre; corre en el hilo principal

if __name__ == "__main__":
    main()
