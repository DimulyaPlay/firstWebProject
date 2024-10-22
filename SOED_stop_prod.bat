@echo off
cd /d %~dp0
call taskkill /F /IM nginx.exe /T
pause