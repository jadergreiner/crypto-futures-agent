"""Configuracao e avaliacao de cobertura minima para modulos criticos M2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

COBERTURA_MINIMA_LINHA_PCT = 80.0
COBERTURA_MINIMA_BRANCH_PCT = 70.0


@dataclass(frozen=True)
class EspecificacaoCoberturaCritica:
    """Define o escopo e os thresholds de cobertura por modulo critico."""

    nome: str
    caminho_fonte: str
    alvos_teste: tuple[str, ...]
    minimo_linha_pct: float = COBERTURA_MINIMA_LINHA_PCT
    minimo_branch_pct: float = COBERTURA_MINIMA_BRANCH_PCT


@dataclass(frozen=True)
class MetricasCoberturaArquivo:
    """Metricas normalizadas de cobertura para um unico arquivo fonte."""

    percentual_linha: float
    percentual_branch: float
    total_linhas: int
    linhas_cobertas: int
    total_branches: int
    branches_cobertas: int


@dataclass(frozen=True)
class ResultadoCoberturaCritica:
    """Resultado final do gate por modulo critico."""

    nome: str
    caminho_fonte: str
    percentual_linha: float
    percentual_branch: float
    minimo_linha_pct: float
    minimo_branch_pct: float
    aprovado: bool


def construir_especificacoes_cobertura_critica() -> tuple[EspecificacaoCoberturaCritica, ...]:
    """Retorna o catalogo canonico de cobertura minima por modulo critico."""

    return (
        EspecificacaoCoberturaCritica(
            nome="scanner",
            caminho_fonte="core/model2/scanner.py",
            alvos_teste=(
                "tests/test_model2_scanner_detector.py",
                "tests/test_model2_m2_025_11_data_freshness.py",
                "tests/test_model2_m2_028_9_coverage_targets.py",
                "tests/test_model2_tracker.py",
                "tests/test_model2_bridge_flow.py",
                "tests/test_model2_export_signals_flow.py",
                "tests/test_model2_resolution_flow.py",
            ),
        ),
        EspecificacaoCoberturaCritica(
            nome="validator",
            caminho_fonte="core/model2/validator.py",
            alvos_teste=(
                "tests/test_model2_validator.py",
                "tests/test_model2_validation_flow.py",
                "tests/test_model2_m2_028_9_coverage_targets.py",
            ),
        ),
        EspecificacaoCoberturaCritica(
            nome="signal_bridge",
            caminho_fonte="core/model2/signal_bridge.py",
            alvos_teste=(
                "tests/test_model2_signal_bridge.py",
                "tests/test_model2_bridge_flow.py",
                "tests/test_model2_m2_024_3_integration.py",
            ),
        ),
        EspecificacaoCoberturaCritica(
            nome="order_layer",
            caminho_fonte="core/model2/order_layer.py",
            alvos_teste=(
                "tests/test_model2_order_layer.py",
                "tests/test_model2_order_layer_flow.py",
                "tests/test_model2_order_layer_short_only.py",
                "tests/test_model2_m2_024_1_decision_contract.py",
                "tests/test_model2_m2_024_3_idempotence_gate.py",
                "tests/test_model2_m2_024_3_integration.py",
                "tests/test_model2_m2_024_5_stage_timeout.py",
                "tests/test_model2_m2_028_4_drawdown_gate.py",
                "tests/test_model2_m2_028_5_correlation_gate.py",
            ),
        ),
        EspecificacaoCoberturaCritica(
            nome="live_execution",
            caminho_fonte="core/model2/live_execution.py",
            alvos_teste=(
                "tests/test_model2_live_gate_short_only.py",
                "tests/test_model2_m2_023_1_error_contract.py",
                "tests/test_model2_m2_024_1_decision_contract.py",
                "tests/test_model2_m2_024_2_reason_code_catalog.py",
                "tests/test_model2_m2_024_2_catalog_unification.py",
                "tests/test_model2_m2_024_10_error_contract.py",
                "tests/test_model2_m2_028_9_coverage_targets.py",
            ),
        ),
        EspecificacaoCoberturaCritica(
            nome="cycle_watchdog",
            caminho_fonte="core/model2/cycle_watchdog.py",
            alvos_teste=(
                "tests/test_model2_m2_027_resilience_failsafe.py",
            ),
        ),
    )


def _calcular_percentual(cobertos: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round((float(cobertos) / float(total)) * 100.0, 2)


def extrair_metricas_cobertura_arquivo(
    coverage_json: Mapping[str, Any],
    caminho_fonte: str,
) -> MetricasCoberturaArquivo:
    """Extrai percentuais de linha e branch de um arquivo no JSON do coverage."""

    arquivos = coverage_json.get("files")
    if not isinstance(arquivos, Mapping):
        raise ValueError("coverage_json_sem_files")

    caminho_normalizado = caminho_fonte.replace("\\", "/")
    arquivo = None
    for chave, valor in arquivos.items():
        if str(chave).replace("\\", "/") == caminho_normalizado:
            arquivo = valor
            break
    if not isinstance(arquivo, Mapping):
        raise ValueError(f"coverage_arquivo_ausente:{caminho_fonte}")

    summary = arquivo.get("summary")
    if not isinstance(summary, Mapping):
        raise ValueError(f"coverage_summary_ausente:{caminho_fonte}")

    total_linhas = int(summary.get("num_statements", 0))
    linhas_cobertas = int(summary.get("covered_lines", 0))
    total_branches = int(summary.get("num_branches", 0))
    branches_cobertas = int(summary.get("covered_branches", 0))

    return MetricasCoberturaArquivo(
        percentual_linha=_calcular_percentual(linhas_cobertas, total_linhas),
        percentual_branch=_calcular_percentual(branches_cobertas, total_branches),
        total_linhas=total_linhas,
        linhas_cobertas=linhas_cobertas,
        total_branches=total_branches,
        branches_cobertas=branches_cobertas,
    )


def avaliar_cobertura_critica(
    metricas_por_modulo: Mapping[str, MetricasCoberturaArquivo],
    especificacoes: Sequence[EspecificacaoCoberturaCritica],
) -> tuple[ResultadoCoberturaCritica, ...]:
    """Aplica o gate de cobertura minima por modulo critico."""

    resultados: list[ResultadoCoberturaCritica] = []
    for especificacao in especificacoes:
        metricas = metricas_por_modulo[especificacao.nome]
        aprovado = (
            metricas.percentual_linha >= especificacao.minimo_linha_pct
            and metricas.percentual_branch >= especificacao.minimo_branch_pct
        )
        resultados.append(
            ResultadoCoberturaCritica(
                nome=especificacao.nome,
                caminho_fonte=especificacao.caminho_fonte,
                percentual_linha=metricas.percentual_linha,
                percentual_branch=metricas.percentual_branch,
                minimo_linha_pct=especificacao.minimo_linha_pct,
                minimo_branch_pct=especificacao.minimo_branch_pct,
                aprovado=aprovado,
            )
        )
    return tuple(resultados)