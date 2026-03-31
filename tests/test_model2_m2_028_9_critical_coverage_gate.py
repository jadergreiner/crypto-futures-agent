"""Testes do gate de cobertura minima por modulo critico (M2-028.9)."""

from __future__ import annotations

from core.model2.critical_module_coverage import (
    MetricasCoberturaArquivo,
    avaliar_cobertura_critica,
    construir_especificacoes_cobertura_critica,
    extrair_metricas_cobertura_arquivo,
)


def test_construir_especificacoes_cobertura_critica_lista_modulos_esperados() -> None:
    especificacoes = construir_especificacoes_cobertura_critica()

    nomes = {especificacao.nome for especificacao in especificacoes}

    assert nomes == {
        "scanner",
        "validator",
        "signal_bridge",
        "order_layer",
        "live_execution",
        "cycle_watchdog",
    }


def test_extrair_metricas_cobertura_arquivo_calcula_percentuais_linha_e_branch() -> None:
    coverage_json = {
        "files": {
            "core/model2/validator.py": {
                "summary": {
                    "num_statements": 20,
                    "covered_lines": 18,
                    "num_branches": 10,
                    "covered_branches": 7,
                }
            }
        }
    }

    metricas = extrair_metricas_cobertura_arquivo(
        coverage_json,
        "core/model2/validator.py",
    )

    assert metricas.percentual_linha == 90.0
    assert metricas.percentual_branch == 70.0
    assert metricas.total_linhas == 20
    assert metricas.total_branches == 10


def test_avaliar_cobertura_critica_reprova_modulo_abaixo_do_threshold() -> None:
    especificacoes = tuple(
        item
        for item in construir_especificacoes_cobertura_critica()
        if item.nome in {"scanner", "validator"}
    )
    metricas_por_modulo = {
        "scanner": MetricasCoberturaArquivo(
            percentual_linha=81.0,
            percentual_branch=71.0,
            total_linhas=100,
            linhas_cobertas=81,
            total_branches=10,
            branches_cobertas=7,
        ),
        "validator": MetricasCoberturaArquivo(
            percentual_linha=79.9,
            percentual_branch=70.0,
            total_linhas=100,
            linhas_cobertas=79,
            total_branches=10,
            branches_cobertas=7,
        ),
    }

    resultados = avaliar_cobertura_critica(metricas_por_modulo, especificacoes)

    assert resultados[0].aprovado is True
    assert resultados[1].aprovado is False
    assert resultados[1].nome == "validator"