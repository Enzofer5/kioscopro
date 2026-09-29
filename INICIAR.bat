@echo off
chcp 65001 >nul
title KioscoPro - Inicio
cd /d "%~dp0"
if not exist instance mkdir instance
echo %date% %time% INICIO >> instance\inicio.log

set PORT=5050
if exist .env for /f "tokens=2 delims==" %%a in ('findstr /b "PORT=" .env') do set PORT=%%a

rem Si ya esta funcionando, solo abre el navegador
netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul
if not errorlevel 1 (
  echo %date% %time% YA ESTABA FUNCIONANDO >> instance\inicio.log
  start "" http://127.0.0.1:%PORT%
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ tildando "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist venv (
  echo Creando entorno virtual...
  python -m venv venv
)
call venv\Scripts\activate.bat

echo Verificando dependencias...
pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Error instalando dependencias.
  pause
  exit /b 1
)

if not exist .env (
  echo Creando configuracion de DEMO con SQLite...
  python -c "import secrets;open('.env','w',encoding='utf-8').write('APP_ENV=development\nSECRET_KEY='+secrets.token_hex(32)+'\nDATABASE_URL=sqlite:///instance/kiosco_demo.db\nNEGOCIO_NOMBRE=Kiosco Demo\nHOST=0.0.0.0\nPORT=5050\n')"
  flask seed-demo
) else (
  flask init-db
)

echo Iniciando KioscoPro en segundo plano...
echo %date% %time% LANZANDO SERVIDOR >> instance\inicio.log
start "" venv\Scripts\pythonw.exe run.py

rem Espera hasta 20 segundos a que el servidor responda
set /a INTENTOS=0
:esperar
timeout /t 1 /nobreak >nul
set /a INTENTOS+=1
netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul
if not errorlevel 1 goto listo
if %INTENTOS% lss 20 goto esperar
echo.
echo El servidor no arranco. Revisa el archivo instance\servidor.log
pause
exit /b 1

:listo
echo.
echo ==========================================================
echo  KioscoPro funcionando en http://127.0.0.1:%PORT%
echo  Desde el celular (misma red Wi-Fi): http://IP-DE-ESTA-PC:%PORT%
echo  Queda funcionando aunque cierres esta ventana.
echo  Para apagarlo: doble clic en DETENER.bat
echo ==========================================================
start "" http://127.0.0.1:%PORT%
timeout /t 5 >nul
