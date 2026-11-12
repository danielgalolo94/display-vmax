@echo off
setlocal
rem Lanza el motor del display en Windows, sin la app de XYZ Nexus.
rem Uso: run_display_windows.bat [tema]   (por defecto: ryzen9)

cd /d "%~dp0"

set "THEME=%~1"
if "%THEME%"=="" set "THEME=ryzen9"

if not exist "themes\%THEME%.py" (
    echo [display] Tema no encontrado: %THEME%
    echo [display] Temas disponibles:
    dir /b themes\*.py
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo [display] Python no esta en el PATH.
    pause
    exit /b 1
)

python -c "import usb.core, PIL, psutil" >nul 2>&1
if errorlevel 1 (
    echo [display] Instalando dependencias ^(pyusb, pillow, psutil, libusb-package^)...
    python -m pip install -q pyusb pillow psutil libusb-package
    if errorlevel 1 (
        echo [display] Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
)

echo [display] Si la app XYZ Nexus Software esta abierta, cerrala antes: tiene el dispositivo tomado.
echo [display] Tema: %THEME%  ^(Ctrl+C para salir^)
python display-engine.py %THEME%

echo [display] El motor termino.
pause
endlocal
