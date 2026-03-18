"""
Testes de integracao para FLUXUSDT — Infraestrutura cross-chain e computacao descentralizada.

Valida:
- Configuracao do simbolo em config/symbols.py
- Playbook FLUX: confluencia, risco, ciclo e decisao de operar
- Integracao com a lista de simbolos autorizados
"""

import pytest
from config.symbols import SYMBOLS, ALL_SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS
from playbooks import FLUXPlaybook


# ============================================================================
# Configuracao do simbolo
# ============================================================================

def test_fluxusdt_presente_em_symbols() -> None:
    """FLUXUSDT deve estar definido em SYMBOLS."""
    assert "FLUXUSDT" in SYMBOLS, "FLUXUSDT nao encontrado em config/symbols.py"


def test_fluxusdt_campos_obrigatorios() -> None:
    """FLUXUSDT deve ter todos os campos obrigatorios."""
    config = SYMBOLS["FLUXUSDT"]
    for campo in ("papel", "ciclo_proprio", "correlacao_btc",
                  "beta_estimado", "classificacao", "caracteristicas"):
        assert campo in config, f"Campo obrigatorio ausente: {campo}"


def test_fluxusdt_em_all_symbols() -> None:
    """FLUXUSDT deve aparecer em ALL_SYMBOLS."""
    assert "FLUXUSDT" in ALL_SYMBOLS


def test_fluxusdt_em_authorized_symbols() -> None:
    """FLUXUSDT deve estar na whitelist de execucao automatica."""
    assert "FLUXUSDT" in AUTHORIZED_SYMBOLS


def test_fluxusdt_beta() -> None:
    """Beta deve ser adequado para mid-cap com alta sensibilidade."""
    beta = SYMBOLS["FLUXUSDT"]["beta_estimado"]
    assert 2.0 <= beta <= 4.0, f"Beta {beta} fora da faixa esperada para mid-cap high-beta"


def test_fluxusdt_classificacao() -> None:
    """Classificacao deve refletir perfil cross-chain."""
    assert SYMBOLS["FLUXUSDT"]["classificacao"] == "mid_cap_cross_chain"


def test_fluxusdt_caracteristica_cross_chain() -> None:
    """Caracteristica 'cross_chain' deve estar presente."""
    assert "cross_chain" in SYMBOLS["FLUXUSDT"]["caracteristicas"]


def test_fluxusdt_caracteristica_high_beta() -> None:
    """Caracteristica 'high_beta' deve indicar sensibilidade de mercado."""
    assert "high_beta" in SYMBOLS["FLUXUSDT"]["caracteristicas"]


# ============================================================================
# Instanciacao do playbook
# ============================================================================

def test_flux_playbook_instancia() -> None:
    """FLUXPlaybook deve ser instanciavel sem erros."""
    pb = FLUXPlaybook()
    assert pb.symbol == "FLUXUSDT"


def test_flux_playbook_beta() -> None:
    """Playbook deve carregar beta correto de SYMBOLS."""
    pb = FLUXPlaybook()
    assert pb.beta == SYMBOLS["FLUXUSDT"]["beta_estimado"]


def test_flux_playbook_classificacao() -> None:
    """Playbook deve carregar classificacao correta."""
    pb = FLUXPlaybook()
    assert pb.classificacao == SYMBOLS["FLUXUSDT"]["classificacao"]


def test_flux_playbook_info() -> None:
    """get_info() deve retornar dicionario com campos esperados."""
    pb = FLUXPlaybook()
    info = pb.get_info()
    for campo in ("symbol", "papel", "ciclo", "correlacao_btc", "beta", "classificacao"):
        assert campo in info


# ============================================================================
# Ajustes de confluencia
# ============================================================================

def test_confluencia_regime_risk_on() -> None:
    """Regime RISK_ON deve adicionar bonus de confluencia."""
    pb = FLUXPlaybook()
    ajustes = pb.get_confluence_adjustments({"market_regime": "RISK_ON"})
    assert "regime_risk_on" in ajustes
    assert ajustes["regime_risk_on"] > 0


def test_confluencia_regime_risk_off() -> None:
    """Regime RISK_OFF nao deve gerar bonus de regime."""
    pb = FLUXPlaybook()
    ajustes = pb.get_confluence_adjustments({"market_regime": "RISK_OFF"})
    assert "regime_risk_on" not in ajustes


def test_confluencia_alinhamento_btc() -> None:
    """Alinhamento BTC + D1 na mesma direcao deve gerar bonus."""
    pb = FLUXPlaybook()
    ctx = {"btc_bias": "LONG", "d1_bias": "LONG", "market_regime": "RISK_ON"}
    ajustes = pb.get_confluence_adjustments(ctx)
    assert "alinhamento_btc" in ajustes
    assert ajustes["alinhamento_btc"] > 0


def test_confluencia_sem_alinhamento_btc() -> None:
    """BTC e D1 em direcoes opostas nao geram bonus de alinhamento."""
    pb = FLUXPlaybook()
    ctx = {"btc_bias": "SHORT", "d1_bias": "LONG"}
    ajustes = pb.get_confluence_adjustments(ctx)
    assert "alinhamento_btc" not in ajustes


def test_confluencia_estrutura_d1_bullish() -> None:
    """Estrutura D1 bullish deve adicionar bonus."""
    pb = FLUXPlaybook()
    ajustes = pb.get_confluence_adjustments({"smc_d1_structure": "bullish"})
    assert "estrutura_d1_clara" in ajustes
    assert ajustes["estrutura_d1_clara"] > 0


def test_confluencia_estrutura_d1_neutro() -> None:
    """Estrutura D1 em range nao deve gerar bonus."""
    pb = FLUXPlaybook()
    ajustes = pb.get_confluence_adjustments({"smc_d1_structure": "range"})
    assert "estrutura_d1_clara" not in ajustes


def test_confluencia_defi_narrativa_ativa() -> None:
    """Fear & Greed entre 55-80 deve ativar bonus de narrativa DeFi."""
    pb = FLUXPlaybook()
    ajustes = pb.get_confluence_adjustments({"fear_greed_value": 65})
    assert "defi_narrativa_ativa" in ajustes
    assert ajustes["defi_narrativa_ativa"] > 0


def test_confluencia_extrema_ganancia_penalidade() -> None:
    """Fear & Greed acima de 85 deve gerar penalidade."""
    pb = FLUXPlaybook()
    ajustes = pb.get_confluence_adjustments({"fear_greed_value": 90})
    assert "extrema_ganancia" in ajustes
    assert ajustes["extrema_ganancia"] < 0


def test_confluencia_retorna_dict() -> None:
    """get_confluence_adjustments deve sempre retornar dicionario."""
    pb = FLUXPlaybook()
    resultado = pb.get_confluence_adjustments({})
    assert isinstance(resultado, dict)


# ============================================================================
# Ajustes de risco
# ============================================================================

def test_risco_position_size_multiplier_conservador() -> None:
    """Posicao conservadora para beta 2.9."""
    pb = FLUXPlaybook()
    ajustes = pb.get_risk_adjustments({})
    mult = ajustes["position_size_multiplier"]
    assert mult <= 0.55, f"Multiplicador {mult} nao e conservador o suficiente para beta 2.9"


def test_risco_stop_multiplier_calibrado() -> None:
    """Stop calibrado para estrutura SMC mais clara que memecoins."""
    pb = FLUXPlaybook()
    ajustes = pb.get_risk_adjustments({})
    assert ajustes["stop_multiplier"] >= 1.4


def test_risco_alta_volatilidade_reduz_posicao() -> None:
    """ATR% acima de 6% deve reduzir posicao para exatamente 35%."""
    pb = FLUXPlaybook()
    ajustes = pb.get_risk_adjustments({"atr_pct": 7.5})
    assert ajustes["position_size_multiplier"] == 0.35


def test_risco_baixa_volatilidade_aumenta_posicao() -> None:
    """ATR% abaixo de 2% deve aumentar posicao para exatamente 55%."""
    pb = FLUXPlaybook()
    ajustes = pb.get_risk_adjustments({"atr_pct": 1.5})
    assert ajustes["position_size_multiplier"] == 0.55


def test_risco_retorna_campos_obrigatorios() -> None:
    """get_risk_adjustments deve sempre retornar campos obrigatorios."""
    pb = FLUXPlaybook()
    ajustes = pb.get_risk_adjustments({})
    assert "position_size_multiplier" in ajustes
    assert "stop_multiplier" in ajustes


# ============================================================================
# Fase do ciclo
# ============================================================================

def test_ciclo_bull_run_impulso_defi() -> None:
    """Bull run com D1 long → fase de impulso DeFi."""
    pb = FLUXPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "BULL_RUN", "d1_bias": "LONG"})
    assert fase == "FLUX_IMPULSO_DEFI"


def test_ciclo_bull_run_distribuicao() -> None:
    """Bull run com D1 nao long → fase de distribuicao."""
    pb = FLUXPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "BULL_RUN", "d1_bias": "NEUTRO"})
    assert fase == "FLUX_DISTRIBUICAO"


def test_ciclo_bear_market_queda() -> None:
    """Bear market com D1 short → fase de queda."""
    pb = FLUXPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "BEAR_MARKET", "d1_bias": "SHORT"})
    assert fase == "FLUX_QUEDA"


def test_ciclo_acumulacao_long() -> None:
    """Fora de bull/bear e D1 long → acumulacao."""
    pb = FLUXPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "ACCUMULATION", "d1_bias": "LONG"})
    assert fase == "FLUX_ACUMULACAO"


def test_ciclo_lateralizacao() -> None:
    """Sem tendencia clara → lateralizacao."""
    pb = FLUXPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "ACCUMULATION", "d1_bias": "NEUTRO"})
    assert fase == "FLUX_LATERALIZACAO"


def test_ciclo_retorna_string_nao_vazia() -> None:
    """get_cycle_phase deve sempre retornar string nao vazia."""
    pb = FLUXPlaybook()
    fase = pb.get_cycle_phase({})
    assert isinstance(fase, str) and len(fase) > 0


# ============================================================================
# Decisao de operar (should_trade)
# ============================================================================

def test_should_trade_condicoes_ideais() -> None:
    """Deve operar em RISK_ON com D1 direcional."""
    pb = FLUXPlaybook()
    assert pb.should_trade("RISK_ON", "LONG") is True
    assert pb.should_trade("RISK_ON", "SHORT") is True


def test_should_trade_bias_neutro_bloqueia() -> None:
    """Bias D1 neutro deve bloquear operacao (sem tendencia para swing)."""
    pb = FLUXPlaybook()
    assert pb.should_trade("RISK_ON", "NEUTRO") is False


def test_should_trade_regime_risk_off_bloqueia() -> None:
    """Regime RISK_OFF deve bloquear operacao de mid-cap."""
    pb = FLUXPlaybook()
    assert pb.should_trade("RISK_OFF", "LONG") is False
    assert pb.should_trade("RISK_OFF", "SHORT") is False


def test_should_trade_regime_neutro_bloqueia() -> None:
    """Regime neutro deve bloquear operacao."""
    pb = FLUXPlaybook()
    assert pb.should_trade("NEUTRO", "LONG") is False


def test_should_trade_conflito_btc_bloqueia() -> None:
    """Conflito entre BTC e D1 deve bloquear por precaucao."""
    pb = FLUXPlaybook()
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="SHORT") is False


def test_should_trade_btc_alinhado_permite() -> None:
    """BTC alinhado com D1 deve permitir operacao."""
    pb = FLUXPlaybook()
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="LONG") is True


def test_should_trade_btc_neutro_nao_bloqueia() -> None:
    """BTC neutro nao deve bloquear (apenas conflito direto bloqueia)."""
    pb = FLUXPlaybook()
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="NEUTRO") is True


# ============================================================================
# Integracao completa
# ============================================================================

def test_pipeline_completo_condicoes_favoraveis() -> None:
    """Simula pipeline completo em condicoes favoraveis de swing trade."""
    pb = FLUXPlaybook()

    contexto = {
        "market_regime": "RISK_ON",
        "btc_bias": "LONG",
        "d1_bias": "LONG",
        "smc_d1_structure": "bullish",
        "fear_greed_value": 65,
        "atr_pct": 3.5,
    }

    # Deve operar
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="LONG") is True

    # Confluencia positiva
    confluencia = pb.get_confluence_adjustments(contexto)
    total = sum(confluencia.values())
    assert total > 0, "Confluencia total deve ser positiva em condicoes ideais"

    # Risco conservador
    risco = pb.get_risk_adjustments(contexto)
    assert risco["position_size_multiplier"] <= 0.55
    assert risco["stop_multiplier"] >= 1.4

    # Ciclo identificado
    dados = {"btc_cycle_phase": "BULL_RUN", "d1_bias": "LONG"}
    fase = pb.get_cycle_phase(dados)
    assert len(fase) > 0


def test_pipeline_completo_condicoes_desfavoraveis() -> None:
    """Simula pipeline completo em condicoes desfavoraveis — deve bloquear."""
    pb = FLUXPlaybook()

    # Nao deve operar em RISK_OFF
    assert pb.should_trade("RISK_OFF", "LONG") is False

    # Nao deve operar com bias neutro
    assert pb.should_trade("RISK_ON", "NEUTRO") is False

    # Confluencia negativa em extrema ganancia + risk_off
    contexto = {"fear_greed_value": 92, "market_regime": "RISK_OFF"}
    confluencia = pb.get_confluence_adjustments(contexto)
    penalidades = [v for v in confluencia.values() if v < 0]
    assert len(penalidades) > 0, "Deve haver penalidades em condicoes desfavoraveis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
