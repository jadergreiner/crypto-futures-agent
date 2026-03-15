@echo off
REM ==============================================================================
REM Crypto Futures Agent - Instalador de Serviço Windows (Daemon)
REM ==============================================================================
REM Requerimento: NSSM (Non-Sucking Service Manager) deve estar no PATH do sistema.
REM Baixe em: http://nssm.cc/
REM
REM Uso: Execute como Administrador
REM ==============================================================================

setlocal enabledelayedexpansion

echo.
echo ======================================================
echo    Instalador do Daemon: Crypto Futures Agent (M2) 
echo ======================================================
echo.

openfiles >nul 2>&1
if '%errorlevel%' NEQ '0' (
    echo [ERRO] Voce precisa executar este script como ADMINISTRADOR.
    echo Por favor, clique com o botao direito e selecione "Executar como Administrador".
    pause
    exit /b 1
)

where nssm >nul 2>&1
if '%errorlevel%' NEQ '0' (
    echo [ERRO] O utilitario 'nssm' nao foi encontrado no PATH.
    echo Baixe o utilitario de http://nssm.cc e coloque 'nssm.exe' em uma pasta do sistema ^(ex: C:\Windows^).
    pause
    exit /b 1
)

set SERVICE_NAME=CryptoFuturesAgentM2
set SCRIPT_DIR=%~dp0
set REPO_DIR=%SCRIPT_DIR%..
cd "%REPO_DIR%"
set REPO_ABSOLUTE_DIR=%CD%

echo Configurando servico Windows '%SERVICE_NAME%'...
echo Caminho do Repositorio: %REPO_ABSOLUTE_DIR%

REM Parar e remover servico anterior, se existir
nssm stop "%SERVICE_NAME%" >nul 2>&1
nssm remove "%SERVICE_NAME%" confirm >nul 2>&1

REM Usa o proprio cmd para rodar o arquivo .bat do Loop e atrelar os Logs
nssm install "%SERVICE_NAME%" "%REPO_ABSOLUTE_DIR%\iniciar.bat"

REM Adiciona as diretivas de AppDirectory para encontrar o venv corretamente
nssm set "%SERVICE_NAME%" AppDirectory "%REPO_ABSOLUTE_DIR%"

REM Garantir a reinicializacao se bugar
nssm set "%SERVICE_NAME%" AppRestartDelay 15000 
nssm set "%SERVICE_NAME%" Description "Crypto Futures Agent - Live Daemon (Model 2.0)"

REM Emite stdout/err para os logs nativos
if not exist "%REPO_ABSOLUTE_DIR%\logs" mkdir "%REPO_ABSOLUTE_DIR%\logs"
nssm set "%SERVICE_NAME%" AppStdout "%REPO_ABSOLUTE_DIR%\logs\daemon_live_stdout.log"
nssm set "%SERVICE_NAME%" AppStderr "%REPO_ABSOLUTE_DIR%\logs\daemon_live_stderr.log"
nssm set "%SERVICE_NAME%" AppStdoutCreationDisposition 4
nssm set "%SERVICE_NAME%" AppStderrCreationDisposition 4

REM Envia parametros iniciais invisíveis garantindo Opcao 2 e Modo Live 
REM Echo [INFO] Simulando input do menu 2
nssm set "%SERVICE_NAME%" AppParameters "< deploy\daemon_input.txt"

echo.
echo [INFO] Inicializando...
nssm start "%SERVICE_NAME%"

echo.
echo ======================================================
echo   [SUCESSO] Servico Instalado e Rodando background!
echo   Maneje nativamente com: 
echo     - 'sc stop %SERVICE_NAME%'
echo     - 'sc start %SERVICE_NAME%'
echo   Acompanhe os logs em: logs\daemon_live_stdout.log
echo ======================================================
pause
