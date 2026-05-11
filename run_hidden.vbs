Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' LIMPEZA: Mata instâncias antigas antes de iniciar (modo oculto e aguarda terminar)
' Mata o servidor
WshShell.Run "powershell -Command " & chr(34) & "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*server.js*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" & chr(34), 0, True
' Mata o cliente
WshShell.Run "powershell -Command " & chr(34) & "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" & chr(34), 0, True

' Inicia o Servidor (Node.js)
WshShell.Run "cmd /c cd /d " & chr(34) & strPath & "\server" & chr(34) & " && node src/server.js", 0, False

' Aguarda 2 segundos para o servidor estabilizar
WScript.Sleep 2000

' Inicia o Cliente (Python)
WshShell.Run "cmd /c cd /d " & chr(34) & strPath & "\client" & chr(34) & " && python main.py", 0, False
