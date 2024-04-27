cd /d %~dp0
call python -m venv venv
call venv\Scripts\activate.bat
call pip install --no-index --find-links=./deps -r requirements.txt

