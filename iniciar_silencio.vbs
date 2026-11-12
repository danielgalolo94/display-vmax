' Lanza Display VMAX (motor + icono de bandeja) sin ventana.
' Uso: wscript iniciar_silencio.vbs [tema]   (por defecto: vmax)
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
theme = "vmax"
If WScript.Arguments.Count > 0 Then theme = WScript.Arguments(0)
sh.CurrentDirectory = dir
pyw = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Microsoft\WindowsApps\pythonw.exe"
sh.Run """" & pyw & """ """ & dir & "display_todo.pyw"" " & theme, 0, False
