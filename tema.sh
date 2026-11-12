#!/bin/bash
# Selector de temas para el display XYZ
# Uso: ./tema.sh [nombre|list|stop|restart|current]

THEME_FILE="$HOME/.local/share/xyz-display/theme"
THEMES_DIR="$(dirname "$(realpath "$0")")/themes"
ENGINE="$(dirname "$(realpath "$0")")/display-engine.py"

# ── Helpers ───────────────────────────────────────────────────────────────────
current_theme() {
    cat "$THEME_FILE" 2>/dev/null || echo ""
}

autostart_theme() {
    ls ~/.config/systemd/user/default.target.wants/xyz-display@*.service 2>/dev/null \
        | head -1 \
        | sed 's/.*xyz-display@//; s/\.service//'
}

engine_running() {
    pgrep -f "display-engine.py" > /dev/null 2>&1
}

# Lista temas: excluye __init__ y archivos que empiecen con _
list_themes() {
    for f in "$THEMES_DIR"/*.py; do
        name=$(basename "$f" .py)
        [[ "$name" == __* ]] && continue
        [[ "$name" == _*  ]] && continue
        echo "$name"
    done | sort
}

# Extrae la descripción del docstring (línea "Tema: ...")
theme_desc() {
    local name="$1"
    local f="$THEMES_DIR/$name.py"
    grep -m1 "Tema:" "$f" 2>/dev/null | sed 's/.*Tema:[[:space:]]*//' | tr -d '"' || echo "$name"
}

# ── Menú interactivo ──────────────────────────────────────────────────────────
show_menu() {
    local cur; cur=$(current_theme)
    local boot; boot=$(autostart_theme)
    local status
    if engine_running; then
        status="● ACTIVO"
    else
        status="○ detenido"
    fi

    clear
    echo ""
    echo "  ╔════════════════════════════════════════════════════╗"
    echo "  ║          XYZ DISPLAY — SELECTOR DE TEMAS          ║"
    echo "  ╚════════════════════════════════════════════════════╝"
    echo ""
    printf "  Engine: %-20s  Tema actual: %s\n" "$status" "${cur:-(ninguno)}"
    printf "  Arranque automático: %s\n" "${boot:-(ninguno)}"
    echo ""
    echo "  ─────────────────────────────────────────────────────"

    local i=1
    local themes=()
    while IFS= read -r t; do
        themes+=("$t")
        local desc; desc=$(theme_desc "$t")
        local marker="  "
        [[ "$t" == "$cur" ]] && marker="► "
        printf "  %s[%2d]  %-14s  %s\n" "$marker" "$i" "$t" "$desc"
        ((i++))
    done < <(list_themes)

    echo "  ─────────────────────────────────────────────────────"
    echo "   [a]  Setear tema de arranque"
    echo "   [s]  Detener display"
    echo "   [q]  Salir"
    echo ""
    read -rp "  Elegí un número o acción: " choice

    case "$choice" in
        q) exit 0 ;;
        s) stop_display; exit 0 ;;
        a) pick_autostart; show_menu; return ;;
        ''|*[!0-9]*)
            echo "  Opción inválida"
            sleep 1
            show_menu ;;
        *)
            if [ "$choice" -ge 1 ] && [ "$choice" -le "${#themes[@]}" ]; then
                set_theme "${themes[$((choice-1))]}"
            else
                echo "  Número fuera de rango"
                sleep 1
                show_menu
            fi ;;
    esac
}

# ── Acciones ──────────────────────────────────────────────────────────────────
set_theme() {
    local name="$1"
    if [ ! -f "$THEMES_DIR/$name.py" ]; then
        echo "✗ Tema '$name' no existe. Disponibles:"
        list_themes
        exit 1
    fi

    mkdir -p "$(dirname "$THEME_FILE")"
    echo "$name" > "$THEME_FILE"
    echo "✓ Tema → $name"

    if ! engine_running; then
        echo "  Iniciando engine..."
        nohup python3 "$ENGINE" "$name" >/tmp/xyz-display.log 2>&1 &
        echo "  Engine iniciado (PID $!)"
    else
        echo "  Aplicado en caliente"
    fi
}

set_autostart() {
    local name="$1"
    if [ ! -f "$THEMES_DIR/$name.py" ]; then
        echo "✗ Tema '$name' no existe."
        exit 1
    fi
    # deshabilitar instancias previas (eliminando symlinks directamente)
    rm -f ~/.config/systemd/user/default.target.wants/xyz-display@*.service
    systemctl --user enable "xyz-display@$name.service"
    echo "✓ Arranque automático → $name"
}

pick_autostart() {
    local cur_boot; cur_boot=$(autostart_theme)
    clear
    echo ""
    echo "  ── SETEAR TEMA DE ARRANQUE ──────────────────────────"
    echo "  Actual: ${cur_boot:-(ninguno)}"
    echo ""
    local i=1
    local themes=()
    while IFS= read -r t; do
        themes+=("$t")
        local marker="  "
        [[ "$t" == "$cur_boot" ]] && marker="► "
        printf "  %s[%2d]  %s\n" "$marker" "$i" "$t"
        ((i++))
    done < <(list_themes)
    echo ""
    echo "   [0]  Deshabilitar arranque automático"
    echo "   [q]  Cancelar"
    echo ""
    read -rp "  Elegí un número: " choice
    case "$choice" in
        q|'') return ;;
        0)
            rm -f ~/.config/systemd/user/default.target.wants/xyz-display@*.service
            echo "✓ Arranque automático deshabilitado"
            sleep 1 ;;
        *[0-9]*)
            if [ "$choice" -ge 1 ] && [ "$choice" -le "${#themes[@]}" ]; then
                set_autostart "${themes[$((choice-1))]}"
                sleep 1
            fi ;;
    esac
}

stop_display() {
    if engine_running; then
        pkill -f "display-engine.py" 2>/dev/null && echo "✓ Display detenido"
    else
        echo "  Display no estaba corriendo"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "${1:-}" in
    ""          ) show_menu ;;
    "list"      ) list_themes ;;
    "stop"      ) stop_display ;;
    "current"   ) current_theme ;;
    "restart"   ) stop_display; sleep 1; set_theme "$(current_theme)" ;;
    "status"    ) engine_running && echo "● activo: $(current_theme)" || echo "○ detenido" ;;
    "autostart" ) [ -n "$2" ] && set_autostart "$2" || autostart_theme ;;
    *           ) set_theme "$1" ;;
esac
