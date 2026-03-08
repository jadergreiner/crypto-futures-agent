@echo off
REM Teste de escopo de variáveis em batch com delayed expansion

setlocal enabledelayedexpansion

echo.
echo ========== TESTE DE ESCOPO DE VARIÁVEIS ==========
echo.

REM SOLUÇÃO CORRIGIDA: Inicializar ANTES do bloco
echo [TESTE 1] Inicializacao ANTES do bloco (CORRETO)
set "FLAG="
set "VALUE="

echo Executando simulacao de entrada de usuario (S para sim)...
set CHOICE=S

if /i "!CHOICE!"=="s" (
    set FLAG=--flag-ativado
    set VALUE=--valor-123
    echo [DEBUG - dentro do if] FLAG=!FLAG!
    echo [DEBUG - dentro do if] VALUE=!VALUE!
) else (
    set FLAG=
    set VALUE=
)

echo [DEBUG - depois do if] FLAG=!FLAG!
echo [DEBUG - depois do if] VALUE=!VALUE!
echo.

if "!FLAG!"=="" (
    echo [RESULTADO] Flags VAZIAS (problema!)
) else (
    echo [RESULTADO] Flags PREENCHIDAS (correto!)
)

echo.
echo Comando que seria executado:
echo python main.py --mode live !FLAG! !VALUE!
echo.
echo ======= FIM DO TESTE ==========

pause
