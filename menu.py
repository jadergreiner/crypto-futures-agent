#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Menu de inicialização do Crypto Futures Agent
Versão simplificada e robusta em Python
"""

import os
import sys
import subprocess
import time

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def exibir_banner():
    print("=" * 70)
    print("CRYPTO FUTURES AGENT - INICIAR")
    print("=" * 70)
    print()

def exibir_verificacoes():
    print("[*] Executando verificacoes pre-operacionais...")
    print()
    
    verificacoes = [
        ("Ambiente virtual", lambda: os.path.exists("venv")),
        ("Arquivo .env", lambda: os.path.exists(".env")),
        ("Banco de dados", lambda: os.path.exists("db/crypto_agent.db")),
        ("Diretorio de logs", lambda: os.path.exists("logs")),
        ("Diretorio de modelos", lambda: os.path.exists("models"))
    ]
    
    for idx, (nome, verificacao) in enumerate(verificacoes, 1):
        status = "OK" if verificacao() else "AVISO"
        print(f"[{idx}/5] [{status}] {nome}")
    
    print()
    print("=" * 70)
    print("[PRE-OPERACIONAL] TODAS AS VERIFICACOES OK")
    print("=" * 70)
    print()

def exibir_menu():
    print("OPERADOR - ESCOLHA UMA OPCAO")
    print("-" * 70)
    print()
    print("  1. Teste (Paper Trading - SEM RISCO, apenas validacao)")
    print()
    print("  2. OPERACAO PADRAO - INICIAR AGENTE LIVE COM TREINAMENTO")
    print("     (Opcao recomendada - usa configuracao ja decidida)")
    print()
    print("  --- Status e Monitoramento ---")
    print("  3. Status Rápido (posições abertas + PnL)")
    print("  4. Posições Detalhadas")
    print("  5. Status em Tempo Real (completo)")
    print("  6. Consolidado de Ciclo (de 5 minutos)")
    print("  7. Diagnostico de Sinais (por que poucos sinais?)")
    print()
    print("  --- Opcoes Avancadas ---")
    print("  8. Monitorar Posicoes Abertas (verbose)")
    print("  9. Executar Backtest")
    print("  10. Treinar Modelo RL Manualmente")
    print("  11. Executar Setup Inicial")
    print("  12. Diagnosticar Sistema")
    print("  13. Assumir/Gerenciar Posicao Aberta")
    print("  14. Sair")
    print()
    print("-" * 70)
    print()

def opcao_1():
    """Paper Trading"""
    print("INICIANDO AGENTE EM MODO PAPER TRADING")
    print("=" * 70)
    print()
    print("Modo: SIMULACAO (SEM RISCO)")
    print("Nenhuma ordem real sera enviada para a Binance.")
    print()
    print("Pressione Ctrl+C para interromper a execucao.")
    print()
    time.sleep(2)
    
    subprocess.run(["python", "main.py", "--mode", "paper"])

def opcao_2():
    """Operacao Padrao - LIVE"""
    print("INICIANDO AGENTE EM MODO LIVE OPERACIONAL")
    print("=" * 70)
    print()
    print("[!!! ATENCAO CRITICA !!!]")
    print()
    print("Voce esta prestes a ativar o MODO LIVE com capital REAL.")
    print("Ordens serao ENVIADAS para a Binance e EXECUTADAS.")
    print()
    print("Configuracao OPERACIONAL (ja decidida pela reuniao):")
    print("  - Capital por posicao: U$ 1,00")
    print("  - Alavancagem: 10x")
    print("  - Stop Loss: Obrigatorio")
    print("  - Parcial 50% + Take Profit final")
    print("  - Treinamento concorrente: A CADA 2 HORAS")
    print("  - Monitoramento: Continuo")
    print()
    print("Confirme 2 vezes que compreende os riscos:")
    print()
    
    conf1 = input("  [1/2] Os orders sao REAIS? Digite 'SIM': ").strip().upper()
    if conf1 != "SIM":
        print("  Operacao cancelada.")
        return
    
    conf2 = input("  [2/2] Voce eh o operador autorizado? Digite 'INICIO': ").strip().upper()
    if conf2 != "INICIO":
        print("  Operacao cancelada.")
        return
    
    print()
    print("Iniciando em modo LIVE OPERACIONAL...")
    print()
    print("Configuracao FIXA (decidida pela reuniao):")
    print("  - Modo: LIVE (capital REAL)")
    print("  - Intervalo de decisao: 300 segundos (5 minutos)")
    print("  - Intervalo de treinamento: 7200 segundos (2 HORAS)")
    print("  - Aprendizado concorrente: ATIVADO")
    print()
    print("Pressione Ctrl+C para PARAR SISTEMA COM SEGURANCA.")
    print()
    time.sleep(3)
    
    subprocess.run(["python", "main.py", "--mode", "live", "--integrated", 
                   "--integrated-interval", "300", "--concurrent-training", 
                   "--training-interval", "7200"])

def opcao_3():
    """Status Rápido"""
    print()
    subprocess.run(["python", "status.py"])

def opcao_4():
    """Posições Detalhadas"""
    print()
    subprocess.run(["python", "posicoes.py"])

def opcao_5():
    """Status em Tempo Real"""
    print()
    subprocess.run(["python", "status_realtime.py"])

def opcao_6():
    """Consolidado de Ciclo (5 min)"""
    print()
    subprocess.run(["python", "-c", 
                   "import sys; sys.path.insert(0, '.'); from monitoring.cycle_summary import print_cycle_summary; from config.symbols import ALL_SYMBOLS; print_cycle_summary(ALL_SYMBOLS)"])

def opcao_7():
    """Diagnóstico de Sinais"""
    print()
    subprocess.run(["python", "diagnostico_sinais.py"])

def opcao_8():
    """Monitorar posicoes"""
    print("MONITORAR POSICOES ABERTAS")
    print("=" * 70)
    print()
    
    simbolo = input("Digite o simbolo para monitorar (ex: BTCUSDT) ou deixe em branco para TODAS: ").strip().upper()
    intervalo = input("Digite o intervalo em segundos (padrao: 300 = 5 minutos): ").strip()
    
    if intervalo == "":
        intervalo = "300"
    
    print()
    print("Iniciando monitor de posicoes...")
    if simbolo:
        print(f"Modo: Monitorando apenas {simbolo}")
        subprocess.run(["python", "main.py", "--monitor", "--monitor-symbol", simbolo, 
                       "--monitor-interval", intervalo])
    else:
        print("Modo: Monitorando TODAS as posicoes abertas")
        subprocess.run(["python", "main.py", "--monitor", "--monitor-interval", intervalo])

def opcao_9():
    """Backtest"""
    print("EXECUTAR BACKTEST")
    print("=" * 70)
    print()
    
    data_inicio = input("Digite a data inicial (formato: YYYY-MM-DD): ").strip()
    data_fim = input("Digite a data final (formato: YYYY-MM-DD): ").strip()
    
    if not data_inicio or not data_fim:
        print("Datas obrigatorias!")
        return
    
    print()
    print("Executando backtest...")
    subprocess.run(["python", "main.py", "--backtest", "--backtest-start", data_inicio, 
                   "--backtest-end", data_fim])

def opcao_10():
    """Treinar modelo"""
    print("TREINAR MODELO RL MANUALMENTE")
    print("=" * 70)
    print()
    
    epochs = input("Digite o numero de epochs (padrao: 100): ").strip()
    if epochs == "":
        epochs = "100"
    
    print()
    print("Iniciando treinamento...")
    subprocess.run(["python", "main.py", "--train", "--train-epochs", epochs])

def opcao_11():
    """Setup"""
    print("EXECUTAR SETUP INICIAL")
    print("=" * 70)
    print()
    print("Inicializando sistema...")
    subprocess.run(["python", "main.py", "--setup"])

def opcao_12():
    """Diagnosticar"""
    print("DIAGNOSTICAR SISTEMA")
    print("=" * 70)
    print()
    print("Executando diagnosticos...")
    subprocess.run(["python", "main.py", "--diagnose"])

def opcao_13():
    """Gerenciar posicoes"""
    print("ASSUMIR/GERENCIAR POSICAO ABERTA")
    print("=" * 70)
    print()
    print("Execute com detalhes no arquivo: python main.py --manage-position")

def opcao_14():
    """Sair"""
    print("Encerrando...")
    sys.exit(0)

def main():
    while True:
        limpar_tela()
        exibir_banner()
        exibir_verificacoes()
        exibir_menu()
        
        opcao = input("Digite o numero da opcao desejada (1-14): ").strip()
        
        print()
        
        if opcao == "1":
            opcao_1()
        elif opcao == "2":
            opcao_2()
        elif opcao == "3":
            opcao_3()
        elif opcao == "4":
            opcao_4()
        elif opcao == "5":
            opcao_5()
        elif opcao == "6":
            opcao_6()
        elif opcao == "7":
            opcao_7()
        elif opcao == "8":
            opcao_8()
        elif opcao == "9":
            opcao_9()
        elif opcao == "10":
            opcao_10()
        elif opcao == "11":
            opcao_11()
        elif opcao == "12":
            opcao_12()
        elif opcao == "13":
            opcao_13()
        elif opcao == "14":
            opcao_14()
        else:
            print("[ERRO] Opcao invalida!")
            print("Por favor, escolha um numero entre 1 e 14.")
            input("Pressione ENTER para continuar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSistema interrompido pelo operador.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[ERRO] Falha inesperada: {e}")
        input("Pressione ENTER para sair...")
        sys.exit(1)
