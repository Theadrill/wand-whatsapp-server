@echo off
title W.A.N.D. Server
echo Encerrando instancias anteriores...
taskkill /f /fi "windowtitle eq W.A.N.D. Server" >nul 2>&1

echo Iniciando W.A.N.D. Server...
cd /d %~dp0\server
npm start
pause
