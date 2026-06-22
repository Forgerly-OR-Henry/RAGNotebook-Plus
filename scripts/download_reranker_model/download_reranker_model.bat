@echo off
setlocal EnableExtensions

set "NO_PAUSE="
if /I "%~1"=="--no-pause" (
    set "NO_PAUSE=1"
    shift
)

set "PROJECT_ROOT=%CD%"
if not exist "%PROJECT_ROOT%\scripts\download_reranker_model\download_reranker_model.py" (
    for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
)
pushd "%PROJECT_ROOT%" >nul

set "PYTHON_EXE=%PROJECT_ROOT%\backend\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" "%PROJECT_ROOT%\scripts\download_reranker_model\download_reranker_model.py" %*
set "SCRIPT_EXIT_CODE=%ERRORLEVEL%"

popd >nul
if not defined NO_PAUSE pause
exit /b %SCRIPT_EXIT_CODE%
