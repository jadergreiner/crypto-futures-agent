"""
Suite RED — M2-022.6: Consolidar documentacao de arquitetura live.

Todos os testes desta suite devem FALHAR antes da implementacao.
Apos a implementacao (GREEN), todos devem passar.

Mapeamento requisito -> teste:
  RF-001 -> test_arquitetura_alvo_contem_secao_fluxo_live_ponta_a_ponta
  RF-002 -> test_arquitetura_alvo_documenta_metricas_operacionais
  RF-003 -> test_arquitetura_alvo_referencia_healthcheck_e_componentes
  RF-004 -> test_regras_negocio_contem_rn_isolamento_por_modo_operacional
  RF-005 -> test_runbook_contem_secao_triagem_erros_recorrentes_live
  RF-005 -> test_runbook_cobre_votacao_timeout_e_posicao_sem_protecao
  RF-006 -> test_runbook_define_metrica_diagnostico_baseline_em_minutos
  RF-007 -> test_synchronization_registra_sync_consolidacao_m2_022_6
  RNF-001 -> test_docs_alvo_respeitam_md013_80_colunas
  RNF-004 -> test_docs_nao_sugerem_bypass_de_guardrails
  RNF-005 -> test_docs_alvo_nao_contradizem_fluxo_live_entre_si
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ARQUITETURA = REPO_ROOT / "docs" / "ARQUITETURA_ALVO.md"
REGRAS = REPO_ROOT / "docs" / "REGRAS_DE_NEGOCIO.md"
RUNBOOK = REPO_ROOT / "docs" / "RUNBOOK_M2_OPERACAO.md"
SYNC = REPO_ROOT / "docs" / "SYNCHRONIZATION.md"

_CAMADAS = [
    "warm-up",
    "inferencia",
    "safety",
    "execucao",
    "reconciliacao",
]

_METRICAS = [
    "latencia de inferencia",
    "taxa de bloqueio",
    "divergencia",
    "posicoes sem protecao",
]

_MODOS = ["live", "shadow", "paper"]


# ---------------------------------------------------------------------------
# RF-001 — ARQUITETURA_ALVO.md: secao de fluxo live ponta-a-ponta
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_arquitetura_alvo_contem_secao_fluxo_live_ponta_a_ponta() -> None:
    """RF-001: Verifica secao explicita de fluxo live ponta-a-ponta com
    pelo menos 3 das 5 camadas listadas dentro da mesma secao.

    Deve FALHAR antes da implementacao.
    """
    text = ARQUITETURA.read_text(encoding="utf-8")

    # Busca por secao de segundo nivel (##) sobre fluxo live ponta-a-ponta
    section_pattern = re.compile(
        r"^##\s+.*fluxo.*live.*ponta.*a.*ponta.*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = section_pattern.search(text)
    assert match is not None, (
        "ARQUITETURA_ALVO.md nao contém seccao de nivel ## sobre "
        "'fluxo live ponta-a-ponta'. "
        "Adicionar secao descrevendo o ciclo completo das 5 camadas."
    )

    # Extrai o bloco da secao ate o proximo heading de mesmo nivel
    section_start = match.start()
    next_section = re.search(r"^##\s", text[section_start + 1:], re.MULTILINE)
    section_end = (
        section_start + 1 + next_section.start()
        if next_section
        else len(text)
    )
    section_text = text[section_start:section_end].lower()

    camadas_presentes = [c for c in _CAMADAS if c in section_text]
    assert len(camadas_presentes) >= 3, (
        f"Secao de fluxo live em ARQUITETURA_ALVO.md menciona apenas "
        f"{len(camadas_presentes)} das 5 camadas esperadas "
        f"({camadas_presentes}). Minimo: 3 camadas."
    )


# ---------------------------------------------------------------------------
# RF-002 — ARQUITETURA_ALVO.md: metricas operacionais por etapa
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_arquitetura_alvo_documenta_metricas_operacionais() -> None:
    """RF-002: Verifica presenca dos 4 termos canonicos de metricas
    operacionais diretamente em ARQUITETURA_ALVO.md.

    Deve FALHAR antes da implementacao (termos estao apenas no RUNBOOK).
    """
    text = ARQUITETURA.read_text(encoding="utf-8").lower()
    faltando = [m for m in _METRICAS if m not in text]
    assert not faltando, (
        "ARQUITETURA_ALVO.md nao documenta as seguintes metricas "
        f"operacionais: {faltando}. "
        "Adicionar secao de metricas com referencia cruzada ao Runbook."
    )


# ---------------------------------------------------------------------------
# RF-003 — ARQUITETURA_ALVO.md: secao healthcheck com componentes
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_arquitetura_alvo_referencia_healthcheck_e_componentes() -> None:
    """RF-003: Verifica secao explicita de healthcheck e componentes
    monitorados com referencia a go_live_preflight.py e
    healthcheck_live_execution.py dentro do mesmo bloco/secao.

    Deve FALHAR antes da implementacao (nao ha secao dedicada de componentes).
    """
    text = ARQUITETURA.read_text(encoding="utf-8")

    # A secao de healthcheck deve ter um header explícito
    section_pattern = re.compile(
        r"^##\s+.*healthcheck.*component.*$|"
        r"^##\s+.*component.*monitorad.*$|"
        r"^##\s+.*healthcheck.*monitorad.*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = section_pattern.search(text)
    assert match is not None, (
        "ARQUITETURA_ALVO.md nao tem secao de nivel ## sobre "
        "'healthcheck e componentes monitorados'. "
        "Adicionar secao listando componentes e referenciando ambos os scripts."
    )

    # Dentro dessa secao, ambos os scripts devem aparecer
    section_start = match.start()
    next_sec = re.search(r"^##\s", text[section_start + 1:], re.MULTILINE)
    section_end = (
        section_start + 1 + next_sec.start()
        if next_sec
        else len(text)
    )
    block = text[section_start:section_end]

    assert "go_live_preflight.py" in block, (
        "Secao de healthcheck em ARQUITETURA_ALVO.md nao referencia "
        "go_live_preflight.py."
    )
    assert "healthcheck_live_execution.py" in block, (
        "Secao de healthcheck em ARQUITETURA_ALVO.md nao referencia "
        "healthcheck_live_execution.py."
    )


# ---------------------------------------------------------------------------
# RF-004 — REGRAS_DE_NEGOCIO.md: RN de isolamento por modo operacional
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_regras_negocio_contem_rn_isolamento_por_modo_operacional() -> None:
    """RF-004: Verifica que existe uma regra RN-xxx que menciona os tres
    modos (live, shadow, paper) dentro do mesmo bloco de regra, com
    referencia a fail-safe por modo.

    Deve FALHAR antes da implementacao.
    """
    text = REGRAS.read_text(encoding="utf-8")

    # Extrai blocos de regra RN-xxx ate o proximo ### ou fim do doc
    rn_headers = list(
        re.finditer(r"^###\s+(RN-\d+[^\n]*)\n", text, re.MULTILINE)
    )
    assert rn_headers, "Nenhum bloco RN-xxx encontrado em REGRAS_DE_NEGOCIO.md"

    for idx, hdr in enumerate(rn_headers):
        start = hdr.start()
        end = (
            rn_headers[idx + 1].start()
            if idx + 1 < len(rn_headers)
            else len(text)
        )
        block = text[start:end].lower()

        modos_presentes = [m for m in _MODOS if m in block]
        tem_fail_safe = "fail-safe" in block or "failsafe" in block
        tem_isolamento = "isolamento" in block or "isolar" in block

        if (
            len(modos_presentes) == 3
            and tem_fail_safe
            and tem_isolamento
        ):
            return  # passou

    pytest.fail(
        "REGRAS_DE_NEGOCIO.md nao tem regra RN-xxx que mencione "
        "os tres modos (live, shadow, paper) com fail-safe e isolamento "
        "no mesmo bloco. "
        "Adicionar RN de isolamento de risco por modo operacional."
    )


# ---------------------------------------------------------------------------
# RF-005 — RUNBOOK_M2_OPERACAO.md: secao de triagem de erros do ciclo live
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_runbook_contem_secao_triagem_erros_recorrentes_live() -> None:
    """RF-005a: Verifica secao explicita de triagem de erros recorrentes
    do ciclo live com pelo menos 3 passos numerados ou em lista.

    Deve FALHAR antes da implementacao (atual Troubleshooting cobre bootstrap).
    """
    text = RUNBOOK.read_text(encoding="utf-8")

    # Busca secao de nivel ## sobre triagem/erros do ciclo live
    secao_pattern = re.compile(
        r"^##\s+.*triagem.*erro.*live.*$|"
        r"^##\s+.*erros.*recorrentes.*ciclo.*$|"
        r"^##\s+.*troubleshooting.*ciclo.*live.*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = secao_pattern.search(text)
    assert match is not None, (
        "RUNBOOK_M2_OPERACAO.md nao tem secao ## sobre triagem de erros "
        "recorrentes do ciclo live. "
        "Adicionar secao dedicada ao ciclo live (nao ao bootstrap)."
    )

    # Dentro da secao deve haver pelo menos 3 itens de lista ou passos
    section_start = match.start()
    next_sec = re.search(r"^##\s", text[section_start + 1:], re.MULTILINE)
    section_end = (
        section_start + 1 + next_sec.start()
        if next_sec
        else len(text)
    )
    block = text[section_start:section_end]

    passos = re.findall(r"^[\d]+\.\s+.+$|^[-*]\s+.+$", block, re.MULTILINE)
    assert len(passos) >= 3, (
        f"Secao de triagem do ciclo live tem apenas {len(passos)} passos. "
        "Minimo: 3 passos acionaveis com fail-safe."
    )


@pytest.mark.docs
def test_runbook_cobre_votacao_timeout_e_posicao_sem_protecao() -> None:
    """RF-005b: Verifica que a secao de triagem do ciclo live cobre os erros
    canonicos: votacao, timeout e posicao sem protecao.

    Deve FALHAR antes da implementacao.
    """
    text = RUNBOOK.read_text(encoding="utf-8")

    secao_pattern = re.compile(
        r"^##\s+.*triagem.*erro.*live.*$|"
        r"^##\s+.*erros.*recorrentes.*ciclo.*$|"
        r"^##\s+.*troubleshooting.*ciclo.*live.*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = secao_pattern.search(text)
    assert match is not None, (
        "Secao de triagem do ciclo live nao encontrada em "
        "RUNBOOK_M2_OPERACAO.md. Necessario para cobrir votacao/timeout."
    )

    section_start = match.start()
    next_sec = re.search(r"^##\s", text[section_start + 1:], re.MULTILINE)
    section_end = (
        section_start + 1 + next_sec.start()
        if next_sec
        else len(text)
    )
    block = text[section_start:section_end].lower()

    assert re.search(r"vota[cç][aã]o|voting", block), (
        "Secao de triagem do ciclo live nao cobre erro de votacao."
    )
    assert "timeout" in block, (
        "Secao de triagem do ciclo live nao cobre timeout de reconciliacao."
    )
    assert re.search(r"posi[cç][aã]o sem prote[cç][aã]o|sem prote[cç][aã]o", block), (
        "Secao de triagem do ciclo live nao cobre posicao sem protecao."
    )


# ---------------------------------------------------------------------------
# RF-006 — RUNBOOK_M2_OPERACAO.md: metrica de diagnostico baseline
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_runbook_define_metrica_diagnostico_baseline_em_minutos() -> None:
    """RF-006: Verifica presenca de valor numerico de minutos como metrica
    de diagnostico baseline (alvo <= 5 min) na secao de triagem do ciclo live.

    Deve FALHAR antes da implementacao.
    """
    text = RUNBOOK.read_text(encoding="utf-8")

    secao_pattern = re.compile(
        r"^##\s+.*triagem.*erro.*live.*$|"
        r"^##\s+.*erros.*recorrentes.*ciclo.*$|"
        r"^##\s+.*troubleshooting.*ciclo.*live.*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = secao_pattern.search(text)
    assert match is not None, (
        "Secao de triagem do ciclo live nao encontrada. "
        "Necessaria para definir metrica de diagnostico baseline."
    )

    section_start = match.start()
    next_sec = re.search(r"^##\s", text[section_start + 1:], re.MULTILINE)
    section_end = (
        section_start + 1 + next_sec.start()
        if next_sec
        else len(text)
    )
    block = text[section_start:section_end]

    metrica_pattern = re.compile(
        r"(\d+)\s*min|\bdiagnostico\b.*?(\d+)",
        re.IGNORECASE,
    )
    match_metrica = metrica_pattern.search(block)
    assert match_metrica is not None, (
        "Secao de triagem do ciclo live nao define metrica numerica "
        "de diagnostico baseline em minutos. "
        "Adicionar alvo operacional (ex: 'Tempo de triagem esperado: <= 5 min')."
    )

    # Extrae valor numerico e valida <= 5
    grupo = match_metrica.group(1) or match_metrica.group(2)
    if grupo:
        assert int(grupo) <= 5, (
            f"Metrica de diagnostico baseline e {grupo} min, "
            "mas o alvo operacional e <= 5 min."
        )


# ---------------------------------------------------------------------------
# RF-007 — SYNCHRONIZATION.md: registro [SYNC] da consolidacao M2-022.6
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_synchronization_registra_sync_consolidacao_m2_022_6() -> None:
    """RF-007: Verifica que SYNCHRONIZATION.md tem um registro [SYNC] que
    referencia M2-022.6 E lista os 3 docs atualizados na consolidacao
    (ARQUITETURA_ALVO, REGRAS_DE_NEGOCIO, RUNBOOK_M2_OPERACAO).

    Deve FALHAR antes da implementacao (SYNCs atuais cobrem apenas PO/SA).
    """
    text = SYNC.read_text(encoding="utf-8")

    # Encontra todos os blocos SYNC que mencionam M2-022.6
    sync_blocks = re.findall(
        r"###\s+\[SYNC[^\]]*\][^\n]*M2-022\.6[^\n]*\n(.*?)(?=###|\Z)",
        text,
        re.DOTALL,
    )
    assert sync_blocks, (
        "SYNCHRONIZATION.md nao tem entrada [SYNC] para M2-022.6. "
        "Registrar consolidacao documental apos implementacao."
    )

    docs_obrigatorios = [
        "ARQUITETURA_ALVO.md",
        "REGRAS_DE_NEGOCIO.md",
        "RUNBOOK_M2_OPERACAO.md",
    ]

    for block in sync_blocks:
        docs_presentes = [d for d in docs_obrigatorios if d in block]
        if len(docs_presentes) == 3:
            return  # passou

    pytest.fail(
        "Nenhum registro [SYNC] para M2-022.6 em SYNCHRONIZATION.md lista "
        f"os 3 docs obrigatorios: {docs_obrigatorios}. "
        "O SYNC de consolidacao deve listar os docs atualizados."
    )


# ---------------------------------------------------------------------------
# RNF-001 — Conformidade MD013: linhas <= 80 colunas
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_docs_alvo_respeitam_md013_80_colunas() -> None:
    """RNF-001: Verifica que nenhuma linha em ARQUITETURA_ALVO.md,
    REGRAS_DE_NEGOCIO.md e RUNBOOK_M2_OPERACAO.md excede 80 caracteres.

    Excecoes: linhas de codigo (``` ou ~~~), URLs brutas, linhas em branco.
    Este teste deve PASSAR antes e depois da implementacao (regressao).
    """
    _CODE_FENCE = re.compile(r"^```|^~~~")
    _URL_LINE = re.compile(r"^\s*https?://\S+\s*$")

    violacoes: list[str] = []
    for doc_path in (ARQUITETURA, REGRAS, RUNBOOK):
        lines = doc_path.read_text(encoding="utf-8").splitlines()
        in_code_block = False
        for lineno, line in enumerate(lines, start=1):
            if _CODE_FENCE.match(line):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line.strip() or _URL_LINE.match(line):
                continue
            if len(line) > 80:
                violacoes.append(
                    f"{doc_path.name}:{lineno}: {len(line)} cols"
                )

    assert not violacoes, (
        "Linhas excedem 80 colunas (MD013) nos docs alvo:\n"
        + "\n".join(violacoes[:20])
        + ("\n... (truncado)" if len(violacoes) > 20 else "")
    )


# ---------------------------------------------------------------------------
# RNF-004 — Sem bypass de guardrails nos docs
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_docs_nao_sugerem_bypass_de_guardrails() -> None:
    """RNF-004: Verifica que nenhum dos 3 docs contem frases imperativas que
    sugiram desabilitar risk_gate ou circuit_breaker.

    Linhas com negacao explicita (sem/nunca/nao/jamais/proibido) sao
    excluidas — ex.: 'sem desabilitar risk_gate' e uma restricao, nao instrucao.
    Este teste deve PASSAR antes e depois da implementacao (regressao).
    """
    _BYPASS_PATTERNS = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"desabilitar\s+risk_gate",
            r"bypass\s+circuit_breaker",
            r"skip\s+risk_gate",
            r"desabilitar\s+circuit_breaker",
            r"ignorar\s+risk_gate",
        ]
    ]
    # Palavras de negacao que tornam a frase uma restricao, nao instrucao
    _NEGACOES = re.compile(
        r"\b(sem|nunca|nao|jamais|proibido|evite|evitar)\b",
        re.IGNORECASE,
    )

    violacoes: list[str] = []
    for doc_path in (ARQUITETURA, REGRAS, RUNBOOK):
        text = doc_path.read_text(encoding="utf-8")
        for pat in _BYPASS_PATTERNS:
            for m in pat.finditer(text):
                # Captura a linha completa onde o match ocorreu
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                line_end = line_end if line_end >= 0 else len(text)
                full_line = text[line_start:line_end]
                # Contexto estendido: 120 chars antes do match (cobre quebra
                # de linha anterior) — captura "sem" no fim da linha -1
                context_start = max(0, m.start() - 120)
                extended = text[context_start : m.end()]
                # Ignora se h\'a negacao no contexto imediato
                if _NEGACOES.search(extended):
                    continue
                lineno = text[: m.start()].count("\n") + 1
                violacoes.append(
                    f"{doc_path.name}:{lineno}: '{full_line.strip()}'"
                )

    assert not violacoes, (
        "Docs contem instrucoes que sugerem bypass de guardrails:\n"
        + "\n".join(violacoes)
    )


# ---------------------------------------------------------------------------
# RNF-005 — Consistencia cruzada: fluxo live sem contradicoes
# ---------------------------------------------------------------------------

@pytest.mark.docs
def test_docs_alvo_nao_contradizem_fluxo_live_entre_si() -> None:
    """RNF-005: Verifica que os 3 docs mencionam o mesmo conjunto de
    etapas do ciclo live (ao menos: inferencia, execucao, reconciliacao)
    sem contradicao explicita de ordem.

    Implementacao minima: cada doc deve citar pelo menos 2 das 3 etapas.
    """
    etapas_chave = ["inferencia", "execucao", "reconciliacao"]

    faltando: list[str] = []
    for doc_path in (ARQUITETURA, REGRAS, RUNBOOK):
        text = doc_path.read_text(encoding="utf-8").lower()
        presentes = [e for e in etapas_chave if e in text]
        if len(presentes) < 2:
            faltando.append(
                f"{doc_path.name}: apenas {presentes} das etapas {etapas_chave}"
            )

    assert not faltando, (
        "Os seguintes docs nao descrevem ao menos 2 etapas do ciclo live "
        "(inferencia, execucao, reconciliacao):\n"
        + "\n".join(faltando)
    )
