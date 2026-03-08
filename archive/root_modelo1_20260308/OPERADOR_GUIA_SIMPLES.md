# 🚀 OPERADOR - COMECE AQUI

## Uma Única Instrução

```
Abra: iniciar.bat

Escolha: Opção 2 (LIVE Integrado + Treinamento)

Pronto! Sistema roda sozinho.
```

---

## É Isso!

O sistema já vem configurado com as decisões tomadas:

✅ **$1,00 por posição**
✅ **Alavancagem 10x**
✅ **Stop Loss obrigatório**
✅ **Parcial 50% + TP final**
✅ **Treinamento a cada 2 horas**
✅ **Aprendizado concorrente ativo**

Você não precisa mexer em nada.

---

## 🚨 SITUAÇÕES CRÍTICAS (Leia ANTES de iniciar)

**CRÍTICO:** Leia em situação de crise:
- [EMERGENCY_STOP_PROCEDURE.md](EMERGENCY_STOP_PROCEDURE.md)
  — Como pausar seguramente se algo der errado
- [CIRCUIT_BREAKER_RESPONSE.md](CIRCUIT_BREAKER_RESPONSE.md)
  — O que fazer quando sistema bloquear
- [DASHBOARD_OPERATOR_ALERTS.md](DASHBOARD_OPERATOR_ALERTS.md)
  — Como interpretar alertas do dashboard

---

## Se Algo der Errado

### Sistema não inicia
→ Verificar se arquivo `.env` tem API keys

### Não detecta posições
→ Verificar se API key está com permissão de TRADING no Binance

### Recebe erro
→ Procurar em `logs/agent.log`

### Circuit breaker disparou?
→ Leia: [CIRCUIT_BREAKER_RESPONSE.md](CIRCUIT_BREAKER_RESPONSE.md)

### Preciso parar emergencialmente?
→ Leia: [EMERGENCY_STOP_PROCEDURE.md](EMERGENCY_STOP_PROCEDURE.md)

---

## Ver Status (Enquanto Roda)

Abra outra janela PowerShell:
```powershell
cd C:\repo\crypto-futures-agent
python main.py --mode live --monitor
```

Isso mostra as 20 posições em tempo real.

---

## Parar Sistema

Pressione na janela original:
```
Ctrl+C
```

Pronto. Sistema salva tudo automaticamente.

---

**É isto. Nada de complicado.**

