@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicializacao
REM ==============================================================================

setlocal enabledelayedexpansion

REM Ativar UTF-8 para suportar caracteres especiais nos logs
chcp 65001 > nul 2>&1

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
if "!M2_LOOP_SECONDS!"=="" set "M2_LOOP_SECONDS=300"

echo.
echo ========================================
echo  Crypto Futures Agent
echo  Modo: !M2_MODE!
echo  Simbolos: !M2_SYMBOLS!
echo  Loop: !M2_LOOP_SECONDS!s
echo ========================================
echo.

set "LOG_FILE=logs/startup_log.txt"
set "CYCLE_LOG=logs\m2_cycle.log"
if not exist "logs" mkdir logs
call :GET_BRT_TIMESTAMP
(
    echo [INFO] Agent startup at !TS_BRT! BRT
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

if "%CHOICE%"=="1" goto M2_LOOP_START
if "%CHOICE%"=="0" goto END

echo [ERRO] Opcao invalida.
goto END

:M2_LOOP_START
REM Montar argumentos de simbolos para live_cycle e daily_pipeline
set "LIVE_SYMBOL_ARGS="
set "PIPELINE_SYMBOL_ARGS="
set "M2_SYMBOLS_LOOP=!M2_SYMBOLS:,= !"
for %%S in (!M2_SYMBOLS_LOOP!) do (
    if not "%%~S"=="" (
        set "LIVE_SYMBOL_ARGS=!LIVE_SYMBOL_ARGS! --live-symbol %%~S"
        set "PIPELINE_SYMBOL_ARGS=!PIPELINE_SYMBOL_ARGS! --symbol %%~S"
    )
)

set PYTHONIOENCODING=utf-8
echo.
call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[INFO] Iniciando ciclo M2 model-driven (modo: !M2_MODE!). Ctrl+C para parar."
call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[INFO] Log: !CYCLE_LOG!"

:M2_LOOP
echo.
call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Pipeline diario (D1)..."
python scripts/model2/daily_pipeline.py --timeframe D1 --continue-on-error !PIPELINE_SYMBOL_ARGS! >> "!CYCLE_LOG!" 2>&1

call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Pipeline diario (H4)..."
python scripts/model2/daily_pipeline.py --timeframe H4 --continue-on-error !PIPELINE_SYMBOL_ARGS! >> "!CYCLE_LOG!" 2>&1

call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Pipeline diario (H1)..."
python scripts/model2/daily_pipeline.py --timeframe H1 --continue-on-error !PIPELINE_SYMBOL_ARGS! >> "!CYCLE_LOG!" 2>&1

call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Pipeline diario (M5)..."
python scripts/model2/daily_pipeline.py --timeframe M5 --continue-on-error !PIPELINE_SYMBOL_ARGS! >> "!CYCLE_LOG!" 2>&1

call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Ciclo live..."
python scripts/model2/live_cycle.py --execution-mode !M2_MODE! !LIVE_SYMBOL_ARGS! >> "!CYCLE_LOG!" 2>&1

call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Persistindo episodios de treino..."
python scripts/model2/persist_training_episodes.py --timeframe H4 !PIPELINE_SYMBOL_ARGS! >> "!CYCLE_LOG!" 2>&1

call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Healthcheck..."
python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime >> "!CYCLE_LOG!" 2>&1

call :GET_BRT_TIMESTAMP
call :LOG_AND_ECHO "[M2] Status por simbolo..."
python scripts/model2/operator_cycle_status.py --runtime-dir results/model2/runtime --max-age-minutes 60 --symbols-csv "!M2_SYMBOLS!" > logs\m2_cycle_status.tmp 2>&1
if exist logs\m2_cycle_status.tmp (
    type logs\m2_cycle_status.tmp
    (type logs\m2_cycle_status.tmp) >> "!CYCLE_LOG!" 2>nul
    del /q logs\m2_cycle_status.tmp >nul 2>&1
) else (
    call :LOG_AND_ECHO "[M2][SYM] WARN: nenhum status gerado pelo operator_cycle_status.py"
)

call :GET_BRT_TIMESTAMP
call :GET_BRT_TIMESTAMP_PLUS_SECONDS !M2_LOOP_SECONDS!
call :LOG_AND_ECHO "[M2] Ciclo concluido. Aguardando !M2_LOOP_SECONDS!s... Proximo ciclo as !TS_BRT_PLUS! BRT."
timeout /t !M2_LOOP_SECONDS! /nobreak >nul 2>&1
goto M2_LOOP

REM ---------------------------------------------------------------------------
REM :LOG_AND_ECHO MSG
REM   Exibe MSG no console e appenda ao CYCLE_LOG de forma atomica.
REM   Evita WinError 32 usando bloco () que garante fechamento do handle
REM   antes de retornar ao chamador.
REM ---------------------------------------------------------------------------
:LOG_AND_ECHO
set "_lmsg=%~1"
echo [!TS_BRT! BRT] !_lmsg!
(echo [!TS_BRT! BRT] !_lmsg!) >> "!CYCLE_LOG!"
exit /b 0

:GET_BRT_TIMESTAMP
set "TS_BRT="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$tz='E. South America Standard Time'; [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date), $tz).ToString('yyyy-MM-dd HH:mm:ss')"`) do set "TS_BRT=%%i"
if "!TS_BRT!"=="" set "TS_BRT=%date% %time%"
exit /b 0

:GET_BRT_TIMESTAMP_PLUS_SECONDS
set "TS_BRT_PLUS="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$tz='E. South America Standard Time'; [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date).AddSeconds(%~1), $tz).ToString('yyyy-MM-dd HH:mm:ss')"`) do set "TS_BRT_PLUS=%%i"
if "!TS_BRT_PLUS!"=="" set "TS_BRT_PLUS=!TS_BRT!"
exit /b 0

:END
echo.
echo [FIM] Pressione qualquer tecla para fechar...
pause >nul
exit /b 0
