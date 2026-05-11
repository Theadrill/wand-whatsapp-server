@echo off
title W.A.N.D. Client
echo Encerrando instancias anteriores...
taskkill /f /fi "windowtitle eq W.A.N.D. Client" >nul 2>&1

echo Iniciando W.A.N.D. Client...
cd /d %~dp0
python client/main.py
pause
