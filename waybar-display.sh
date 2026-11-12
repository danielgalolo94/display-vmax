#!/bin/bash
# XYZ Display - módulo waybar + selector de temas
THEME_FILE="/tmp/xyz_display_theme"
THEMES_DIR="$(dirname "$0")/themes"
SERVICE="xyz-display"

current_theme() {
    cat "$THEME_FILE" 2>/dev/null || echo "pipboy"
}

is_running() {
    systemctl --user is-active --quiet "$SERVICE@$(current_theme)"
}

output_json() {
    local theme
    theme=$(current_theme)
    if is_running; then
        printf '{"text":"󰍹 %s","tooltip":"XYZ Display: %s\nClick: cambiar tema | Right: detener","class":"active"}\n' "$theme" "$theme"
    else
        printf '{"text":"󰍹 off","tooltip":"XYZ Display inactivo\nClick: iniciar/cambiar | Right: iniciar","class":"inactive"}\n'
    fi
}

select_theme() {
    local themes=($(ls "$THEMES_DIR"/*.py | xargs -I{} basename {} .py))
    local selected
    selected=$(printf '%s\n' "${themes[@]}" | wofi --dmenu --prompt "Seleccionar Tema Display")
    
    if [ -n "$selected" ]; then
        # Parar servicio anterior, setear nuevo, arrancar
        systemctl --user stop "$SERVICE@$(current_theme)"
        echo "$selected" > "$THEME_FILE"
        systemctl --user start "$SERVICE@$selected"
        pkill -RTMIN+9 waybar
    fi
}

toggle_service() {
    local theme=$(current_theme)
    if is_running; then
        systemctl --user stop "$SERVICE@$theme"
    else
        systemctl --user start "$SERVICE@$theme"
    fi
    sleep 0.5
    pkill -RTMIN+9 waybar
}

case "${1:-}" in
    "select") select_theme ;;
    "toggle") toggle_service ;;
    *)        output_json ;;
esac
