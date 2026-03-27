from pathlib import Path
import re


BACKLOG = Path("docs/BACKLOG.md").read_text(encoding="utf-8")
INICIAR = Path("iniciar.bat").read_text(encoding="utf-8")
ARQ = Path("docs/ARQUITETURA_ALVO.md").read_text(encoding="utf-8")
RNG = Path("docs/REGRAS_DE_NEGOCIO.md").read_text(encoding="utf-8")
README = Path("README.md").read_text(encoding="utf-8")


def test_blid089_quando_loop_m2_entao_inclui_pipeline_d1() -> None:
    assert "daily_pipeline.py --timeframe D1" in INICIAR


def test_pkgpo10_quando_priorizacao_entao_top10_registrado() -> None:
    assert "Top 10" in BACKLOG
    top10_items = re.findall(r"(?m)^\d+\)\s+[A-Z0-9\-\.]+", BACKLOG)
    assert len(top10_items) >= 10


def test_m201910_quando_docs_rl_entao_arquitetura_regras_readme_alinhados() -> None:
    assert "entry_rl_filter" in ARQ
    assert "entry_rl_filter" in RNG
    assert "daily_pipeline.py" in README


def test_blid088_quando_entrega_m5_concluida_entao_status_concluido() -> None:
    chunk = BACKLOG.split("### TAREFA BLID-088")[1].split("### TAREFA")[0]
    assert "Status: CONCLUIDO" in chunk


def test_blid075_quando_top10_priorizado_entao_status_em_analise() -> None:
    chunk = BACKLOG.split("### TAREFA BLID-075")[1].split("### TAREFA")[0]
    assert "Status: Em analise" in chunk
