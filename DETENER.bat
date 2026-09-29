@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist instance\servidor.pid (
  echo KioscoPro no esta funcionando.
  timeout /t 3 >nul
  exit /b 0
)
for /f %%p in (instance\servidor.pid) do taskkill /PID %%p /F >nul 2>nul
del instance\servidor.pid >nul 2>nul
echo KioscoPro detenido.
timeout /t 3 >nul
