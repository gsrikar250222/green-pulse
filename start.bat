@echo off
title GreenPulse Agriculture Platform
cls
echo =================================================================
echo   GreenPulse Agriculture Platform - Server Launcher
echo =================================================================
echo.

set PYTHON_CMD=C:\Users\chebr\AppData\Local\Programs\PythonEmbedded\python.exe

if not exist "%PYTHON_CMD%" (
    set PYTHON_CMD=python
)

"%PYTHON_CMD%" "%~dp0run_server.py"
pause

