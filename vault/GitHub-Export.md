# GitHub Export

Guide to publishing this project on GitHub.

---

## What to include vs exclude

### Include

- All `.py` files (`display-engine.py`, `themes/*.py`)
- `fonts/` directory — all `.ttf` files (all are free/open source fonts)
- `tema.sh`
- `assets/fedora_logo.png` — Fedora logo is open source
- `assets/amd_ryzen_logo.png`, `assets/amd_logo.png` — AMD logos (see note)
- `assets/hud_bg2.png` — original artwork, safe to include
- `vault/` — this documentation
- `service/xyz-display@.service` — systemd service template (copy from `~/.config/systemd/user/`)

### Do NOT include

- `assets/starwars_battle.gif` — copyrighted Disney/Lucasfilm content
- `assets/ryzen_bg.jpg` — likely a copyrighted promotional image
- `themes/__pycache__/` — compiled bytecode
- `themes_backup_*/` — backup directories
- `gen_wallpaper_*.py` — internal tooling (optional, harmless to include)
- `hud_mockups.html` — internal prototyping file
- `skills-lock.json` — Claude Code internal file

> [!WARNING]
> The AMD logos are trademarked. Including them in a public repo is a gray area — AMD's brand guidelines allow use for informational/educational purposes but not commercial use. Document clearly that they are AMD's property.

---

## .gitignore

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/

# Backups and working dirs
themes_backup_*/
themes_backup*/

# Copyrighted / non-redistributable assets
assets/starwars_battle.gif
assets/ryzen_bg.jpg

# Claude Code internals
skills-lock.json
.claude/

# Internal tooling (optional — remove these lines to include them)
hud_mockups.html

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Virtual envs
venv/
.venv/
env/
```

---

## Suggested repo structure

```
xyz-display/
├── README.md                    # repo root README (see below)
├── display-engine.py
├── tema.sh
├── service/
│   └── xyz-display@.service     # systemd service template
├── themes/
│   ├── __init__.py
│   ├── empire.py
│   ├── hud.py
│   ├── hud_cyan.py
│   ├── matrix.py
│   ├── music.py
│   ├── music2.py
│   ├── phantom.py
│   ├── phantom_night.py
│   ├── pipboy.py
│   ├── retrowave.py
│   ├── ryzen.py
│   ├── ryzen2.py
│   ├── ryzen9.py
│   └── starwars.py
├── fonts/
│   ├── Orbitron-Black.ttf
│   ├── Orbitron-Bold.ttf
│   ├── Rajdhani-SemiBold.ttf
│   ├── ShareTechMono.ttf
│   ├── Teko-Medium.ttf
│   ├── NotoSansMono-Bold.ttf
│   ├── Quantico-Bold.ttf
│   ├── Exo2-Bold.ttf
│   ├── CaskaydiaMonoNF-SemiBold.ttf
│   ├── FiraCodeNerdFont-Medium.ttf
│   ├── JetBrainsMono-Bold.ttf
│   └── digital7.ttf
├── assets/
│   ├── fedora_logo.png
│   ├── amd_ryzen_logo.png
│   └── amd_logo.png
└── vault/
    ├── README.md
    ├── Installation.md
    ├── How-Themes-Work.md
    ├── Creating-a-Theme.md
    ├── Themes-Gallery.md
    ├── Sensors-Reference.md
    ├── tema-sh-Reference.md
    └── GitHub-Export.md
```

---

## Root README.md for GitHub

This goes at the repo root — it is what GitHub shows on the project page. Keep it short and link to vault docs for details.

```markdown
# xyz-display

Animated system stats on a USB secondary display (960x480 px).

Built with Python + PIL/Pillow. Runs as a systemd user service on Linux.

## 14 themes

| Theme | Description |
|---|---|
| `phantom` | White HUD for white PC cases |
| `phantom_night` | Dark version of phantom |
| `hud_cyan` | Cyan tactical cockpit HUD |
| `hud` | Blue tactical HUD |
| `starwars` | Hyperspace animation |
| `empire` | Dark Imperial Command |
| `matrix` | Matrix digital rain |
| `retrowave` | 80s synthwave scene |
| `pipboy` | Fallout Pip-Boy terminal |
| `ryzen` | AMD cyberpunk HUD |
| `ryzen2` | AMD HUD data-rich |
| `ryzen9` | AMD red fire HUD |
| `music` | Real-time audio visualizer |
| `music2` | Retrowave visualizer |

## Requirements

- Linux (tested on Fedora)
- Python 3.10+
- `pip install --user pillow psutil pyusb`
- USB display: VID `0x33c3`, PID `0xf101`

## Quick start

    git clone https://github.com/<user>/xyz-display ~/display
    cd ~/display
    pip install --user pillow psutil pyusb
    python3 display-engine.py ryzen      # run immediately
    bash tema.sh                          # interactive theme picker

## Autostart as a systemd service

    cp service/xyz-display@.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    bash tema.sh autostart ryzen

## Documentation

Full docs in [vault/](vault/):
- [Installation](vault/Installation.md)
- [How themes work](vault/How-Themes-Work.md)
- [Create a theme](vault/Creating-a-Theme.md)
- [Theme gallery](vault/Themes-Gallery.md)

## License

MIT. Fonts are under their own open-source licenses.
AMD logos are trademarks of Advanced Micro Devices, Inc.
```

---

## License recommendation

Use **MIT**. Create `LICENSE` in the repo root:

```
MIT License

Copyright (c) 2026 dg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## How others install it

The install flow for a new user:

```bash
# 1. Clone
git clone https://github.com/<user>/xyz-display ~/display

# 2. Python deps
pip install --user pillow psutil pyusb

# 3. USB permissions (udev rule)
sudo tee /etc/udev/rules.d/99-xyz-display.rules <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="33c3", ATTR{idProduct}=="f101", MODE="0666"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger

# 4. Test immediately
cd ~/display
python3 display-engine.py starwars

# 5. Install systemd service for autostart
cp service/xyz-display@.service ~/.config/systemd/user/
systemctl --user daemon-reload
bash tema.sh autostart starwars
```

> [!TIP]
> Consider adding an `install.sh` that automates steps 3–5: checks the udev rule, copies the service file, reloads systemd, and prompts for a default theme. Low effort, high impact for discoverability.

---

## Pushing from the current repo

```bash
cd ~/display

# Stage the right files
git add display-engine.py tema.sh themes/ fonts/ assets/ vault/ .gitignore
git status   # review before committing

git commit -m "Initial release: xyz-display with 14 themes"
git remote add origin https://github.com/<user>/xyz-display.git
git push -u origin main
```

> [!TIP]
> If `fonts/` is large (check with `du -sh fonts/`), consider Git LFS:
> ```bash
> git lfs track "fonts/*.ttf"
> git add .gitattributes
> ```

See [[Installation]] for the full setup instructions to copy into the repo.
