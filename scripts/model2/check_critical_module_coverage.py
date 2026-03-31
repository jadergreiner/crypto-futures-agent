"""Executa o gate de cobertura minima para modulos criticos do pipeline M2."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.model2.critical_module_coverage import (
    ResultadoCoberturaCritica,
    avaliar_cobertura_critica,
    construir_especificacoes_cobertura_critica,
    extrair_metricas_cobertura_arquivo,
)

HTMLCOV_DIR = ROOT_DIR / "htmlcov"
TMP_DIR = HTMLCOV_DIR / ".tmp_coverage"
RCFILE_PATH = ROOT_DIR / ".coveragerc"


def _run_command(command: list[str], env: dict[str, str]) -> None:
    subprocess.run(command, cwd=ROOT_DIR, check=True, env=env)


def _module_env(data_file: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["COVERAGE_FILE"] = str(data_file)
    return env


def _print_summary(resultados: tuple[ResultadoCoberturaCritica, ...]) -> None:
    print("Gate de cobertura critica M2")
    for resultado in resultados:
        status = "OK" if resultado.aprovado else "FAIL"
        print(
            f"- {resultado.nome}: {status} | "
            f"linha={resultado.percentual_linha:.2f}% "
            f"(min {resultado.minimo_linha_pct:.2f}%) | "
            f"branch={resultado.percentual_branch:.2f}% "
            f"(min {resultado.minimo_branch_pct:.2f}%)"
        )


def main() -> int:
    especificacoes = construir_especificacoes_cobertura_critica()

    if HTMLCOV_DIR.exists():
        shutil.rmtree(HTMLCOV_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    metricas_por_modulo = {}
    arquivos_cobertura: list[Path] = []

    for especificacao in especificacoes:
        data_file = TMP_DIR / f".coverage.{especificacao.nome}"
        arquivos_cobertura.append(data_file)
        env = _module_env(data_file)

        _run_command(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--rcfile",
                str(RCFILE_PATH),
                "--branch",
                "--source=core/model2",
                "-m",
                "pytest",
                "-q",
                *especificacao.alvos_teste,
            ],
            env,
        )

        json_path = TMP_DIR / f"coverage-{especificacao.nome}.json"
        _run_command(
            [
                sys.executable,
                "-m",
                "coverage",
                "json",
                "--rcfile",
                str(RCFILE_PATH),
                "-o",
                str(json_path),
            ],
            env,
        )

        with json_path.open("r", encoding="utf-8") as handle:
            coverage_json = json.load(handle)

        metricas_por_modulo[especificacao.nome] = extrair_metricas_cobertura_arquivo(
            coverage_json,
            especificacao.caminho_fonte,
        )

    combined_env = os.environ.copy()
    combined_env["COVERAGE_FILE"] = str(TMP_DIR / ".coverage")
    _run_command(
        [
            sys.executable,
            "-m",
            "coverage",
            "combine",
            *[str(caminho) for caminho in arquivos_cobertura],
        ],
        combined_env,
    )
    _run_command(
        [
            sys.executable,
            "-m",
            "coverage",
            "html",
            "--rcfile",
            str(RCFILE_PATH),
            "-d",
            str(HTMLCOV_DIR),
        ],
        combined_env,
    )
    _run_command(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "--rcfile",
            str(RCFILE_PATH),
            "-o",
            str(HTMLCOV_DIR / "coverage-critical.json"),
        ],
        combined_env,
    )

    resultados = avaliar_cobertura_critica(metricas_por_modulo, especificacoes)
    _print_summary(resultados)
    return 0 if all(resultado.aprovado for resultado in resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())