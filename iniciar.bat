@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicializacao Unificado
REM 1) Legado  2) Nova versao (pipeline + live em loop continuo)
REM ==============================================================================

setlocal enabledelayedexpansion

if not exist "venv" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo Execute setup.bat primeiro para configurar o ambiente.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar venv.
    pause
    exit /b 1
)

if exist "data\klines_cache.db" (
    set DATA_STRATEGY=active
) else (
    set DATA_STRATEGY=inactive
)

if exist "config\symbols_extended.py" (
    set SYMBOLS_MODE=expanded
) else (
    set SYMBOLS_MODE=standard
)

for /f "usebackq delims=" %%i in (`python -c "from config.settings import M2_EXECUTION_MODE; print(M2_EXECUTION_MODE)"`) do set "M2_MODE=%%i"
for /f "usebackq delims=" %%i in (`python -c "from config.settings import M2_LIVE_SYMBOLS; print(','.join(M2_LIVE_SYMBOLS))"`) do set "M2_SYMBOLS=%%i"

if "!M2_SYMBOLS!"=="" set "M2_SYMBOLS=BTCUSDT"
if "!M2_MODE!"=="" set "M2_MODE=shadow"
if "%M2_LOOP_SECONDS%"=="" set "M2_LOOP_SECONDS=300"
if "%M2_RUN_ONCE%"=="" set "M2_RUN_ONCE=0"

echo.
echo ========================================
echo  Crypto Futures Agent - Iniciar.bat
echo  Data Cache: !DATA_STRATEGY!
echo  Symbols Mode: !SYMBOLS_MODE!
echo  M2 Mode: !M2_MODE!
echo  M2 Symbols: !M2_SYMBOLS!
echo  M2 Loop Seconds: !M2_LOOP_SECONDS!
echo ========================================
echo.
echo [1] Legado (menu.py)
echo [2] Nova versao (daily_pipeline + live_cycle + healthcheck em loop)
echo [0] Sair
echo.
set /p CHOICE="Escolha uma opcao: "
set "CHOICE=%CHOICE: =%"
set "CHOICE=%CHOICE:~0,1%"

if "%CHOICE%"=="1" goto LEGACY_MENU
if "%CHOICE%"=="2" goto M2_VERSION_LOOP
if "%CHOICE%"=="0" goto END

echo [ERRO] Opcao invalida.
goto END

:BUILD_ARGS
set "LIVE_SYMBOL_ARGS="
set "PIPELINE_SYMBOL_ARGS="
for %%S in (%M2_SYMBOLS:,= %) do (
    if not "%%~S"=="" (
        set "LIVE_SYMBOL_ARGS=!LIVE_SYMBOL_ARGS! --live-symbol %%~S"
        set "PIPELINE_SYMBOL_ARGS=!PIPELINE_SYMBOL_ARGS! --symbol %%~S"
    )
)
exit /b 0

:LEGACY_MENU
echo.
echo [RUN] python menu.py
python menu.py
goto END

:M2_VERSION_LOOP
call :BUILD_ARGS
echo.
echo [INFO] Modo continuo ativado. Use Ctrl+C para interromper.
if "!M2_RUN_ONCE!"=="1" echo [INFO] M2_RUN_ONCE=1: executara apenas um ciclo.

:M2_LOOP
echo.
echo [RUN] python scripts/model2/daily_pipeline.py --timeframe H4 --continue-on-error !PIPELINE_SYMBOL_ARGS!
python scripts/model2/daily_pipeline.py --timeframe H4 --continue-on-error !PIPELINE_SYMBOL_ARGS!
if %errorlevel% neq 0 (
    echo [ALERTA] daily_pipeline retornou erro.
)

echo.
echo [RUN] python scripts/model2/live_cycle.py --timeframe H4 --execution-mode !M2_MODE! !LIVE_SYMBOL_ARGS!
python scripts/model2/live_cycle.py --timeframe H4 --execution-mode !M2_MODE! !LIVE_SYMBOL_ARGS!
if %errorlevel% neq 0 (
    echo [ALERTA] live_cycle retornou erro.
)

echo.
echo [RUN] python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime --max-age-hours 2 --max-unprotected-filled 0 --max-stale-entry-sent 0 --max-position-mismatches 0
python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime --max-age-hours 2 --max-unprotected-filled 0 --max-stale-entry-sent 0 --max-position-mismatches 0
if %errorlevel% neq 0 echo [ALERTA] Healthcheck live retornou alert.

if "!M2_RUN_ONCE!"=="1" goto END

echo.
echo [INFO] Aguardando !M2_LOOP_SECONDS!s para o proximo ciclo...
timeout /t !M2_LOOP_SECONDS! >nul
goto M2_LOOP

:END
echo.
pause
exit /b 0
