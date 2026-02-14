@echo off
REM ==============================================================================
REM Crypto Futures Agent - Windows Setup Script
REM ==============================================================================
REM This script sets up the development environment for the Crypto Futures Agent
REM on Windows systems. It handles Python environment setup, dependency
REM installation, and initial configuration.
REM ==============================================================================

setlocal enabledelayedexpansion

echo.
echo ==============================================================================
echo                   CRYPTO FUTURES AGENT - SETUP
echo ==============================================================================
echo.

REM Check if Python is installed
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

python --version
echo [OK] Python is installed
echo.

REM Check Python version (must be 3.10+)
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%
echo.

REM Create virtual environment if it doesn't exist
echo [2/7] Setting up virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/7] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo [4/7] Upgrading pip...
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing...
) else (
    echo [OK] pip upgraded
)
echo.

REM Install dependencies
echo [5/7] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies!
    echo.
    echo Please check your internet connection and try again.
    echo If the problem persists, try installing dependencies manually:
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Check and copy .env file
echo [6/7] Checking configuration...
if not exist ".env" (
    if exist ".env.example" (
        echo Copying .env.example to .env...
        copy .env.example .env >nul
        echo [OK] .env file created from template
        echo.
        echo ============================================================
        echo [ACTION REQUIRED] Please configure your .env file!
        echo ============================================================
        echo.
        echo You need to add your Binance API credentials to .env:
        echo   1. Open .env in a text editor
        echo   2. Add your BINANCE_API_KEY
        echo   3. Add your BINANCE_API_SECRET
        echo   4. Set TRADING_MODE to 'paper' for testnet or 'live' for production
        echo.
        echo For security, you can also use Ed25519 authentication:
        echo   - Set BINANCE_PRIVATE_KEY_PATH and BINANCE_PRIVATE_KEY_PASSPHRASE
        echo.
        echo ============================================================
        echo.
    ) else (
        echo [WARNING] .env.example not found!
        echo Please create a .env file manually with your configuration.
    )
) else (
    echo [OK] .env file exists
)
echo.

REM Create necessary directories
echo [7/7] Creating project directories...
if not exist "db" mkdir db
if not exist "logs" mkdir logs
if not exist "models" mkdir models
echo [OK] Directories created: db, logs, models
echo.

echo ==============================================================================
echo                        SETUP COMPLETED SUCCESSFULLY!
echo ==============================================================================
echo.
echo Next steps:
echo.
echo   1. Make sure your .env file is configured with Binance API credentials
echo.
echo   2. Initialize the database and collect historical data:
echo      python main.py --setup
echo.
echo   3. (Optional) Train the RL model:
echo      python main.py --train
echo.
echo   4. Start the agent in paper trading mode:
echo      python main.py --mode paper
echo.
echo   5. Or start the agent in live trading mode (use with caution!):
echo      python main.py --mode live
echo.
echo For more information, see README.md
echo ==============================================================================
echo.

REM Ask if user wants to run initial setup
set /p RUN_SETUP="Do you want to run initial setup now? (y/n): "
if /i "%RUN_SETUP%"=="y" (
    echo.
    echo Running initial setup...
    echo This will initialize the database, collect historical data, and calculate indicators...
    echo This may take several minutes...
    echo.
    python main.py --setup
    if %errorlevel% neq 0 (
        echo.
        echo [WARNING] Setup encountered errors. Please check the logs.
    ) else (
        echo.
        echo [OK] Initial setup completed successfully!
    )
) else (
    echo.
    echo Skipping initial setup. Run it later with: python main.py --setup
)

echo.
echo Press any key to exit...
pause >nul
