@echo off
REM ==============================================================================
REM Short Agent Isolado - Loop continuo dedicado
REM Pipeline + Live Cycle em base separada (sem misturar com iniciar.bat legado)
REM ==============================================================================

setlocal enabledelayedexpansion

if not exist "venv" (
    echo [ERRO] Ambiente virtual nao encontrado.
    echo Execute setup.bat primeiro.
    exit /b 1
)

call venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar venv.
    exit /b 1
)

if "%SHORT_MODEL2_DB_PATH%"=="" set "SHORT_MODEL2_DB_PATH=db/modelo2_short_agent.db"
if "%SHORT_OUTPUT_DIR%"=="" set "SHORT_OUTPUT_DIR=results/model2_short/runtime"
if "%SHORT_LOOP_SECONDS%"=="" set "SHORT_LOOP_SECONDS=300"
if "%SHORT_RUN_ONCE%"=="" set "SHORT_RUN_ONCE=0"
if "%SHORT_EXECUTION_MODE%"=="" set "SHORT_EXECUTION_MODE=live"
if "%SHORT_MARGIN_USD%"=="" set "SHORT_MARGIN_USD=1.0"
if "%SHORT_LEVERAGE%"=="" set "SHORT_LEVERAGE=3"
if "%SHORT_FUNDING_MAX%"=="" set "SHORT_FUNDING_MAX=0.0005"
if "%SHORT_LOG_TO_FILE%"=="" set "SHORT_LOG_TO_FILE=0"
if "%SHORT_LOG_FILE%"=="" set "SHORT_LOG_FILE=logs\\short_agent_cycle.log"

if not exist "logs" mkdir logs

echo.
echo ==============================================
echo  Short Agent Isolado
echo  DB: %SHORT_MODEL2_DB_PATH%
echo  Output: %SHORT_OUTPUT_DIR%
echo  Mode: %SHORT_EXECUTION_MODE%
echo  Loop Seconds: %SHORT_LOOP_SECONDS%
echo  Run Once: %SHORT_RUN_ONCE%
echo  Log To File: %SHORT_LOG_TO_FILE%
echo ==============================================
echo.

set "RUN_ONCE_ARG="
if "%SHORT_RUN_ONCE%"=="1" set "RUN_ONCE_ARG=--run-once"

set "SYMBOL_ARGS="
if not "%SHORT_SYMBOLS%"=="" (
    for %%S in (%SHORT_SYMBOLS:,= %) do (
        if not "%%~S"=="" set "SYMBOL_ARGS=!SYMBOL_ARGS! --symbol %%~S"
    )
)

if "%SHORT_LOG_TO_FILE%"=="1" (
    echo [INFO] Saida redirecionada para %SHORT_LOG_FILE%
    python scripts/model2/live_cycle_short_agent.py ^
      --source-db-path db/crypto_agent.db ^
      --model2-db-path %SHORT_MODEL2_DB_PATH% ^
      --output-dir %SHORT_OUTPUT_DIR% ^
      --execution-mode %SHORT_EXECUTION_MODE% ^
      --loop-seconds %SHORT_LOOP_SECONDS% ^
      --max-margin-per-position-usd %SHORT_MARGIN_USD% ^
      --leverage %SHORT_LEVERAGE% ^
      --funding-rate-max-for-short %SHORT_FUNDING_MAX% ^
      !RUN_ONCE_ARG! ^
      !SYMBOL_ARGS! 1>>%SHORT_LOG_FILE% 2>&1
) else (
    echo [INFO] Saida UX no terminal (tempo real^)
    python scripts/model2/live_cycle_short_agent.py ^
      --source-db-path db/crypto_agent.db ^
      --model2-db-path %SHORT_MODEL2_DB_PATH% ^
      --output-dir %SHORT_OUTPUT_DIR% ^
      --execution-mode %SHORT_EXECUTION_MODE% ^
      --loop-seconds %SHORT_LOOP_SECONDS% ^
      --max-margin-per-position-usd %SHORT_MARGIN_USD% ^
      --leverage %SHORT_LEVERAGE% ^
      --funding-rate-max-for-short %SHORT_FUNDING_MAX% ^
      !RUN_ONCE_ARG! ^
      !SYMBOL_ARGS! 2>nul
)

set "RC=%errorlevel%"
if %RC% neq 0 (
    echo [ERRO] Short agent finalizou com erro. Consulte logs\short_agent_cycle.log
    exit /b %RC%
)

echo [OK] Short agent finalizado.
exit /b 0
