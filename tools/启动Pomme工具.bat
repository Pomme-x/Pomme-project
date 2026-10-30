@echo off
chcp 65001 >nul
title Pomme 博客小工具
set "DIR=%~dp0"
set "SCRIPT=%DIR%pomme_tool.py"
set "CHK=import pymupdf, PIL"

set "SYSW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
set "SYSPY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
set "BUNDLEDW=C:\Users\tom\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\pythonw.exe"
set "BUNDLEDPY=C:\Users\tom\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

rem ---------- 1. 找一个装了 pymupdf + Pillow 的 Python（系统 Python 优先） ----------
rem 注意：用 python.exe 检查（会等待并返回退出码），再用 pythonw.exe 启动界面
if exist "%SYSPY%" (
    "%SYSPY%" -c "%CHK%" >nul 2>nul
    if not errorlevel 1 (
        if exist "%SYSW%" (
            start "" "%SYSW%" "%SCRIPT%"
        ) else (
            start "" "%SYSPY%" "%SCRIPT%"
        )
        exit /b
    )
)
if exist "%BUNDLEDPY%" (
    "%BUNDLEDPY%" -c "%CHK%" >nul 2>nul
    if not errorlevel 1 (
        if exist "%BUNDLEDW%" (
            start "" "%BUNDLEDW%" "%SCRIPT%"
        ) else (
            start "" "%BUNDLEDPY%" "%SCRIPT%"
        )
        exit /b
    )
)

rem ---------- 2. 都没有依赖：自动安装 ----------
echo.
echo Pomme 小工具缺少依赖（pymupdf / Pillow），正在自动安装……
echo 需要联网，请稍等……
echo.
if exist "%SYSPY%" (
    echo [1/2] 安装到系统 Python
    "%SYSPY%" -m pip install --disable-pip-version-check --timeout 60 --retries 2 pymupdf pillow
)
if exist "%BUNDLEDPY%" (
    echo [2/2] 安装到 DSH 自带 Python
    "%BUNDLEDPY%" -m pip install --disable-pip-version-check --timeout 60 --retries 2 pymupdf pillow
)

rem ---------- 3. 安装完再检查一次 ----------
if exist "%SYSPY%" (
    "%SYSPY%" -c "%CHK%" >nul 2>nul
    if not errorlevel 1 (
        echo 安装成功，正在启动……
        start "" "%SYSW%" "%SCRIPT%"
        exit /b
    )
)
if exist "%BUNDLEDPY%" (
    "%BUNDLEDPY%" -c "%CHK%" >nul 2>nul
    if not errorlevel 1 (
        echo 安装成功，正在启动……
        start "" "%BUNDLEDW%" "%SCRIPT%"
        exit /b
    )
)

echo.
echo 依赖安装失败。请手动在命令行运行：
echo   "%SYSPY%" -m pip install pymupdf pillow
echo 然后再双击本文件。
pause
