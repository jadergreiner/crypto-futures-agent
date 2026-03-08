@echo off
REM Script para corrigir encoding de commits usando rebase manual

setlocal enabledelayedexpansion

cd /d c:\repo\crypto-futures-agent

echo.
echo ========================================
echo Correcao de Commit Encoding - Batch
echo =======================================
echo.

REM Criar um arquivo temporário com as novas mensagens
goto :execute

:execute

echo Abra um terminal do Git Bash e execute:
echo.
echo   bash -c "cd /c/repo/crypto-futures-agent"
echo   bash -c "git rebase -i 7849056^"
echo.
echo Depois mude 'pick' para 'edit' para cada commit problemático.
echo.
echo Ou execute o script Python de automation...
echo.

python -c "
import subprocess
import os

os.chdir('c:/repo/crypto-futures-agent')

print('Iniciando rebase interativo...')
print('Quando o editor abrir, você precisa:')
print('1. Mudar pick -> edit para os 11 commits problemáticos')
print('2. Salvar e fechar o editor')
print('3. Para cada commit em edit:')
print('   git commit --amend -m \"nova mensagem\"')
print('   git rebase --continue')
print()

# Tentar iniciar o rebase
result = subprocess.run(['git', 'rebase', '-i', '7849056^'], capture_output=False, text=True)
print(f'Rebase retornou: {result.returncode}')
"

echo.
echo Concluido!
echo.

endlocal
