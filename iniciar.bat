@echo off
REM ==============================================================================
REM Crypto Futures Agent - Script de Inicialização
REM ==============================================================================
REM Este script inicia o agente de trading de futuros de criptomoedas.
REM Garante que o ambiente está configurado e oferece opções de execução.
REM ==============================================================================

setlocal enabledelayedexpansion

REM Inicializar variáveis de status
set "STARTUP_TIME=%date% %time%"
set "STATUS_OK=OK"
set "STATUS_WARN=AVISO"
set "STATUS_ERROR=ERRO"

echo.
echo ==============================================================================
echo                   CRYPTO FUTURES AGENT - INICIAR
echo ==============================================================================
echo Iniciado: %STARTUP_TIME%
echo.
echo [*] Executando verificacoes pre-operacionais...
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

echo [1/5] ^[VERIFICANDO^] Ambiente virtual...
call venv\Scripts\activate.bat >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar ambiente virtual!
    pause
    exit /b 1
)
echo [1/5] [OK] Ambiente virtual ativado
echo.

REM Verificar se o arquivo .env existe
echo [2/5] ^[VERIFICANDO^] Configuracao (.env)...
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
) else (
    echo [2/5] [OK] Arquivo .env encontrado
)
echo.

REM Verificar se o banco de dados existe
echo [3/5] ^[VERIFICANDO^] Banco de dados...
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
            echo Log: logs/agent.log
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
    echo [3/5] [OK] Banco de dados encontrado
)
echo.

REM Verificar logs
echo [4/5] ^[VERIFICANDO^] Logs...
if exist "logs\agent.log" (
    echo [4/5] [OK] Log de execucao disponivel
) else (
    echo [4/5] [AVISO] Nenhum log anterior encontrado
)
echo.

REM Status final pré-operacional
echo [5/5] ^[VERIFICANDO^] Arquivos criticos...
if exist "models" (
    echo [5/5] [OK] Diretorio de modelos disponivel
) else (
    echo [5/5] [AVISO] Diretorio de modelos nao encontrado (sera criado automaticamente)
)
echo.

REM ==============================================================================
REM VERIFICACAO AUTOMATICA: OPERACAO PARALELA (OPCAO C)
REM Se arquivo de autorizacao existir, ativar Operacao C transparentemente
REM ==============================================================================

if exist "AUTHORIZATION_OPÇÃO_C_20FEV.txt" (
    echo [VERIFICACAO AUTOMATICA] Operacao Paralela C detectada...
    echo.
    
    REM Iniciar orquestrador em background (sem interfere com menu)
    start /b python core/orchestrator_opção_c.py > logs/orchestrator_opção_c_bg.log 2>&1
    
    if !errorlevel! equ 0 (
        echo [OK] Operacao Paralela C iniciada em background
        echo     - LIVE Scheduler: RODANDO (16 pares USDT)
        echo     - v0.3 Tests: EXECUTANDO (thread isolada)
        echo     - Monitor Critico: ATIVO (60s checks, kill switch 2%%)
        echo     - Capital em Risco: $5,000 USD
        echo     - Logs: logs/orchestrator_opção_c.log, logs/critical_monitor.log
        echo.
        echo [!] Tela de menu disponivel abaixo. Siga normalmente.
        echo [!] Operacao C corre silenciosamente em background.
        echo.
    ) else (
        echo [AVISO] Falha ao iniciar Operacao C em background
        echo         Continuando menu normalmente...
        echo.
    )
)

echo.

REM Menu de opcoes
echo ==============================================================================
echo                   [PRE-OPERACIONAL] TODAS AS VERIFICACOES OK
echo ==============================================================================
echo.
echo Escolha o modo de execucao:
echo.
echo   1. Paper Trading (Simulacao - SEM RISCO) - RECOMENDADO
echo   2. Live Integrado (Capital REAL - REQUER CONFIRMACAO)
echo   3. Monitorar Posicoes Abertas
echo   4. Executar Backtest
echo   5. Treinar Modelo RL (Demora horas)
echo   6. Executar Setup Inicial 
echo   7. Diagnosticar Sistema
echo   8. Assumir/Gerenciar Posicao Aberta
echo   9. Sair
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
if "%OPCAO%"=="8" goto :opcao8
if "%OPCAO%"=="9" goto :opcao9

echo.
echo [ERRO] Opcao invalida!
echo Por favor, escolha um numero entre 1 e 9.
echo.
goto :final

:opcao1
echo INICIANDO AGENTE EM MODO PAPER TRADING
echo ==============================================================================
echo.
echo Modo: SIMULACAO (SEM RISCO)
echo Nenhuma ordem real sera enviada para a Binance.
echo.
echo Inicio: %date% %time%
echo Log: logs/agent.log
echo.
echo Pressione Ctrl+C para interromper a execucao.
echo.
python main.py --mode paper
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Execucao interrompida com erro!
    echo Ver logs para detalhes: logs/agent.log
) else (
    echo.
    echo [OK] Execucao concluida normalmente.
)
goto :final

:opcao2
echo INICIANDO AGENTE EM MODO LIVE INTEGRADO
echo ==============================================================================
echo.
echo [^!^!^! ATENCAO CRITICA ^!^!^!]
echo.
echo Voce esta prestes a ativar o MODO LIVE com capital REAL.
echo Ordens serao ENVIADAS para a Binance e EXECUTADAS.
echo.
echo Este modo integra:
echo   - Busca automatica de oportunidades
echo   - Execucao e gestao de posicoes abertas
echo   - Monitoramento contínuo
echo.
echo Confirme 3 vezes que compreende os riscos:
echo.
set /p CONF1="[1/3] Os ordersao REAIS? Digite 'SIM': "
if /i not "!CONF1!"=="SIM" (
    echo Operacao cancelada.
    goto :final
)

set /p CONF2="[2/3] Voce revirou o .env e as chaves? Digite 'SIM': "
if /i not "!CONF2!"=="SIM" (
    echo Operacao cancelada.
    goto :final
)

set /p CONF3="[3/3] Voce eh o operador autorizado? Digite 'INICIO': "
if /i not "!CONF3!"=="INICIO" (
    echo Operacao cancelada.
    goto :final
)

echo.
echo Configuracao adicional:
echo.

REM Inicializar variáveis de treino antes do bloco if (SEM aspas para consistência)
set TRAINING_FLAG=
set TRAINING_INTERVAL_FLAG=

set /p ENABLE_TRAINING="Deseja TREINAR modelos enquanto opera (mais recursos)? (s/n): "

if /i "!ENABLE_TRAINING!"=="s" (
    set TRAINING_FLAG=--concurrent-training
    set /p TRAIN_INTERVAL="Intervalo de treinamento em horas (padrao: 4): "
    if "!TRAIN_INTERVAL!"=="" set TRAIN_INTERVAL=4
    set /a TRAIN_SECONDS=!TRAIN_INTERVAL! * 3600
    set TRAINING_INTERVAL_FLAG=--training-interval !TRAIN_SECONDS!
    echo.
    echo [*] Treino concorrente ATIVADO: a cada !TRAIN_INTERVAL! hora^(s^)
) else (
    set TRAINING_FLAG=
    set TRAINING_INTERVAL_FLAG=
    echo.
    echo [*] Treino concorrente DESATIVADO
)

echo.
echo Iniciando em modo LIVE INTEGRADO...
echo Ordens REAIS serao enviadas para a Binance!
echo.
echo Inicio: %date% %time%
echo Log: logs/agent.log
echo.

REM Debug detalhado: mostrar comando que sera executado
echo === DEBUG: FLAGS DE TREINO ===
echo TRAINING_FLAG=[!TRAINING_FLAG!]
echo TRAINING_INTERVAL_FLAG=[!TRAINING_INTERVAL_FLAG!]
echo ===============================
echo.

if "!TRAINING_FLAG!"=="" (
    echo [DEBUG] Treino concorrente DESATIVADO
    echo [DEBUG] Comando: python main.py --mode live --integrated --integrated-interval 300
) else (
    echo [DEBUG] Treino concorrente ATIVADO
    echo [DEBUG] Intervalo: !TRAINING_INTERVAL_FLAG!
    echo [DEBUG] Comando: python main.py --mode live --integrated --integrated-interval 300 !TRAINING_FLAG! !TRAINING_INTERVAL_FLAG!
)
echo.
echo Pressione Ctrl+C para interromper a execucao.
echo.

REM Executar com flags de treino
python main.py --mode live --integrated --integrated-interval 300 !TRAINING_FLAG! !TRAINING_INTERVAL_FLAG!
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Execucao interrompida com erro!
    echo Ver logs: logs/agent.log
) else (
    echo.
    echo [OK] Execucao encerrada. Revisar relatorio: logs/agent.log
)
goto :final

:opcao3
echo MONITORAR POSICOES ABERTAS
echo ==============================================================================
echo.
echo Digite o simbolo para monitorar (ex: BTCUSDT) ou deixe em branco para TODAS:
set /p SIMBOLO="Simbolo [ENTER para todos]: "
echo.
echo Digite o intervalo em segundos (padrao: 300 = 5 minutos):
set /p INTERVALO="Intervalo [ENTER para padrao]: "

if "!INTERVALO!"=="" set INTERVALO=300

echo.
echo Iniciando monitor de posicoes...
if "!SIMBOLO!"=="" (
    echo Modo: Monitorando TODAS as posicoes abertas
) else (
    echo Modo: Monitorando apenas !SIMBOLO!
)
echo Intervalo: !INTERVALO! segundos
echo Logs: logs/agent.log
echo.
echo Pressione Ctrl+C para interromper.
echo.

if "!SIMBOLO!"=="" (
    python main.py --monitor --monitor-interval !INTERVALO!
) else (
    python main.py --monitor --monitor-symbol !SIMBOLO! --monitor-interval !INTERVALO!
)

if !errorlevel! equ 0 (
    echo [OK] Monitor finalizado
) else (
    echo [AVISO] Monitor interrompido
)
goto :final

:opcao4
echo EXECUTAR BACKTEST
echo ==============================================================================
echo.
echo Backtesting permite analisar a performance do modelo em dados historicos.
echo.
echo Digite a data inicial (formato: YYYY-MM-DD):
set /p DATA_INICIO="Data inicial [ex: 2024-01-01]: "
echo.
echo Digite a data final (formato: YYYY-MM-DD):
set /p DATA_FIM="Data final [ex: 2024-12-31]: "

if "!DATA_INICIO!"=="" (
    echo.
    echo [ERRO] Data inicial eh obrigatoria!
    pause
    exit /b 1
)

if "!DATA_FIM!"=="" (
    echo.
    echo [ERRO] Data final eh obrigatoria!
    pause
    exit /b 1
)

echo.
echo Executando backtest...
echo Periodo: !DATA_INICIO! a !DATA_FIM!
echo Logs: logs/agent.log
echo Relatorios: reports/
echo.
echo Pressione Ctrl+C para interromper.
echo.
python main.py --backtest --start-date !DATA_INICIO! --end-date !DATA_FIM!

if !errorlevel! equ 0 (
    echo.
    echo [OK] Backtest concluido
    echo Relatorio salvo: reports/backtest_report.html
) else (
    echo.
    echo [AVISO] Backtest interrompido
)
goto :final

:opcao5
echo TREINAR MODELO RL
echo ==============================================================================
echo.
echo O treinamento do modelo RL usa curriculum learning com 3 fases:
echo.
echo  Fase 1 - Exploracao:  500k timesteps (~1-2 horas)
echo  Fase 2 - Refinamento: 1M timesteps (~2-4 horas)
echo  Fase 3 - Validacao:   100 episodios (~30 min)
echo.
echo TEMPO TOTAL ESTIMADO: 4-7 horas (depende do hardware)
echo.
echo O treinamento pode ser interrompido com Ctrl+C.
echo Progresso sera salvo em: models/
echo Logs detalhados: logs/agent.log
echo.
set /p CONFIRMAR="Deseja continuar? (s/n): "
if /i "!CONFIRMAR!"=="s" (
    echo.
    echo Iniciando treinamento...
    echo Inicio: %date% %time%
    echo.
    python main.py --train
    if !errorlevel! equ 0 (
        echo.
        echo [OK] Treinamento concluido com sucesso!
        echo Modelo salvo: models/crypto_agent_ppo_final.zip
    ) else (
        echo.
        echo [AVISO] Treinamento interrompido ou com erro.
        echo Ver logs: logs/agent.log
    )
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
echo.
echo  1. Inicializar banco de dados
echo  2. Coletar dados historicos da Binance:
echo     - 365 dias no timeframe D1 (diario)
echo     - 180 dias no timeframe H4 (4-horas)
echo     - 90 dias no timeframe H1 (horario)
echo  3. Calcular indicadores tecnicos
echo  4. Validar pipeline ML
echo.
echo TEMPO ESTIMADO: 15-30 minutos (depende da conexao)
echo Banco de dados sera salvo: db/crypto_agent.db (~500MB)
echo.
set /p CONFIRMAR="Deseja continuar? (s/n): "
if /i "!CONFIRMAR!"=="s" (
    echo.
    echo Executando setup inicial...
    echo Inicio: %date% %time%
    echo.
    python main.py --setup
    if !errorlevel! equ 0 (
        echo.
        echo [OK] Setup concluido com sucesso!
        echo Banco de dados pronto: db/crypto_agent.db
        echo Proximo passo: Executar treinamento (opcao 5) ou paper trading (opcao 1)
    ) else (
        echo.
        echo [ERRO] Setup falhou! 
        echo Ver logs para detalhes: logs/agent.log
    )
) else (
    echo.
    echo Setup cancelado.
    echo.
)
goto :final

:opcao7
echo DIAGNOSTICAR SISTEMA
echo ==============================================================================
echo.
echo Executando self-check do sistema...
echo.
python -c "import sys; print(f'Python: {sys.version}'); import stable_baselines3; print('Stable-Baselines3: OK'); import gymnasium; print('Gymnasium: OK'); import pandas; print('Pandas: OK'); import numpy; print('Numpy: OK')" 2>nul
if %errorlevel% equ 0 (
    echo.
    echo [OK] Todas as dependencias estao OK
) else (
    echo.
    echo [AVISO] Algumas dependencias podem estar com problemas
    echo Execute: python -m pytest tests/ -q (para testes detalhados)
)
echo.
echo Verificando conectividade Binance...
python main.py --test-connection 2>nul
echo.
goto :final

:opcao8
echo ASSUMIR / GERENCIAR POSICAO ABERTA
echo ==============================================================================
echo.
echo Digite o simbolo da posicao já aberta na Binance (ex: BTCUSDT):
set /p ADOPT_SYMBOL="Simbolo: "

if "!ADOPT_SYMBOL!"=="" (
    echo.
    echo [ERRO] Simbolo e obrigatorio para assumir uma posicao.
    goto :final
)

echo.
echo Digite o intervalo em segundos para o monitoramento (padrao: 300):
set /p ADOPT_INTERVAL="Intervalo: "

if "!ADOPT_INTERVAL!"=="" set ADOPT_INTERVAL=300

echo.
echo Assumindo gerenciamento da posicao !ADOPT_SYMBOL!...
echo Intervalo: !ADOPT_INTERVAL! segundos
echo.
echo Pressione Ctrl+C para interromper.
echo.

python main.py --mode live --adopt-position !ADOPT_SYMBOL! --monitor-interval !ADOPT_INTERVAL!
goto :final

:opcao9
echo.
echo Encerrando...
echo [OK] Saindo da aplicacao. Ate logo!
echo.
exit /b 0

:final

echo.
echo ==============================================================================
echo.
echo Deseja retornar ao menu? (Pressione qualquer tecla ou feche esta janela)
pause >nul

REM Voltar ao menu
cls
goto :start
