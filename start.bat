@echo off
title AR System
cd /d "%~dp0"
echo Starting Accounts Receivable System...
echo.
echo  URL: http://localhost:5000
echo  Login: admin@lfg.com / admin123
echo.
echo  Press Ctrl+C to stop the server.
echo.
py app.py
pause
