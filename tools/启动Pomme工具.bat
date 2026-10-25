@echo off
chcp 65001 >nul
title Pomme 博客小工具
set "SCRIPT=%~dp0pomme_tool.py"
set "BUNDLED=C:\Users\tom\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED%" (
    "%BUNDLED%" "%SCRIPT%"
    if errorlevel 1 pause
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%SCRIPT%"
    if errorlevel 1 pause
    goto :eof
)

python "%SCRIPT%"
if errorlevel 1 pause
