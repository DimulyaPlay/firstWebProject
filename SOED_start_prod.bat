@echo off
cd /d %~dp0
call taskkill /F /IM nginx.exe /T
call venv\Scripts\activate.bat
call app_nginx.py
pause