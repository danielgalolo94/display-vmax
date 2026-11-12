#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/display"

echo "=== XYZ Display — Instalación ==="
echo ""

# 1. Dependencias sistema
echo "[1/5] Instalando dependencias del sistema..."
sudo apt update -qq
sudo apt install -y python3 python3-pip python3-pil python3-psutil lm-sensors alsa-utils \
    fonts-noto-cjk

# 2. pyusb via pip (no está en apt)
echo "[2/5] Instalando pyusb..."
python3 -m pip install --user pyusb 2>/dev/null || python3 -m pip install --user --break-system-packages pyusb

# 3. Copiar la app
echo "[3/5] Copiando app a $INSTALL_DIR..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  -> $INSTALL_DIR ya existe, actualizando..."
    rsync -a --exclude='__pycache__' "$SCRIPT_DIR/" "$INSTALL_DIR/"
else
    cp -r "$SCRIPT_DIR" "$INSTALL_DIR"
fi
chmod +x "$INSTALL_DIR/tema.sh" "$INSTALL_DIR/waybar-display.sh"

# 4. Regla udev USB
echo "[4/5] Configurando acceso USB sin root..."
sudo tee /etc/udev/rules.d/99-xyz-display.rules > /dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="33c3", ATTR{idProduct}=="f101", MODE="0666"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger

# 5. Servicio systemd
echo "[5/5] Instalando servicio systemd..."
mkdir -p "$HOME/.config/systemd/user"
# Ajustar path en el service file al directorio real de instalación
sed "s|/home/dg/display|$INSTALL_DIR|g" \
    "$SCRIPT_DIR/systemd/xyz-display@.service" \
    > "$HOME/.config/systemd/user/xyz-display@.service"
systemctl --user daemon-reload

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
