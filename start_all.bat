@echo off
title W.A.N.D. Manager
echo === W.A.N.D. Integrated Startup ===

echo [1/2] Limpando processos antigos...
taskkill /f /fi "windowtitle eq W.A.N.D. Server" >nul 2>&1
taskkill /f /fi "windowtitle eq W.A.N.D. Client" >nul 2>&1

echo [2/2] Iniciando Server e Client...
start "W.A.N.D. Server" cmd /c "start_server.bat"
timeout /t 2 >nul
start "W.A.N.D. Client" cmd /c "start_client.bat"

echo.
echo Tudo pronto! O Servidor e o Cliente estao subindo em janelas separadas.
echo Voce pode fechar esta janela se desejar.
timeout /t 5
exit
