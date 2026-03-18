@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicializacao Unificado
REM 1) Legado  2) Nova versao (pipeline + live em loop continuo)
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

set "LOG_FILE=logs/startup_log.txt"
(
    echo [INFO] Agent startup at %date% %time%
    echo   M2 Mode: !M2_MODE!
    echo   M2 Symbols: !M2_SYMBOLS!
    echo   Loop Seconds: !M2_LOOP_SECONDS!
    echo ----------------------------------------
) >> %LOG_FILE%

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
set PYTHONIOENCODING=utf-8
if not exist "logs" mkdir logs
echo.
echo [INFO] Modo continuo ativado. Use Ctrl+C para interromper.
echo [INFO] Log detalhado em: logs\m2_cycle.log
if "!M2_RUN_ONCE!"=="1" echo [INFO] M2_RUN_ONCE=1: executara apenas um ciclo.

:M2_LOOP
echo.
python scripts/model2/sync_market_context.py --timeframe H4 !PIPELINE_SYMBOL_ARGS! >logs\m2_tmp.json 2>>logs/m2_cycle.log
python -c "import json;d=json.load(open('logs/m2_tmp.json'));print('[sync H4 ] status='+d['status']+' | persisted='+str(d['candles_persisted'])+' | skipped='+str(d['candles_duplicated_skipped']))"

python scripts/model2/sync_market_context.py --timeframe M5 !PIPELINE_SYMBOL_ARGS! >logs\m2_tmp.json 2>>logs/m2_cycle.log
python -c "import json;d=json.load(open('logs/m2_tmp.json'));print('[sync M5 ] status='+d['status']+' | persisted='+str(d['candles_persisted'])+' | skipped='+str(d['candles_duplicated_skipped']))"

python scripts/model2/daily_pipeline.py --timeframe H4 --continue-on-error !PIPELINE_SYMBOL_ARGS! >logs\m2_tmp.json 2>>logs/m2_cycle.log
python -c "import json,re;raw=open('logs/m2_tmp.json',encoding='utf-8').read();m=re.search(r'\{.*\}',raw,re.DOTALL);d=json.loads(m.group()) if m else {};stages=d.get('stages',{});erros=d.get('stage_errors',[]);ok=sum(1 for s in stages.values() if s.get('status')=='ok');print('[pipeline] status='+d.get('status','?')+' | stages_ok='+str(ok)+'/'+str(len(stages))+(' | ERROS='+str(erros) if erros else ''))"

python scripts/model2/live_cycle.py --timeframe H4 --execution-mode !M2_MODE! !LIVE_SYMBOL_ARGS! >logs\m2_tmp.json 2>>logs/m2_cycle.log
python -c "
import json,re
raw=open('logs/m2_tmp.json',encoding='utf-8').read()
m=re.search(r'\{.*\}',raw,re.DOTALL)
d=json.loads(m.group()) if m else {}
dash=d.get('dashboard',{})
exe=d.get('execute',{})
staged=exe.get('staged',[])
ready=exe.get('processed_ready',[])
print('[live    ] status='+d.get('status','?')+' | staged='+str(len(staged))+' | ready='+str(len(ready))+' | blocked='+str(dash.get('blocked_count',0))+' | protected='+str(dash.get('protected_count',0))+' | exited='+str(dash.get('exited_count',0))+' | failed='+str(dash.get('failed_count',0)))
for s in staged:
    sym=s.get('symbol','?'); st=s.get('status','?'); reason=s.get('reason','')
    detail=' ('+reason+')' if reason else ''
    print('           '+sym+' -> '+st+detail)
for r in ready:
    sym=r.get('symbol','?'); st=r.get('status','?')
    print('           '+sym+' -> '+st)
"

python scripts/model2/persist_training_episodes.py --timeframe H4 !PIPELINE_SYMBOL_ARGS! >logs\m2_tmp.json 2>>logs/m2_cycle.log
python -c "import json,re;raw=open('logs/m2_tmp.json',encoding='utf-8').read();m=re.search(r'\{.*\}',raw,re.DOTALL);d=json.loads(m.group()) if m else {};print('[episodio] status='+d.get('status','?')+' | inseridos='+str(d.get('episodes_inserted',d.get('inserted',0))))"

python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime --max-age-hours 2 --max-unprotected-filled 0 --max-stale-entry-sent 0 --max-position-mismatches 0 >logs\m2_tmp.json 2>>logs/m2_cycle.log
python -c "import json;d=json.load(open('logs/m2_tmp.json'));v=d.get('violations',[]);print('[health  ] status='+d['status']+(' | VIOLACOES: '+str(v) if v else ''))"

if "!M2_RUN_ONCE!"=="1" goto END

echo.
echo [INFO] Aguardando !M2_LOOP_SECONDS!s para o proximo ciclo...
timeout /t !M2_LOOP_SECONDS! /nobreak >nul 2>&1
goto M2_LOOP

:END
echo.
echo [FIM] Pressione qualquer tecla para fechar...
pause >nul
exit /b 0
