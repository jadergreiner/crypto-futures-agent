@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicializacao
REM Versao 0.3.0 - Data Strategy LIVE (1Y historico para 60 simbolos)
REM ==============================================================================

setlocal enabledelayedexpansion

REM Verificar se venv existe
if not exist "venv" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo.
    echo Execute setup.bat primeiro para configurar o ambiente.
    pause
    exit /b 1
)

REM Ativar ambiente virtual
call venv\Scripts\activate.bat 2>nul

REM ==============================================================================
REM Verificar Data Strategy Cache (Issue #67)
REM ==============================================================================
if exist "data\klines_cache.db" (
    echo [OK] Data Strategy LIVE: Banco de dados 1 ano x 60 simbolos detectado
    set DATA_STRATEGY=active
) else (
    echo [AVISO] Data Strategy NAO INICIALIZADO
    echo.
    echo Para carregar dados: python data/scripts/klines_cache_manager.py --action fetch_full
    echo.
    set DATA_STRATEGY=inactive
)

REM ==============================================================================
REM Verificar se config/symbols_extended.py existe (200 simbolos)
REM ==============================================================================
if exist "config\symbols_extended.py" (
    echo [OK] Modo EXPANDED: 200 simbolos detectados
    set SYMBOLS_MODE=expanded
) else (
    echo [OK] Modo COMPATIBILIDADE: 60 simbolos padrao
    set SYMBOLS_MODE=standard
)

echo.
echo ========================================
echo  Crypto Futures Agent - Menu Principal
echo  Versao: 0.3.0 (Issue #67 - Data Strategy LIVE)
echo  Modo: %SYMBOLS_MODE% (%SYMBOLS_MODE% symbols)
echo  Data Cache: %DATA_STRATEGY%
echo ========================================
echo.

REM Executar menu Python
python menu.py

pause
