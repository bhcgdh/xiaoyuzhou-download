@echo off
cd /d "%~dp0"
call D:\anaconda3\Scripts\activate.bat py313
python server.py
pause
