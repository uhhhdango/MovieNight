@echo off
powershell -WindowStyle Hidden -Command "Start-Process pythonw.exe 'main.py' -WindowStyle Hidden -RedirectStandardOutput 'bot_output.log' -RedirectStandardError 'bot_error.log'"
