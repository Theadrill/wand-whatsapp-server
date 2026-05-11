@echo off
setlocal
cd /d "%~dp0"

title W.A.N.D. Manager
echo === W.A.N.D. Integrated Startup (Silent Mode) ===

echo [1/2] Limpando processos antigos (Server e Client)...
:: Mata processos Node que estão rodando o server.js
powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*server.js*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
:: Mata processos Python que estão rodando o main.py
powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo [2/2] Iniciando Server e Client em segundo plano...
:: Usa o VBS para rodar sem abrir janelas de terminal
cscript //nologo run_hidden.vbs

echo.
echo Concluido! O servidor e o cliente estao rodando em segundo plano.
echo Os icones devem aparecer na bandeja do sistema (perto do relogio).
echo.
timeout /t 5
exit
