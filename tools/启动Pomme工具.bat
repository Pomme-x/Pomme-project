@echo off
setlocal
set "DIR=%~dp0"
set "SCRIPT=%DIR%pomme_tool.py"
set "CHK=import pymupdf, PIL"

set "SYSW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
set "SYSPY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
set "BUNDLEDW=C:\Users\tom\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\pythonw.exe"
set "BUNDLEDPY=C:\Users\tom\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

rem ---- 1. pick a Python that has pymupdf + Pillow (system python first) ----
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

rem ---- 2. try pythonw from PATH ----
where pythonw >nul 2>nul
if not errorlevel 1 (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "%CHK%" >nul 2>nul
        if not errorlevel 1 (
            start "" pythonw "%SCRIPT%"
            exit /b
        )
    )
)

rem ---- 3. install dependencies ----
echo.
echo Pomme tool is missing dependencies: pymupdf / Pillow
echo Installing now, please wait (network required)...
echo.
if exist "%SYSPY%" (
    echo [1/2] system Python
    "%SYSPY%" -m pip install --disable-pip-version-check --timeout 60 --retries 2 pymupdf pillow
)
if exist "%BUNDLEDPY%" (
    echo [2/2] DSH bundled Python
    "%BUNDLEDPY%" -m pip install --disable-pip-version-check --timeout 60 --retries 2 pymupdf pillow
)

rem ---- 4. re-check ----
if exist "%SYSPY%" (
    "%SYSPY%" -c "%CHK%" >nul 2>nul
    if not errorlevel 1 (
        echo Installed OK. Starting...
        start "" "%SYSW%" "%SCRIPT%"
        exit /b
    )
)
if exist "%BUNDLEDPY%" (
    "%BUNDLEDPY%" -c "%CHK%" >nul 2>nul
    if not errorlevel 1 (
        echo Installed OK. Starting...
        start "" "%BUNDLEDW%" "%SCRIPT%"
        exit /b
    )
)

echo.
echo Install failed. Run manually:
echo   "%SYSPY%" -m pip install pymupdf pillow
echo Then double-click this file again.
pause
