"""
Testes para o modelo de Swing Trade autônomo do SKRUSDT.

Valida:
- Configuração do símbolo em config/symbols.py
- Playbook SKR: confluência, risco, ciclo e decisão de operar
- Integração com a lista de símbolos autorizados
"""

import pytest
from config.symbols import SYMBOLS, ALL_SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS
from playbooks import SKRPlaybook


# ============================================================================
# Configuração do símbolo
# ============================================================================

def test_skrusdt_presente_em_symbols():
    """SKRUSDT deve estar definido em SYMBOLS."""
    assert "SKRUSDT" in SYMBOLS, "SKRUSDT não encontrado em config/symbols.py"


def test_skrusdt_campos_obrigatorios():
    """SKRUSDT deve ter todos os campos obrigatórios."""
    config = SYMBOLS["SKRUSDT"]
    for campo in ("papel", "ciclo_proprio", "correlacao_btc",
                  "beta_estimado", "classificacao", "caracteristicas"):
        assert campo in config, f"Campo obrigatório ausente: {campo}"


def test_skrusdt_em_all_symbols():
    """SKRUSDT deve aparecer em ALL_SYMBOLS."""
    assert "SKRUSDT" in ALL_SYMBOLS


def test_skrusdt_em_authorized_symbols():
    """SKRUSDT deve estar na whitelist de execução automática."""
    assert "SKRUSDT" in AUTHORIZED_SYMBOLS


def test_skrusdt_beta_swing_trade():
    """Beta deve ser adequado para swing trade (alto, porém controlado)."""
    beta = SYMBOLS["SKRUSDT"]["beta_estimado"]
    assert 2.0 <= beta <= 4.0, f"Beta {beta} fora da faixa esperada para swing trade"


def test_skrusdt_classificacao_swing():
    """Classificação deve refletir perfil de swing trade."""
    classificacao = SYMBOLS["SKRUSDT"]["classificacao"]
    assert "swing" in classificacao.lower() or "low_cap" in classificacao.lower()


def test_skrusdt_caracteristica_swing_trade():
    """Característica 'swing_trade' deve estar presente."""
    assert "swing_trade" in SYMBOLS["SKRUSDT"]["caracteristicas"]


def test_skrusdt_caracteristica_aprendizado_autonomo():
    """Característica 'autonomous_learning' deve indicar operação sem parâmetros fixos."""
    assert "autonomous_learning" in SYMBOLS["SKRUSDT"]["caracteristicas"]


# ============================================================================
# Instanciação do playbook
# ============================================================================

def test_skr_playbook_instancia():
    """SKRPlaybook deve ser instanciável sem erros."""
    pb = SKRPlaybook()
    assert pb.symbol == "SKRUSDT"


def test_skr_playbook_beta():
    """Playbook deve carregar beta correto de SYMBOLS."""
    pb = SKRPlaybook()
    assert pb.beta == SYMBOLS["SKRUSDT"]["beta_estimado"]


def test_skr_playbook_classificacao():
    """Playbook deve carregar classificação correta."""
    pb = SKRPlaybook()
    assert pb.classificacao == SYMBOLS["SKRUSDT"]["classificacao"]


def test_skr_playbook_info():
    """get_info() deve retornar dicionário com campos esperados."""
    pb = SKRPlaybook()
    info = pb.get_info()
    for campo in ("symbol", "papel", "ciclo", "correlacao_btc", "beta", "classificacao"):
        assert campo in info


# ============================================================================
# Ajustes de confluência
# ============================================================================

def test_confluencia_regime_risk_on():
    """Regime RISK_ON deve adicionar bônus de confluência."""
    pb = SKRPlaybook()
    ajustes = pb.get_confluence_adjustments({"market_regime": "RISK_ON"})
    assert "regime_risk_on" in ajustes
    assert ajustes["regime_risk_on"] > 0


def test_confluencia_regime_risk_off():
    """Regime RISK_OFF não deve gerar bônus de regime."""
    pb = SKRPlaybook()
    ajustes = pb.get_confluence_adjustments({"market_regime": "RISK_OFF"})
    assert "regime_risk_on" not in ajustes


def test_confluencia_alinhamento_btc():
    """Alinhamento BTC + D1 na mesma direção deve gerar bônus."""
    pb = SKRPlaybook()
    ctx = {"btc_bias": "LONG", "d1_bias": "LONG", "market_regime": "RISK_ON"}
    ajustes = pb.get_confluence_adjustments(ctx)
    assert "alinhamento_btc" in ajustes
    assert ajustes["alinhamento_btc"] > 0


def test_confluencia_sem_alinhamento_btc():
    """BTC e D1 em direções opostas não geram bônus de alinhamento."""
    pb = SKRPlaybook()
    ctx = {"btc_bias": "SHORT", "d1_bias": "LONG"}
    ajustes = pb.get_confluence_adjustments(ctx)
    assert "alinhamento_btc" not in ajustes


def test_confluencia_estrutura_d1_bullish():
    """Estrutura D1 bullish deve adicionar bônus."""
    pb = SKRPlaybook()
    ajustes = pb.get_confluence_adjustments({"smc_d1_structure": "bullish"})
    assert "estrutura_d1_clara" in ajustes
    assert ajustes["estrutura_d1_clara"] > 0


def test_confluencia_estrutura_d1_neutro():
    """Estrutura D1 em range não deve gerar bônus."""
    pb = SKRPlaybook()
    ajustes = pb.get_confluence_adjustments({"smc_d1_structure": "range"})
    assert "estrutura_d1_clara" not in ajustes


def test_confluencia_volume_alto():
    """Volume 1.5x acima da média deve gerar bônus."""
    pb = SKRPlaybook()
    ajustes = pb.get_confluence_adjustments({"volume_ratio": 2.0})
    assert "volume_confirmacao" in ajustes


def test_confluencia_extrema_ganancia_penalidade():
    """Fear & Greed acima de 85 deve gerar penalidade."""
    pb = SKRPlaybook()
    ajustes = pb.get_confluence_adjustments({"fear_greed_value": 90})
    assert "extrema_ganancia" in ajustes
    assert ajustes["extrema_ganancia"] < 0


def test_confluencia_retorna_dict():
    """get_confluence_adjustments deve sempre retornar dicionário."""
    pb = SKRPlaybook()
    resultado = pb.get_confluence_adjustments({})
    assert isinstance(resultado, dict)


# ============================================================================
# Ajustes de risco
# ============================================================================

def test_risco_position_size_multiplier_conservador():
    """Posição conservadora para beta 2.8."""
    pb = SKRPlaybook()
    ajustes = pb.get_risk_adjustments({})
    mult = ajustes["position_size_multiplier"]
    assert mult <= 0.55, f"Multiplicador {mult} não é conservador o suficiente para beta 2.8"


def test_risco_stop_multiplier_largo():
    """Stop mais largo para absorver volatilidade de swing."""
    pb = SKRPlaybook()
    ajustes = pb.get_risk_adjustments({})
    assert ajustes["stop_multiplier"] >= 1.5


def test_risco_alta_volatilidade_reduz_posicao():
    """ATR% acima de 6% deve reduzir posição para exatamente 35%."""
    pb = SKRPlaybook()
    ajustes = pb.get_risk_adjustments({"atr_pct": 7.5})
    assert ajustes["position_size_multiplier"] == 0.35


def test_risco_baixa_volatilidade_aumenta_posicao():
    """ATR% abaixo de 2% deve aumentar posição para exatamente 55%."""
    pb = SKRPlaybook()
    ajustes = pb.get_risk_adjustments({"atr_pct": 1.5})
    assert ajustes["position_size_multiplier"] == 0.55


def test_risco_retorna_campos_obrigatorios():
    """get_risk_adjustments deve sempre retornar campos obrigatórios."""
    pb = SKRPlaybook()
    ajustes = pb.get_risk_adjustments({})
    assert "position_size_multiplier" in ajustes
    assert "stop_multiplier" in ajustes


# ============================================================================
# Fase do ciclo
# ============================================================================

def test_ciclo_bull_run_alinhado():
    """Bull run com D1 long → fase de impulso."""
    pb = SKRPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "BULL_RUN", "d1_bias": "LONG"})
    assert fase == "SWING_IMPULSO"


def test_ciclo_bull_run_distribuicao():
    """Bull run com D1 não long → fase de distribuição."""
    pb = SKRPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "BULL_RUN", "d1_bias": "NEUTRO"})
    assert fase == "SWING_DISTRIBUICAO"


def test_ciclo_bear_market_queda():
    """Bear market com D1 short → fase de queda."""
    pb = SKRPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "BEAR_MARKET", "d1_bias": "SHORT"})
    assert fase == "SWING_QUEDA"


def test_ciclo_acumulacao_long():
    """Fora de bull/bear e D1 long → acumulação long."""
    pb = SKRPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "ACCUMULATION", "d1_bias": "LONG"})
    assert fase == "SWING_ACUMULACAO_LONG"


def test_ciclo_lateralizacao():
    """Sem tendência clara → lateralização."""
    pb = SKRPlaybook()
    fase = pb.get_cycle_phase({"btc_cycle_phase": "ACCUMULATION", "d1_bias": "NEUTRO"})
    assert fase == "SWING_LATERALIZACAO"


def test_ciclo_retorna_string_nao_vazia():
    """get_cycle_phase deve sempre retornar string não vazia."""
    pb = SKRPlaybook()
    fase = pb.get_cycle_phase({})
    assert isinstance(fase, str) and len(fase) > 0


# ============================================================================
# Decisão de operar (should_trade)
# ============================================================================

def test_should_trade_condicoes_ideais():
    """Deve operar em RISK_ON com D1 direcional."""
    pb = SKRPlaybook()
    assert pb.should_trade("RISK_ON", "LONG") is True
    assert pb.should_trade("RISK_ON", "SHORT") is True


def test_should_trade_bias_neutro_bloqueia():
    """Bias D1 neutro deve bloquear operação (sem tendência para swing)."""
    pb = SKRPlaybook()
    assert pb.should_trade("RISK_ON", "NEUTRO") is False


def test_should_trade_regime_risk_off_bloqueia():
    """Regime RISK_OFF deve bloquear operação de low-cap."""
    pb = SKRPlaybook()
    assert pb.should_trade("RISK_OFF", "LONG") is False
    assert pb.should_trade("RISK_OFF", "SHORT") is False


def test_should_trade_regime_neutro_bloqueia():
    """Regime neutro deve bloquear operação."""
    pb = SKRPlaybook()
    assert pb.should_trade("NEUTRO", "LONG") is False


def test_should_trade_conflito_btc_bloqueia():
    """Conflito entre BTC e D1 deve bloquear por precaução."""
    pb = SKRPlaybook()
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="SHORT") is False


def test_should_trade_btc_alinhado_permite():
    """BTC alinhado com D1 deve permitir operação."""
    pb = SKRPlaybook()
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="LONG") is True


def test_should_trade_btc_neutro_nao_bloqueia():
    """BTC neutro não deve bloquear (apenas conflito direto bloqueia)."""
    pb = SKRPlaybook()
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="NEUTRO") is True


# ============================================================================
# Integração completa
# ============================================================================

def test_pipeline_completo_condicoes_favoraveis():
    """Simula pipeline completo em condições favoráveis de swing trade."""
    pb = SKRPlaybook()

    contexto = {
        "market_regime": "RISK_ON",
        "btc_bias": "LONG",
        "d1_bias": "LONG",
        "smc_d1_structure": "bullish",
        "volume_ratio": 1.8,
        "fear_greed_value": 65,
        "atr_pct": 3.5,
    }

    # Deve operar
    assert pb.should_trade("RISK_ON", "LONG", btc_bias="LONG") is True

    # Confluência positiva
    confluencia = pb.get_confluence_adjustments(contexto)
    total = sum(confluencia.values())
    assert total > 0, "Confluência total deve ser positiva em condições ideais"

    # Risco conservador
    risco = pb.get_risk_adjustments(contexto)
    assert risco["position_size_multiplier"] <= 0.55
    assert risco["stop_multiplier"] >= 1.5

    # Ciclo identificado
    dados = {"btc_cycle_phase": "BULL_RUN", "d1_bias": "LONG"}
    fase = pb.get_cycle_phase(dados)
    assert len(fase) > 0


def test_pipeline_completo_condicoes_desfavoraveis():
    """Simula pipeline completo em condições desfavoráveis — deve bloquear."""
    pb = SKRPlaybook()

    # Não deve operar em RISK_OFF
    assert pb.should_trade("RISK_OFF", "LONG") is False

    # Não deve operar com bias neutro
    assert pb.should_trade("RISK_ON", "NEUTRO") is False

    # Confluência negativa em extrema ganância
    contexto = {"fear_greed_value": 92, "market_regime": "RISK_OFF"}
    confluencia = pb.get_confluence_adjustments(contexto)
    penalidades = [v for v in confluencia.values() if v < 0]
    assert len(penalidades) > 0, "Deve haver penalidades em condições desfavoráveis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
