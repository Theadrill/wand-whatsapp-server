Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' Inicia o Servidor (Node.js) - Entra na pasta server e executa
WshShell.Run "cmd /c cd /d " & chr(34) & strPath & "\server" & chr(34) & " && node src/server.js", 0, False

' Aguarda 2 segundos para o servidor estabilizar
WScript.Sleep 2000

' Inicia o Cliente (Python) - Entra na pasta client e executa
' Usamos o modo 0 para esconder a janela do console que o python abriria
WshShell.Run "cmd /c cd /d " & chr(34) & strPath & "\client" & chr(34) & " && python main.py", 0, False
