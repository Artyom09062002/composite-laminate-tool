@echo off
setlocal
title Composite Laminate Design and Analysis Tool

cd /d "%~dp0"
if errorlevel 1 goto :fail

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo Creating a private Python environment for this project...
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 (
        py -3.11 -m venv ".venv"
    ) else (
        python -m venv ".venv"
    )
    if errorlevel 1 goto :fail
)

if not exist "%VENV_PY%" goto :fail
echo Checking project dependencies...
"%VENV_PY%" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :fail

if /I "%~1"=="--check" (
    echo Running automated checks...
    "%VENV_PY%" -m unittest discover -s tests -v
    if errorlevel 1 goto :fail
    echo All checks passed.
    exit /b 0
)

echo Starting the app. Your browser should open automatically.
echo If it does not, open the Local URL printed below (usually http://localhost:8501).
echo Keep this window open. Press Ctrl+C here to stop the app.
"%VENV_PY%" -m streamlit run app.py --server.headless false --server.showEmailPrompt false --browser.gatherUsageStats false
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo Could not start or check the app. Read the error above.
echo Check that Python 3.11 is installed and that the internet is available for first-time setup.
pause
exit /b 1
