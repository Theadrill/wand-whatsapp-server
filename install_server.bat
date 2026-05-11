@echo off
title Instalando Dependencias do Servidor
echo Instalando modulos Node.js...
cd /d %~dp0\server
npm install
echo.
echo Concluido!
pause
