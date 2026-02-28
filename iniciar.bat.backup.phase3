@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicializacao
REM Versao simplificada e robusta
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

REM Executar menu Python
python menu.py

pause
