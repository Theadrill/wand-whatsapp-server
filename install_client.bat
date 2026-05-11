@echo off
title Instalando Dependencias do Cliente
echo Instalando bibliotecas Python...
cd /d %~dp0
pip install -r client/requirements.txt
echo.
echo Concluido!
pause
