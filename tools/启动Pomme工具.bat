@echo off
chcp 65001 >nul
title Pomme 博客小工具
set "SCRIPT=%~dp0pomme_tool.py"
set "BUNDLEDW=C:\Users\tom\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\pythonw.exe"
set "SYSW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"

if exist "%BUNDLEDW%" (
    start "" "%BUNDLEDW%" "%SCRIPT%"
    exit /b
)
if exist "%SYSW%" (
    start "" "%SYSW%" "%SCRIPT%"
    exit /b
)
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 "%SCRIPT%"
    exit /b
)
start "" pythonw "%SCRIPT%"
