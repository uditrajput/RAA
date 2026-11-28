@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM RAA Launcher for Windows (Setup UI + MCP Server)
REM Usage:
REM   scripts\start_raa.bat              Start both Setup UI and MCP HTTP server
REM   scripts\start_raa.bat --ui-only    Start Setup UI only
REM   scripts\start_raa.bat --mcp-only   Start MCP HTTP server only
REM   scripts\start_raa.bat --mcp-stdio  Start MCP server in stdio mode (foreground)
REM   scripts\start_raa.bat --no-open    Do not auto-open browser
REM ============================================================================

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if not defined UI_HOST set "UI_HOST=127.0.0.1"
if not defined UI_PORT set "UI_PORT=8765"
if not defined MCP_HOST set "MCP_HOST=127.0.0.1"
if not defined MCP_PORT set "MCP_PORT=8766"
if not defined MCP_TRANSPORT set "MCP_TRANSPORT=http"

set "RUN_UI=1"
set "RUN_MCP=1"
set "OPEN_BROWSER=1"

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--ui-only" (
    set "RUN_MCP=0"
) else if /i "%~1"=="--mcp-only" (
    set "RUN_UI=0"
) else if /i "%~1"=="--mcp-stdio" (
    set "RUN_UI=0"
    set "MCP_TRANSPORT=stdio"
    set "OPEN_BROWSER=0"
) else if /i "%~1"=="--no-open" (
    set "OPEN_BROWSER=0"
) else (
    echo Unknown option: %~1
    exit /b 1
)
shift
goto parse_args
:args_done

if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_BIN=%REPO_ROOT%\.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Neither .venv\Scripts\python.exe nor system python was found.
        exit /b 1
    )
    set "PYTHON_BIN=python"
)

if /i "%MCP_TRANSPORT%"=="stdio" (
    "%PYTHON_BIN%" -m raa.cli.main serve mcp --transport stdio
    exit /b %errorlevel%
)

echo [RAA] Using Python: %PYTHON_BIN%
echo [RAA] Workspace:    %REPO_ROOT%

if "%RUN_UI%"=="1" (
    echo [RAA] Starting Setup UI & API at http://%UI_HOST%:%UI_PORT%/setup ...
    start "RAA Setup UI (%UI_HOST%:%UI_PORT%)" cmd /k "cd /d "%REPO_ROOT%" && "%PYTHON_BIN%" -m raa.cli.main serve api --host %UI_HOST% --port %UI_PORT%"
)

if "%RUN_MCP%"=="1" (
    echo [RAA] Starting MCP Server (%MCP_TRANSPORT%) at http://%MCP_HOST%:%MCP_PORT%/mcp ...
    start "RAA MCP Server (%MCP_HOST%:%MCP_PORT%)" cmd /k "cd /d "%REPO_ROOT%" && "%PYTHON_BIN%" -m raa.cli.main serve mcp --transport %MCP_TRANSPORT% --host %MCP_HOST% --port %MCP_PORT%"
)

if "%RUN_UI%"=="1" if "%OPEN_BROWSER%"=="1" (
    timeout /t 2 /nobreak >nul
    start "" "http://%UI_HOST%:%UI_PORT%/setup"
)

echo [RAA] Launch complete. Close the spawned terminal windows to stop the servers.
endlocal
