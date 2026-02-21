# 📚 REFERÊNCIA TÉCNICA - DECISOR DE MODOS

> ⚠️ **OPERADOR:** Se você quer começar, abra [COMECE_AQUI.md](COMECE_AQUI.md) (2 minutos)
>
> Este documento é para **DESENVOLVEDOR** - Todas as opções de configuração possíveis.

## Árvore de Decisão Interativa

```
┌──────────────────────────────────────────────────────────────────┐
│           QUAL COMANDO DEVO EXECUTAR?                            │
└──────────────────────────────────────────────────────────────────┘

🤔 Pergunta 1: É sua PRIMEIRA VEZ operado o agente?
│
├─ SIM → Continue para Pergunta 2
└─ NÃO → Vá para Pergunta 3

🤔 Pergunta 2: Quer testar SEM risco antes de usar capital real?
│
├─ SIM → EXECUTE: python main.py --mode paper --integrated --integrated-interval 300
│        (Simula trades, não gasta capital real)
│
└─ NÃO → Continue para Pergunta 3

🤔 Pergunta 3: Há 20 posições já abertas na Binance?
│
├─ SIM → Continue para Pergunta 4
└─ NÃO → Comece com BÁSICO (abaixo)

🤔 Pergunta 4: Quer que o sistema TAMBÉM treine o modelo enquanto traduz?
│
├─ NÃO (apenas traduzir) → EXECUTE: python main.py --mode live --integrated --integrated-interval 300
│                          (Rápido, sem processamento de treino)
│
└─ SIM (traduzir + aprender) → Continue para Pergunta 5

🤔 Pergunta 5: Há quanto tempo está operando?
│
├─ Menos de 4 horas → EXECUTE: python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
│                     (Treina a cada 4 horas - conservador)
│
├─ 1-7 dias → EXECUTE: python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
│              (Padrão recomendado)
│
└─ Mais de 1 semana (Win rate >55%) → Continue para Pergunta 6

🤔 Pergunta 6: Quer mais agressividade de aprendizagem?
│
├─ NÃO, manter conservador → EXECUTE: python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
│
└─ SIM, aumentar aprendizado → EXECUTE: python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 7200
                 (Treina a cada 2 horas - mais dinâmico)
```

---

## Tabela Comparativa Rápida

| Necessidade | Comando | Duração | Risco | Ideal Para |
|-------------|---------|---------|-------|-----------|
| **Apenas testa** | `--mode paper --integrated` | ∞ | 🟢 ZERO | Dias 1-2 |
| **Começar operação** | `--mode live --integrated --integrated-interval 300` | ∞ | 🟡 MÉDIO | Dias 1-4 |
| **Produção estável** | `--mode live --integrated ... --concurrent-training --training-interval 14400` | ∞ | 🟡 MÉDIO-ALTO | Dia 2+ |
| **Produção agressiva** | `--mode live --integrated ... --concurrent-training --training-interval 7200` | ∞ | 🔴 ALTO | Semana 2+ |
| **Monitor posições** | `--mode live --monitor --monitor-interval 5` | ∞ | 🟢 ZERO | Verificação |
| **Treinar modelo** | `--train` | ~2h | 🟢 ZERO | Manual |
| **Testar pipeline** | `--dry-run` | ~10min | 🟢 ZERO | Diagnóstico |
| **Backtest histórico** | `--backtest --start-date ... --end-date ...` | ~30min | 🟢 ZERO | Validação |

---

## Tabela de Progresso Semanal Recomendado

```
SEMANA 1: "CONSOLIDAÇÃO"
═══════════════════════════════════════════════════════════════════

DIA 1️⃣ - VALIDAÇÃO
├─ Modo: LIVE sem treinamento
├─ Comando: python main.py --mode live --integrated --integrated-interval 300
├─ Duração: 4-8 horas
├─ Objetivo: Validar que sistema não quebra, gerencia posições
└─ Checkpoints:
    ✓ Nenhum erro de risco
    ✓ Sistema detecta 20 posições
    ✓ Logs limpos

DIA 2️⃣-3️⃣ - OBSERVAÇÃO
├─ Modo: LIVE com treinamento (padrão)
├─ Comando: python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
├─ Duração: 48+ horas
├─ Objetivo: Rodar 2 ciclos completos de treinamento
└─ Checkpoints:
    ✓ Pelo menos 1-2 trades abertos
    ✓ Win rate ≥45%
    ✓ Drawdown <5%

DIA 4️⃣-7️⃣ - OPERAÇÃO NORMAL
├─ Modo: LIVE com treinamento
├─ Comando: (mesmo de dias 2-3)
├─ Duração: 4+ dias
├─ Objetivo: Acumular dados, treinar várias vezes
└─ Checkpoints:
    ✓ Win rate ≥50%
    ✓ Pelo menos 5+ trades
    ✓ Capital crescendo

═══════════════════════════════════════════════════════════════════

SEMANA 2+: "OTIMIZAÇÃO"
═══════════════════════════════════════════════════════════════════

SE Win rate >55% E Sharpe >0,5:
├─ Aumentar frequência de treino
├─ Novo comando: --training-interval 7200 (ao invés de 14400)
├─ Aumentar capital: max_margin_per_position_usd = $15 (ao invés de $8,48)
└─ Monitorar: Drawdown não ultrapasse 5% com novo capital

SE Win rate <50%:
├─ Manter conservador
├─ Manter comando atual
├─ Rodar 7 dias mais antes de avaliar
└─ Se ainda <50% → Retreinar modelo com --train

```

---

## Fluxograma de Erro / Troubleshooting

```
┌────────────────────────────────────────────────┐
│    SISTEMA RODA MAS NÃO ABRE TRADES            │
└────────────────────────────────────────────────┘

CAUSA #1: Confiança mínima não atingida (normal)
├─ Sintoma: Ciclos passam mas nenhuma sinal
├─ Verificar: "Confluence: 3/14" (precisa de 7/14+)
├─ Ação: Aguardar - regime é NEUTRO, é normal
└─ Paciência: Confluence aparece em 1-3 ciclos

CAUSA #2: Whitelist vazia (sem símbolos autorizados)
├─ Sintoma: "Escopo de execução: 0 símbolos"
├─ Verificar: config/execution_config.py
├─ Ação: Adicionar símbolos à whitelist:
│         "whitelist": ["BTCUSDT", "ETHUSDT"]
└─ Reiniciar: Ctrl+C e python main.py ...

CAUSA #3: Capital insuficiente
├─ Sintoma: "Margem insuficiente para posição"
├─ Verificar: max_margin_per_position_usd = $8,48
├─ Ação: Aumentar valor ou capital na Binance
└─ Reiniciar após mudança

CAUSA #4: Modelo não treinado
├─ Sintoma: "Model not found" nos logs
├─ Verificar: ls models/crypto_agent_ppo_final.zip
├─ Ação: python main.py --train
└─ Aguardar ~2 horas de treinamento

CAUSA #5: API key inválida
├─ Sintoma: "Authentication failed"
├─ Verificar: .env com BINANCE_API_KEY correto
├─ Ação: Regenerar API key na Binance
└─ Reiniciar sistema

═════════════════════════════════════════════════════

┌────────────────────────────────────────────────┐
│   DRAWDOWN ACIMA DE 5% (ALERTA CRÍTICO)        │
└────────────────────────────────────────────────┘

AÇÃO IMEDIATA:
├─ 1. Verificar logs para erro específico
├─ 2. Pausar novo trading (Ctrl+C)
├─ 3. Monitorar posições abertas
├─ 4. SEM liquidação imediata (protegidas)
└─ 5. Investigar raiz do problema

POSSÍVEIS CAUSAS:
├─ Mercado virou agressivamente (flash crash)
├─ Modelo virou agressivo demais
├─ Thresholds de confluência muito baixos
├─ Evento macroeconômico não previsto
└─ Bug no cálculo de risco

RECUPERAÇÃO:
├─ A. Esperar 24h antes de reiniciar
├─ B. Rodar novo treinamento: python main.py --train
├─ C. Aumentar thresholds de confiança
├─ D. Reduzir max_margin_per_position_usd
└─ E. Reiniciar conservador (--integrated-interval 600)

═════════════════════════════════════════════════════

┌────────────────────────────────────────────────┐
│    TREINO CONCORRENTE NÃO EXECUTA              │
└────────────────────────────────────────────────┘

SINTOMA 1: Logs dizem "Concurrent training disabled"
├─ Verificar: Passou o argumento --concurrent-training?
├─ Ação: Adicione --concurrent-training ao comando
└─ Comando correto: python main.py --mode live --integrated --concurrent-training --training-interval 14400

SINTOMA 2: Treino começa mas paralisa
├─ Verificar: Disco livre =? df
├─ Ação: Liberar espaço em disco (precisa ~500MB)
└─ Solução: Delete logs antigos, video, etc

SINTOMA 3: Erro de memória durante treino
├─ Verificar: RAM disponível
├─ Ação: Fechar navegador, Discord, etc
└─ Configuração: Aumentar --training-interval (menos frequente)

═════════════════════════════════════════════════════
```

---

## Tabela: "O Que Cada Parâmetro Faz?"

| Parâmetro | Valor | Efeito | Quando Usar |
|-----------|-------|--------|-------------|
| `--mode` | `live` | **Capital REAL** em operação | PRODUÇÃO |
| `--mode` | `paper` | Simula trades, sem gastar | TESTE/VALIDAÇÃO |
| `--integrated` | (flag) | Monitora posições em paralelo | SEMPRE (com vivo) |
| `--integrated-interval` | `300` | Decisão a cada 5 minutos | Padrão, seguro |
| `--integrated-interval` | `180` | Decisão a cada 3 minutos | Capital >$1k |
| `--integrated-interval` | `600` | Decisão a cada 10 minutos | Mercado lento |
| `--concurrent-training` | (flag) | Treina modelo em background | Depois de validar |
| `--training-interval` | `14400` | Treina a cada 4 horas | Padrão recomendado |
| `--training-interval` | `7200` | Treina a cada 2 horas | Após 1 semana sucesso |
| `--training-interval` | `28800` | Treina a cada 8 horas | Bem-conservador |
| `--monitor` | (flag) | Apenas VER posições | Diagnóstico |
| `--monitor-interval` | `5` | Atualiza a cada 5 seg | Monitor rápido |
| `--setup` | (flag) | Coleta dados históricos | Primeira vez EVER |
| `--train` | (flag) | Treina modelo manualmente | Antes de LIVE |
| `--dry-run` | (flag) | Testa sem Binance | Diagnóstico |
| `--backtest` | (flag) + dates | Simula trading histórico | Validação |

---

## Exemplo: Aumentar Agrovisividade Gradualmente

### Semana 1 - Começar Conservador
```powershell
# Dia 1-2: Sem treinamento (foco em validação)
python main.py --mode live --integrated --integrated-interval 300

# Dia 3-7: Com treinamento padrão (4h)
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

### Semana 2 - Se Win Rate >55%
```powershell
# Aumentar frequência de treino para 2h
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 7200
```

### Semana 3+ - Se Sharpe >0,5
```powershell
# Aumentar velocidade de decisão para 3 min
python main.py --mode live --integrated --integrated-interval 180 --concurrent-training --training-interval 7200
```

---

## Checklist: Antes de Colocar Capital Maior

- [ ] Operou por 7 dias mínimo
- [ ] Win rate ≥50%
- [ ] Sharpe ratio ≥0,3
- [ ] Max drawdown nunca >5% em nenhum dia
- [ ] Sistema foi interrompido 0x por erro
- [ ] Logs não mostram warnings críticos
- [ ] Nenhuma posição perdeu >50% em 1 trade
- [ ] Monitoramento foi consistente
- [ ] Risk management nunca foi violado

**SE TOS ✅ TODOS:** Pode aumentar capital até 2x

---

## Command Quick Deploy (Copy-Paste)

### Para Notebook / Persistência

Se quiser que sistema continue mesmo após desconectar SSH/RDP:

**Windows (via Task Scheduler):**
```powershell
# Admin PowerShell:
$action = New-ScheduledTaskAction -Execute "C:\repo\crypto-futures-agent\venv\Scripts\python.exe" -Argument 'main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400' -WorkingDirectory "C:\repo\crypto-futures-agent"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "CryptoFuturesAgent" -RunLevel Highest
```

Isso executa comando automaticamente na inicialização Windows!

---

🎯 **TEM DÚVIDA? Volte para a seção correspondente do GUIA COMPLETO!**

