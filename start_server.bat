@echo off
title W.A.N.D. Server
echo Iniciando W.A.N.D. Server...
cd /d %~dp0\server
npm start
pause
