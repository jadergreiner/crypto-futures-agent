@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

cls
echo ================================================================================
echo PHASE 2 - INICIAR OPERACAO COM RISCO ALTO
echo ================================================================================
echo.
echo Arquivos de autorização necessários:
if exist "PHASE2_AUTORIZADO_RISCO_ALTO_*.json" (
    echo ✅ Autorização registrada
) else (
    echo ⚠️  Execute primeiro: python phase2_registrar_autorizacao.py
    echo.
    pause
    exit /b 1
)
echo.
echo ⚠️  AVISO CRITICO:
echo   - Drawdown: -46.61%%
echo   - Posições: 20 abertas
echo   - Circuit Breaker: DISPARADO
echo.

REM Verificar se venv existe
if not exist "venv\Scripts\activate.bat" (
    echo ❌ ERRO: venv não encontrado
    echo Crie com: python -m venv venv
    pause
    exit /b 1
)

REM Ativar venv
call venv\Scripts\activate.bat

REM Confirmação dupla do operador
echo.
echo ================================================================================
echo CONFIRMAÇÃO DUPLA DO OPERADOR
echo ================================================================================
echo.
set /p confirm1="[1/2] Os orders são REAIS e serão EXECUTADOS? Digite 'SIM': "
if /i not "!confirm1!"=="SIM" (
    echo ❌ Operação CANCELADA
    pause
    exit /b 1
)

echo.
set /p confirm2="[2/2] Você é o operador AUTORIZADO? Digite 'INICIO': "
if /i not "!confirm2!"=="INICIO" (
    echo ❌ Operação CANCELADA
    pause
    exit /b 1
)

REM Executar Phase 2
echo.
echo ================================================================================
echo INICIANDO PHASE 2 - MODO LIVE COM RISCO ALTO
echo ================================================================================
echo.
echo ✅ Confirmações positivas recebidas
echo ⏳ Conectando à Binance Futures...
echo.

python main.py --mode live --integrated --training-interval 7200

if %errorlevel% equ 0 (
    echo.
    echo ✅ Phase 2 concluída com sucesso
) else (
    echo.
    echo ❌ Erro durante Phase 2 (código: !errorlevel!)
)

pause
