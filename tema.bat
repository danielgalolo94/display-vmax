@echo off
setlocal EnableDelayedExpansion
rem Selector de temas para el display en Windows (equivalente a tema.sh)
rem Uso: tema.bat [nombre|list|current|status|stop|restart|autostart [nombre]]
rem Sin argumentos abre el menu.

cd /d "%~dp0"
set "STATE_DIR=%USERPROFILE%\.local\share\xyz-display"
set "STATE=%STATE_DIR%\theme"
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Display VMAX.lnk"

if "%~1"=="" goto menu
if /i "%~1"=="list" goto cmd_list
if /i "%~1"=="current" goto cmd_current
if /i "%~1"=="status" goto cmd_status
if /i "%~1"=="stop" goto cmd_stop
if /i "%~1"=="restart" goto cmd_restart
if /i "%~1"=="autostart" goto cmd_autostart
goto cmd_set

rem ?? Helpers ?????????????????????????????????????????????

:build_list
set N=0
for %%f in ("themes\*.py") do (
    set "NM=%%~nf"
    set "SKIP="
    if "!NM:~0,1!"=="_" set "SKIP=1"
    echo !NM!| findstr /c:"(" >nul && set "SKIP=1"
    if not defined SKIP (
        set /a N+=1
        set "T!N!=!NM!"
    )
)
exit /b 0

:engine_running
set "RUN=0"
for /f %%r in ('powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match 'display_todo|display-engine' }) { '1' } else { '0' }"') do set "RUN=%%r"
exit /b 0

:current_theme
set "CUR="
if exist "%STATE%" set /p CUR=<"%STATE%"
exit /b 0

:autostart_theme
set "BOOT="
if exist "%LNK%" (
    for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%').Arguments"`) do set "BOOT=%%a"
)
exit /b 0

:set_theme
rem %1 = nombre de tema
if not exist "themes\%~1.py" (
    echo x Tema '%~1' no existe. Disponibles:
    call :build_list
    for /l %%i in (1,1,!N!) do echo   !T%%i!
    exit /b 1
)
if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"
> "%STATE%" echo %~1
echo ok Tema -^> %~1
call :engine_running
if "!RUN!"=="0" (
    echo   Iniciando engine...
    wscript //nologo "%~dp0iniciar_silencio.vbs" %~1
) else (
    echo   Aplicado en caliente
)
exit /b 0

:stop_engine
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match 'display_todo|display-engine' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
exit /b 0

rem ?? Comandos ????????????????????????????????????????????

:cmd_list
call :build_list
for /l %%i in (1,1,!N!) do echo !T%%i!
exit /b 0

:cmd_current
call :current_theme
echo %CUR%
exit /b 0

:cmd_status
call :engine_running
call :current_theme
if "!RUN!"=="1" (echo activo: %CUR%) else (echo detenido)
exit /b 0

:cmd_stop
call :engine_running
if "!RUN!"=="1" (
    call :stop_engine
    echo ok Display detenido
) else (
    echo Display no estaba corriendo
)
exit /b 0

:cmd_restart
call :current_theme
if "%CUR%"=="" (echo No hay tema actual. & exit /b 1)
call :stop_engine
timeout /t 1 /nobreak >nul
call :set_theme "%CUR%"
exit /b 0

:cmd_set
call :set_theme "%~1"
exit /b %errorlevel%

:cmd_autostart
if "%~2"=="" (
    call :autostart_theme
    if "!BOOT!"=="" (echo Arranque automatico: ^(ninguno^)) else (echo Arranque automatico: !BOOT!)
    exit /b 0
)
if not exist "themes\%~2.py" (echo x Tema '%~2' no existe. & exit /b 1)
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.Arguments='%~2'; $s.Save()"
echo ok Arranque automatico -^> %~2
exit /b 0

rem ?? Menu interactivo ???????????????????????????????????

:menu
call :build_list
call :current_theme
call :autostart_theme
call :engine_running
cls
echo.
echo   ======================================================
echo             XYZ DISPLAY - SELECTOR DE TEMAS
echo   ======================================================
echo.
if "!RUN!"=="1" (set "STATUS=ACTIVO") else (set "STATUS=detenido")
echo   Engine: !STATUS!     Tema actual: %CUR%
if "!BOOT!"=="" (echo   Arranque automatico: ^(ninguno^)) else (echo   Arranque automatico: !BOOT!)
echo.
echo   ------------------------------------------------------
for /l %%i in (1,1,!N!) do (
    set "MARK=  "
    if "!T%%i!"=="%CUR%" set "MARK=> "
    echo   !MARK![%%i]  !T%%i!
)
echo   ------------------------------------------------------
echo    [a]  Setear tema de arranque
echo    [s]  Detener display
echo    [q]  Salir
echo.
set "CH="
set /p CH=  Elegi un numero o accion:
if /i "!CH!"=="q" exit /b 0
if /i "!CH!"=="s" (call :cmd_stop & pause & exit /b 0)
if /i "!CH!"=="a" goto menu_autostart
if "!CH!"=="" goto menu
set "VALID="
for /f "delims=0123456789" %%x in ("!CH!") do set "VALID=no"
if defined VALID (echo   Opcion invalida & timeout /t 1 >nul & goto menu)
if !CH! lss 1 (echo   Numero fuera de rango & timeout /t 1 >nul & goto menu)
if !CH! gtr !N! (echo   Numero fuera de rango & timeout /t 1 >nul & goto menu)
call :set_theme "!T%CH%!"
pause
exit /b 0

:menu_autostart
call :build_list
call :autostart_theme
cls
echo.
echo   == SETEAR TEMA DE ARRANQUE ==
echo   Actual: !BOOT!
echo.
for /l %%i in (1,1,!N!) do (
    set "MARK=  "
    if "!T%%i!"=="!BOOT!" set "MARK=> "
    echo   !MARK![%%i]  !T%%i!
)
echo.
echo    [0]  Deshabilitar arranque automatico
echo    [q]  Cancelar
echo.
set "CH="
set /p CH=  Elegi un numero:
if /i "!CH!"=="q" goto menu
if "!CH!"=="" goto menu_autostart
if "!CH!"=="0" (
    powershell -NoProfile -Command "Remove-Item -LiteralPath '%LNK%' -ErrorAction SilentlyContinue"
    echo ok Arranque automatico deshabilitado
    pause
    goto menu
)
if !CH! lss 1 goto menu_autostart
if !CH! gtr !N! goto menu_autostart
call :cmd_autostart x "!T%CH%!"
pause
goto menu
