#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/display"

echo "=== XYZ Display — Instalación (Arch Linux) ==="
echo ""

# 1. Dependencias sistema
echo "[1/5] Instalando dependencias del sistema..."
sudo pacman -Sy --noconfirm
sudo pacman -S --noconfirm --needed python python-pip python-pillow python-psutil \
    python-pyusb lm_sensors alsa-utils noto-fonts-cjk

# 2. pyusb ya instalado via pacman arriba

# 3. Copiar la app
echo "[2/5] Copiando app a $INSTALL_DIR..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  -> $INSTALL_DIR ya existe, actualizando..."
    rsync -a --exclude='__pycache__' "$SCRIPT_DIR/" "$INSTALL_DIR/"
else
    cp -r "$SCRIPT_DIR" "$INSTALL_DIR"
fi
chmod +x "$INSTALL_DIR/tema.sh" "$INSTALL_DIR/waybar-display.sh"

# 4. Regla udev USB
echo "[3/5] Configurando acceso USB sin root..."
sudo tee /etc/udev/rules.d/99-xyz-display.rules > /dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="33c3", ATTR{idProduct}=="f101", MODE="0666"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger

# 5. Servicio systemd
echo "[4/5] Instalando servicio systemd..."
mkdir -p "$HOME/.config/systemd/user"
sed "s|/home/dg/display|$INSTALL_DIR|g" \
    "$SCRIPT_DIR/systemd/xyz-display@.service" \
    > "$HOME/.config/systemd/user/xyz-display@.service"
systemctl --user daemon-reload

# 6. pyusb via pip por si acaso
echo "[5/5] Verificando pyusb..."
python -c "import usb" 2>/dev/null || python -m pip install --user pyusb

echo ""
echo "=== Instalación completa ==="
echo ""
echo "Conectá el display y arrancá con:"
echo "  bash $INSTALL_DIR/tema.sh ryzen"
echo ""
echo "Para autostart en login:"
echo "  bash $INSTALL_DIR/tema.sh autostart ryzen"
echo ""
echo "Temas disponibles:"
ls "$INSTALL_DIR/themes/"*.py | xargs -I{} basename {} .py | grep -v '__init__' | sort | sed 's/^/  - /'
