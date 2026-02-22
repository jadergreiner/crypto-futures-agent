# 📝 TAREFA-001: TEMPLATES DE IMPLEMENTAÇÃO

**Status:** Templates prontos para copy/paste
**Linguagem:** Python
**Encoding:** UTF-8
**Lint:** 80 caracteres máximo

---

## TEMPLATE 1: MOTOR CORE (DEV)

### Arquivo: `execution/heuristic_signals.py`

```python
"""
Gerador de sinais heurísticos conservadores.

Implementação: TAREFA-001 Phase 2
Responsável: Dev (Engenheiro Software)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class SignalComponent:
    """
    Estrutura componente sinal heurístico.

    Atributos:
        nome: Identificador componente (smc, ema_alignment, rsi,
              adx)
        valor: Valor calculado (normalize 0-1)
        limiar: Limiar validação (quando excedido = válido)
        valido: Booleano resultado comparação
        confianca: Score confiança este componente (0-1)
    """
    nome: str
    valor: float
    limiar: float
    valido: bool
    confianca: float = 0.5

    def serializar(self) -> Dict[str, Any]:
        """Serializar para auditoria JSON."""
        return {
            "nome": self.nome,
            "valor": round(self.valor, 4),
            "limiar": round(self.limiar, 4),
            "valido": self.valido,
            "confianca": round(self.confianca, 2),
        }


@dataclass
class HeuristicSignal:
    """
    Sinal heurístico completo orquestrado.

    Atributos:
        simbolo: Par trading (ETHUSDT, OGNUSDT, etc)
        timestamp: Quando sinal foi gerado (UTC)
        tipo_sinal: BUY | SELL | WAIT
        componentes: Lista SignalComponent validadas
        confianca_total: Score agregado (0-100%)
        score_confluencia: Quantos componentes confluem (0-14)
        regime_mercado: RISK_ON | RISK_OFF | NEUTRAL (D1 bias)
        viés_d1: BULLISH | BEARISH | NEUTRAL (tendência D1)
        avaliacao_risco: CLEARED | RISKY | BLOCKED (RiskGate)
        preco_entrada: Preço recomendado entrada
        stop_loss: Preço stop loss recomendado
        take_profit: Preço take profit recomendado
        razao_risco_retorno: R:R ratio (stop_loss vs take_profit)
        auditoria: Dict rastreamento completo decisão
    """
    simbolo: str
    timestamp: datetime
    tipo_sinal: str  # BUY | SELL | WAIT
    componentes: List[SignalComponent] = field(
        default_factory=list)
    confianca_total: float = 0.0
    score_confluencia: int = 0
    regime_mercado: str = "NEUTRAL"
    viés_d1: str = "NEUTRAL"
    avaliacao_risco: str = "CLEARED"
    preco_entrada: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    razao_risco_retorno: Optional[float] = None
    auditoria: Dict[str, Any] = field(
        default_factory=dict)

    def serializar(self) -> Dict[str, Any]:
        """Serializar para auditoria JSON."""
        return {
            "simbolo": self.simbolo,
            "timestamp":
                self.timestamp.isoformat(),
            "tipo_sinal": self.tipo_sinal,
            "componentes": [
                c.serializar()
                for c in self.componentes
            ],
            "confianca_total":
                round(self.confianca_total, 2),
            "score_confluencia":
                self.score_confluencia,
            "regime_mercado":
                self.regime_mercado,
            "viés_d1": self.viés_d1,
            "avaliacao_risco":
                self.avaliacao_risco,
            "preco_entrada":
                round(self.preco_entrada, 4)
                if self.preco_entrada else None,
            "stop_loss":
                round(self.stop_loss, 4)
                if self.stop_loss else None,
            "take_profit":
                round(self.take_profit, 4)
                if self.take_profit else None,
            "razao_risco_retorno":
                round(self.razao_risco_retorno, 2)
                if self.razao_risco_retorno else None,
            "auditoria": self.auditoria,
        }


class RiskGate:
    """
    Proteção risco inline.

    Avalia drawdown de fechamento + circuit breaker.
    Retorna: CLEARED (< 3%), RISKY (3-5%),
             BLOCKED (> 5%)
    """

    def __init__(self,
                 limiar_risky: float = 0.03,
                 limiar_blocked: float = 0.05):
        """
        Inicializar proteção.

        Args:
            limiar_risky: Drawdown % ativa RISKY
            limiar_blocked: Drawdown % ativa BLOCKED
        """
        self.limiar_risky = limiar_risky
        self.limiar_blocked = limiar_blocked
        self.saldo_anterior = None
        self.pico_sessao = None
        self.circuit_breaker = False

    def avaliar(self,
                saldo_atual: float,
                pico_sessao: float) -> tuple[str, str]:
        """
        Avaliar status risco.

        Args:
            saldo_atual: Saldo conta atual
            pico_sessao: Pico saldo esta sessão

        Returns:
            (status, mensagem)
            status: CLEARED | RISKY | BLOCKED
            mensagem: Descrição texto
        """
        # Circuit breaker precedência
        if self.circuit_breaker:
            return ("BLOCKED",
                    "Circuit breaker ativo")

        # Calcular drawdown
        if pico_sessao <= 0:
            return ("BLOCKED",
                    "Sem pico sessão (precondicao)")

        drawdown = 1 - (saldo_atual / pico_sessao)

        # Classificar
        if drawdown > self.limiar_blocked:
            return ("BLOCKED",
                    f"Drawdown {drawdown:.2%} > "
                    f"{self.limiar_blocked:.2%}")
        elif drawdown > self.limiar_risky:
            return ("RISKY",
                    f"Drawdown {drawdown:.2%} "
                    f"({self.limiar_risky:.2%}-"
                    f"{self.limiar_blocked:.2%})")
        else:
            return ("CLEARED",
                    f"Drawdown {drawdown:.2%} "
                    f"< {self.limiar_risky:.2%}")

    def ativar_circuit_breaker(self) -> None:
        """Ativar circuit breaker (resets @ nova
        sessão)."""
        self.circuit_breaker = True
        logger.warning("Circuit breaker ATIVADO")


class HeuristicSignalGenerator:
    """
    Orquestrador principal geração sinais.

    Fluxo:
      1. Validar entradas (OHLCV + regime +
         indicadores)
      2. Computar componentes (SMC, Technical,
         MultiTimeframe)
      3. Agregar confiança & score confluencia
      4. Avaliar risco (RiskGate)
      5. Construir sinal (BUY | SELL | WAIT)
      6. Log auditoria

    Responsável: Dev (Engenheiro Software)
    """

    def __init__(self,
                 configs: Optional[Dict] = None):
        """
        Inicializar gerador.

        Args:
            configs: Dict configurações
                     (limites, pesos, etc)
        """
        self.configs = configs or {}
        self.risk_gate = RiskGate()
        self.logger = logger

    def gerar_sinal(self,
                    simbolo: str,
                    preco_atual: float,
                    dados_ohlcv: Dict,
                    dados_d1: Dict,
                    dados_h4: Dict,
                    dados_h1: Dict,
                    regime: str,
                    saldo_atual: float,
                    pico_sessao: float,
                    ) -> Optional[HeuristicSignal]:
        """
        Orquestrador principal.

        Fluxo completo geração sinal heurístico.

        Args:
            simbolo: Par trading (ETHUSDT)
            preco_atual: Preço fechamento atual
            dados_ohlcv: OHLCV DataFrame último
            dados_d1: DataFrame diário completo
            dados_h4: DataFrame 4h completo
            dados_h1: DataFrame 1h completo
            regime: RISK_ON | RISK_OFF | NEUTRAL
            saldo_atual: Saldo conta
            pico_sessao: Pico saldo sessão

        Returns:
            HeuristicSignal | None (erro)
        """
        try:
            # Step 1: Validar entradas
            if not self._validar_entrada(
                simbolo, preco_atual, dados_ohlcv
            ):
                self.logger.warning(
                    f"Validação falhou {simbolo}"
                )
                return None

            # Step 2: Computar componentes
            componentes = (
                self._avaliar_componentes(
                    dados_ohlcv,
                    dados_d1,
                    dados_h4,
                    dados_h1,
                    regime
                )
            )

            if not componentes:
                self.logger.debug(
                    f"Sem componentes válidos "
                    f"{simbolo}"
                )
                return None

            # Step 3: Agregar confiança
            confianca_total = (
                self._computar_confianca_agregada(
                    componentes
                )
            )
            score_confluencia = (
                self._computar_score_confluencia(
                    componentes
                )
            )

            # Step 4: Avaliar risco
            status_risco, msg_risco = (
                self.risk_gate.avaliar(
                    saldo_atual,
                    pico_sessao
                )
            )

            # Step 5: Decidir sinal
            tipo_sinal = (
                self._decidir_tipo_sinal(
                    confianca_total,
                    score_confluencia,
                    status_risco,
                    regime
                )
            )

            # Step 6: Construir sinal
            sinal = HeuristicSignal(
                simbolo=simbolo,
                timestamp=datetime.now(
                    timezone.utc
                ),
                tipo_sinal=tipo_sinal,
                componentes=componentes,
                confianca_total=confianca_total,
                score_confluencia=(
                    score_confluencia
                ),
                regime_mercado=regime,
                viés_d1=self._extrair_viés_d1(
                    dados_d1
                ),
                avaliacao_risco=status_risco,
            )

            # Step 7: Log auditoria
            self._logar_auditoria(
                sinal, msg_risco
            )

            return sinal

        except Exception as e:
            self.logger.error(
                f"Erro gerar sinal {simbolo}: "
                f"{str(e)}"
            )
            return None

    def _validar_entrada(self,
                         simbolo: str,
                         preco: float,
                         dados: Dict) -> bool:
        """Validar precondições."""
        # TODO: Implementar validação
        # - Verificar simbolo != None
        # - Verificar preco > 0
        # - Verificar dados não vazio
        # - Verificar OHLCV completo
        return True

    def _avaliar_componentes(
        self,
        dados_ohlcv: Dict,
        dados_d1: Dict,
        dados_h4: Dict,
        dados_h1: Dict,
        regime: str
    ) -> List[SignalComponent]:
        """Computar todos componentes."""
        # TODO: Implementar
        # 1. SMC: detect_order_blocks, FVG, BOS
        # 2. Technical: EMA alignment, RSI, ADX
        # 3. MultiTimeframe: H4 vs H1 alignment
        # 4. Regime check
        # Retornar: List[SignalComponent]
        return []

    def _computar_confianca_agregada(
        self,
        componentes: List[SignalComponent]
    ) -> float:
        """Agregar confiança componentes."""
        # TODO: Implementar fórmula
        # media ponderada confianca
        # pesos: SMC=0.4, Technical=0.35,
        #        MultiTimeframe=0.25
        return 0.0

    def _computar_score_confluencia(
        self,
        componentes: List[SignalComponent]
    ) -> int:
        """Contar quantos componentes
        confluem."""
        # TODO: Implementar
        # count(c.valido for c in componentes)
        # Max: 14 (múltiplos componentes)
        return 0

    def _decidir_tipo_sinal(
        self,
        confianca: float,
        confluencia: int,
        status_risco: str,
        regime: str
    ) -> str:
        """Decisão final sinal."""
        # TODO: Implementar lógica
        # SE status_risco == "BLOCKED" → WAIT
        # SENÃO calcular BUY/SELL/WAIT
        #   baseado confianca + confluencia
        # Retornar: BUY | SELL | WAIT
        return "WAIT"

    def _extrair_viés_d1(
        self,
        dados_d1: Dict
    ) -> str:
        """Extrair viés diário."""
        # TODO: Usar EMA200/price position
        # SE price > EMA200 → BULLISH
        # SENÃO → BEARISH
        return "NEUTRAL"

    def _logar_auditoria(
        self,
        sinal: HeuristicSignal,
        msg_risco: str
    ) -> None:
        """Log auditoria trail."""
        log_entry = {
            "timestamp": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
            "sinal": sinal.serializar(),
            "risk_message": msg_risco,
        }
        self.logger.info(
            json.dumps(log_entry)
        )
```

---

## TEMPLATE 2: INDICADORES (BRAIN)

### Arquivo: `indicators/smc.py`

```python
"""SMC: Detecção Smart Money Concepts.

Enhancements TAREFA-001:
  - detect_order_blocks()
  - detect_fair_value_gaps()
  - detect_break_of_structure()

Responsável: Brain (Engenheiro ML)
"""

def detect_order_blocks(
    dados: Dict,
    periodo: int = 5
) -> List[Dict]:
    """
    Detectar zonas frescas order block.

    Args:
        dados: OHLCV DataFrame
        periodo: Barras lookback

    Returns:
        List[Dict] com zonas frescas
        {"tipo": "BULLISH"|"BEARISH",
         "high_zone": float,
         "low_zone": float}
    """
    # TODO: Implementar
    # 1. Identificar estrutura reversal
    # 2. Localizar order block (zona acúmulo)
    # 3. Retornar zonas frescas (untested)
    return []


def detect_fair_value_gaps(
    dados: Dict
) -> List[Dict]:
    """
    Detectar FVGs abertos (gaps justos).

    Args:
        dados: OHLCV DataFrame

    Returns:
        List[Dict] FVGs
        {"tipo": "BULLISH"|"BEARISH",
         "high_fvg": float,
         "low_fvg": float,
         "barras_abertas": int}
    """
    # TODO: Implementar
    # 1. Detectar gaps nas últimas 3 barras
    # 2. Verificar se ainda abertos
    # 3. Retornar FVGs com info abertura
    return []


def detect_break_of_structure(
    dados: Dict
) -> str:
    """
    Detectar BOS (break of structure).

    Args:
        dados: OHLCV DataFrame última seção

    Returns:
        "BULLISH_BOS" | "BEARISH_BOS" |
        "NO_BOS"
    """
    # TODO: Implementar
    # 1. Comparar swings prev vs atual
    # 2. Validar rompimento nível
    # 3. Retornar tipo BOS
    return "NO_BOS"
```

### Arquivo: `indicators/technical.py`

```python
"""Technical: Indicadores técnicos.

Enhancements TAREFA-001:
  - calculate_ema_alignment()
  - calculate_di_plus()
  - calculate_di_minus()

Responsável: Brain (Engenheiro ML)
"""

def calculate_ema_alignment(
    dados: Dict
) -> float:
    """
    Verificar alinhamento EMA.

    Validar: EMA50 > EMA200 (bullish) ou
             EMA50 < EMA200 (bearish)

    Args:
        dados: OHLCV DataFrame

    Returns:
        +1.0 (bullish) | 0.0 (neutro) |
        -1.0 (bearish)
    """
    # TODO: Implementar
    # 1. Calcular EMA50 e EMA200
    # 2. Comparar posições
    # 3. Retornar alignment
    return 0.0


def calculate_di_plus(dados: Dict) -> Any:
    """
    Calcular DI+ (ADX positivo).

    Parte do ADX system (Wilder's DMI).

    Args:
        dados: OHLCV DataFrame

    Returns:
        pd.Series DI+ (0-100)
    """
    # TODO: Implementar cálculo DI+
    # 1. Calcular +DM (movimento positivo)
    # 2. Calcular TR (true range)
    # 3. Aplicar smoothing EMA
    pass


def calculate_di_minus(dados: Dict) -> Any:
    """
    Calcular DI- (ADX negativo).

    Parte do ADX system (Wilder's DMI).

    Args:
        dados: OHLCV DataFrame

    Returns:
        pd.Series DI- (0-100)
    """
    # TODO: Implementar cálculo DI-
    # 1. Calcular -DM (movimento negativo)
    # 2. Calcular TR (true range)
    # 3. Aplicar smoothing EMA
    pass
```

### Arquivo: `indicators/multi_timeframe.py`

```python
"""Multi-timeframe: Análise múltiplos
timeframes.

Enhancements TAREFA-001:
  - Complete detect_regime()

Responsável: Brain (Engenheiro ML)
"""

def detect_regime(
    d1_data: Dict,
    h4_data: Dict,
    h1_data: Dict
) -> str:
    """
    Detectar regime mercado multi-timeframe.

    Lógica:
      D1 + H4 bullish → RISK_ON
      D1 + H4 bearish → RISK_OFF
      Conflitos/neutro → NEUTRAL

    Args:
        d1_data: DataFrame D1 (diário)
        h4_data: DataFrame H4
        h1_data: DataFrame H1

    Returns:
        "RISK_ON" | "RISK_OFF" | "NEUTRAL"
    """
    # TODO: Implementar
    # 1. Get D1 tendência (EMA200/price)
    # 2. Get H4 tendência
    # 3. Combinar lógica
    # 4. Retornar regime
    return "NEUTRAL"
```

---

## TEMPLATE 3: TESTES QA

### Arquivo: `tests/test_heuristic_signals.py`

```python
"""
Testes unitários heuristic signals.

TAREFA-001 - Suite QA completa

Responsável: Audit (Gerente QA)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import json


class TestRiskGate:
    """Testes proteção risco inline."""

    def test_risk_gate_cleared_status(self):
        """Verificar status CLEARED < 3%."""
        # TODO

    def test_risk_gate_risky_status(self):
        """Verificar status RISKY 3-5%."""
        # TODO

    def test_risk_gate_blocked_status(self):
        """Verificar status BLOCKED > 5%."""
        # TODO

    def test_risk_gate_circuit_breaker(self):
        """Verificar circuit breaker."""
        # TODO


class TestSignalComponent:
    """Testes SignalComponent dataclass."""

    def test_signal_component_criacao(self):
        """Criar component válido."""
        # TODO

    def test_signal_component_serializacao(
        self
    ):
        """Serializar para auditoria JSON."""
        # TODO


class TestHeuristicSignalGenerator:
    """Testes motor geração sinais."""

    def test_gerar_sinal_basico(self):
        """Fluxo básico geração sinal."""
        # TODO

    def test_smc_deteccao_order_block(self):
        """Detector order block SMC."""
        # TODO

    def test_ema_alignment_bullish(self):
        """EMA alignment bullish válido."""
        # TODO

    def test_ema_alignment_bearish(self):
        """EMA alignment bearish válido."""
        # TODO

    def test_rsi_oversold_deteccao(self):
        """RSI oversold (<30) detecção."""
        # TODO

    def test_rsi_overbought_deteccao(self):
        """RSI overbought (>70) detecção."""
        # TODO

    def test_adx_trend_confirmacao(self):
        """ADX trend confirmation (>25)."""
        # TODO

    def test_regime_deteccao_risk_on(self):
        """Regime RISK_ON detectado."""
        # TODO

    def test_regime_deteccao_risk_off(self):
        """Regime RISK_OFF detectado."""
        # TODO


class TestEdgeCases:
    """Testes cenários edge case críticos."""

    def test_edge_case_baixa_liquidez(self):
        """Volume extremamente baixo."""
        # TODO

    def test_edge_case_flash_crash(self):
        """Flash crash -8% bloqueado."""
        # TODO

    def test_edge_case_timeout_rede(self):
        """Network timeout graceful."""
        # TODO

    def test_edge_case_funding_rate_extremo(
        self
    ):
        """Funding rate extremo."""
        # TODO

    def test_edge_case_dataframe_vazio(self):
        """Tratamento DataFrame vazio."""
        # TODO


class TestPerformance:
    """Testes baseline performance."""

    def test_latencia_execucao(self):
        """Executar < 100ms por símbolo."""
        # TODO

    def test_footprint_memoria(self):
        """Usar < 2KB memória por sinal."""
        # TODO

    def test_geracao_sinal_batch(self):
        """Processar 60 pares em < 6s."""
        # TODO


class TestAuditoria:
    """Testes auditoria trail."""

    def test_auditoria_trail_logging(self):
        """Auditoria trail completa logged."""
        # TODO

    def test_auditoria_campos_compliance(
        self
    ):
        """Campos compliance preenchidos."""
        # TODO


# Fixtures úteis

@pytest.fixture
def mock_dados_ohlcv():
    """Mock OHLCV data."""
    return {
        "open": [100.0, 101.0],
        "high": [101.5, 102.0],
        "low": [99.5, 100.5],
        "close": [101.0, 101.5],
        "volume": [1000, 1100],
    }


@pytest.fixture
def generator():
    """Inicializar gerador heurístico."""
    from execution.heuristic_signals import (
        HeuristicSignalGenerator
    )
    return HeuristicSignalGenerator()
```

---

**Nota:** Todos templates devem manter:
- ✅ 100% português (documentação)
- ✅ Type hints obrigatórios
- ✅ Docstrings Google-style
- ✅ Encoding UTF-8
- ✅ Max 80 caracteres por linha
- ✅ Sem números mágicos hardcoded

Última atualização: 22 FEV 2026
