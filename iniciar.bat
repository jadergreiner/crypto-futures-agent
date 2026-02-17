@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicialização
REM ==============================================================================
REM Este script inicia o agente de trading de futuros de criptomoedas.
REM Garante que o ambiente está configurado e oferece opções de execução.
REM ==============================================================================

setlocal enabledelayedexpansion

echo.
echo ==============================================================================
echo                   CRYPTO FUTURES AGENT - INICIAR
echo ==============================================================================
echo.

REM Verificar se o ambiente virtual existe
if not exist "venv" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo.
    echo Por favor, execute o setup.bat primeiro para configurar o ambiente:
    echo   setup.bat
    echo.
    pause
    exit /b 1
)

REM Ativar ambiente virtual
echo [1/3] Ativando ambiente virtual...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar ambiente virtual!
    pause
    exit /b 1
)
echo [OK] Ambiente virtual ativado
echo.

REM Verificar se o arquivo .env existe
if not exist ".env" (
    echo [AVISO] Arquivo .env nao encontrado!
    echo.
    echo Por favor, configure seu arquivo .env com as credenciais da Binance:
    echo   1. Copie .env.example para .env
    echo   2. Edite .env e adicione suas API keys
    echo.
    set /p CONTINUE="Deseja continuar mesmo assim? (s/n): "
    if /i not "!CONTINUE!"=="s" (
        echo.
        echo Operacao cancelada.
        pause
        exit /b 1
    )
    echo.
)

REM Verificar se o banco de dados existe
echo [2/3] Verificando banco de dados...
if not exist "db\crypto_agent.db" (
    echo [AVISO] Banco de dados nao encontrado!
    echo.
    echo O banco de dados precisa ser inicializado antes de executar o agente.
    echo.
    set /p RUN_SETUP="Deseja executar o setup inicial agora? (s/n): "
    if /i "!RUN_SETUP!"=="s" (
        echo.
        echo Executando setup inicial...
        echo Isso pode levar varios minutos...
        echo.
        python main.py --setup
        if !errorlevel! neq 0 (
            echo.
            echo [ERRO] Setup falhou! Verifique os logs para mais detalhes.
            pause
            exit /b 1
        )
        echo.
        echo [OK] Setup concluido com sucesso!
        echo.
    ) else (
        echo.
        echo [AVISO] Continuando sem banco de dados inicializado.
        echo Algumas funcionalidades podem nao funcionar corretamente.
        echo.
    )
) else (
    echo [OK] Banco de dados encontrado
)
echo.

REM Menu de opcoes
echo [3/3] Escolha o modo de execucao:
echo.
echo ==============================================================================
echo                            OPCOES DE EXECUCAO
echo ==============================================================================
echo.
echo   1. Modo Paper Trading (Simulacao - RECOMENDADO)
echo   2. Modo Live Trading (Capital Real - CUIDADO!)
echo   3. Monitorar Posicoes Abertas
echo   4. Executar Backtest
echo   5. Treinar Modelo RL
echo   6. Executar Setup Inicial
echo   7. Sair
echo.
echo ==============================================================================
echo.

set /p OPCAO="Digite o numero da opcao desejada: "

echo.
echo ==============================================================================

if "%OPCAO%"=="1" goto :opcao1
if "%OPCAO%"=="2" goto :opcao2
if "%OPCAO%"=="3" goto :opcao3
if "%OPCAO%"=="4" goto :opcao4
if "%OPCAO%"=="5" goto :opcao5
if "%OPCAO%"=="6" goto :opcao6
if "%OPCAO%"=="7" goto :opcao7

echo.
echo [ERRO] Opcao invalida!
echo Por favor, escolha um numero entre 1 e 7.
echo.
goto :final

:opcao1
echo INICIANDO AGENTE EM MODO PAPER TRADING
echo ==============================================================================
echo.
echo O agente sera iniciado em modo de simulacao.
echo Nenhuma ordem real sera enviada para a Binance.
echo.
echo Pressione Ctrl+C para interromper a execucao.
echo.
python main.py --mode paper
goto :final

:opcao2
echo INICIANDO AGENTE EM MODO LIVE TRADING
echo ==============================================================================
echo.
echo [^!^!^! ATENCAO ^!^!^!]
echo Voce escolheu o modo LIVE com capital REAL!
echo.
set /p CONFIRMACAO="Tem certeza que deseja continuar? Digite 'SIM' para confirmar: "
if /i "!CONFIRMACAO!"=="SIM" (
    echo.
    echo Iniciando em modo LIVE...
    echo Ordens REAIS serao enviadas para a Binance!
    echo.
    echo Pressione Ctrl+C para interromper a execucao.
    echo.
    python main.py --mode live
) else (
    echo.
    echo Operacao cancelada por seguranca.
    echo.
)
goto :final

:opcao3
echo MONITORAR POSICOES ABERTAS
echo ==============================================================================
echo.
echo Digite o simbolo para monitorar (ex: C98USDT) ou deixe em branco para monitorar todas:
set /p SIMBOLO="Simbolo: "
echo.
echo Digite o intervalo em segundos (padrao: 300 = 5 minutos):
set /p INTERVALO="Intervalo: "

if "!INTERVALO!"=="" set INTERVALO=300

echo.
echo Iniciando monitor de posicoes...
echo Intervalo: !INTERVALO! segundos
if not "!SIMBOLO!"=="" echo Simbolo: !SIMBOLO!
echo.
echo Pressione Ctrl+C para interromper.
echo.

if "!SIMBOLO!"=="" (
    python main.py --monitor --monitor-interval !INTERVALO!
) else (
    python main.py --monitor --monitor-symbol !SIMBOLO! --monitor-interval !INTERVALO!
)
goto :final

:opcao4
echo EXECUTAR BACKTEST
echo ==============================================================================
echo.
echo Digite a data inicial (formato: YYYY-MM-DD):
set /p DATA_INICIO="Data inicial: "
echo.
echo Digite a data final (formato: YYYY-MM-DD):
set /p DATA_FIM="Data final: "

if "!DATA_INICIO!"=="" (
    echo.
    echo [ERRO] Data inicial e obrigatoria!
    pause
    exit /b 1
)

if "!DATA_FIM!"=="" (
    echo.
    echo [ERRO] Data final e obrigatoria!
    pause
    exit /b 1
)

echo.
echo Executando backtest de !DATA_INICIO! ate !DATA_FIM!...
echo.
python main.py --backtest --start-date !DATA_INICIO! --end-date !DATA_FIM!
goto :final

:opcao5
echo TREINAR MODELO RL
echo ==============================================================================
echo.
echo O treinamento do modelo pode levar varias horas.
echo.
set /p CONFIRMAR="Deseja continuar? (s/n): "
if /i "!CONFIRMAR!"=="s" (
    echo.
    echo Iniciando treinamento do modelo RL...
    echo.
    python main.py --train
) else (
    echo.
    echo Treinamento cancelado.
    echo.
)
goto :final

:opcao6
echo EXECUTAR SETUP INICIAL
echo ==============================================================================
echo.
echo O setup inicial ira:
echo   - Inicializar o banco de dados
echo   - Coletar dados historicos (365 dias D1, 180 dias H4, 90 dias H1)
echo   - Calcular indicadores tecnicos
echo.
echo Isso pode levar varios minutos.
echo.
set /p CONFIRMAR="Deseja continuar? (s/n): "
if /i "!CONFIRMAR!"=="s" (
    echo.
    echo Executando setup inicial...
    echo.
    python main.py --setup
    if !errorlevel! equ 0 (
        echo.
        echo [OK] Setup concluido com sucesso!
    ) else (
        echo.
        echo [ERRO] Setup falhou! Verifique os logs.
    )
) else (
    echo.
    echo Setup cancelado.
)
goto :final

:opcao7
echo.
echo Saindo...
exit /b 0

:final

echo.
echo ==============================================================================
echo.
echo Pressione qualquer tecla para voltar ao menu ou fechar a janela...
pause >nul

REM Voltar ao menu
goto :eof
