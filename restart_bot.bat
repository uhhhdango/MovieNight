@echo off
echo Stopping bot...

:: Kill any running pythonw.exe processes that point to your bot
taskkill /IM pythonw.exe /FI "WINDOWTITLE eq pythonw.exe X:\MovieNight\MovieNight\main.py" /F >nul 2>&1

:: Optional: force kill any pythonw.exe
:: taskkill /IM pythonw.exe /F >nul 2>&1

echo Starting bot...
powershell -WindowStyle Hidden -Command ^
  "Start-Process pythonw.exe 'X:\MovieNight\MovieNight\main.py' -WindowStyle Hidden -RedirectStandardOutput 'X:\MovieNight\MovieNight\bot_output.log' -RedirectStandardError 'X:\MovieNight\MovieNight\bot_error.log'"

echo Done.
