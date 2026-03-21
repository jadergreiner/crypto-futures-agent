@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicializacao
REM ==============================================================================

setlocal enabledelayedexpansion

if not exist "venv" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo Execute setup.bat primeiro para configurar o ambiente.
    exit /b 1
)

call venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar venv.
    exit /b 1
)

for /f "usebackq delims=" %%i in (`python -c "from config.settings import M2_EXECUTION_MODE; print(M2_EXECUTION_MODE)"`) do set "M2_MODE=%%i"
for /f "usebackq delims=" %%i in (`python -c "from config.settings import M2_LIVE_SYMBOLS; print(','.join(M2_LIVE_SYMBOLS))"`) do set "M2_SYMBOLS=%%i"

if "!M2_MODE!"=="" set "M2_MODE=shadow"
if "!M2_SYMBOLS!"=="" set "M2_SYMBOLS=BTCUSDT"

echo.
echo ========================================
echo  Crypto Futures Agent
echo  Modo: !M2_MODE!
echo  Simbolos: !M2_SYMBOLS!
echo ========================================
echo.

set "LOG_FILE=logs/startup_log.txt"
(
    echo [INFO] Agent startup at %date% %time%
    echo   M2 Mode: !M2_MODE!
    echo   M2 Symbols: !M2_SYMBOLS!
    echo ----------------------------------------
) >> %LOG_FILE%

echo [1] Iniciar model-driven
echo [0] Sair
echo.
set /p CHOICE="Escolha uma opcao: "
set "CHOICE=%CHOICE: =%"
set "CHOICE=%CHOICE:~0,1%"

if "%CHOICE%"=="1" goto MAIN_PY
if "%CHOICE%"=="0" goto END

echo [ERRO] Opcao invalida.
goto END

:MAIN_PY
echo.
echo [RUN] python main.py --mode !M2_MODE!
python main.py --mode !M2_MODE!
goto END

:END
echo.
echo [FIM] Pressione qualquer tecla para fechar...
pause >nul
exit /b 0
