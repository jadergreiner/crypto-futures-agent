# Script PowerShell para deletar 77 arquivos duplicados de forma segura
# Data: 22 FEV 2026
# Owner: Facilitador
# Safety: Com log e backup

$RootPath = "C:\repo\crypto-futures-agent"
$ArchiveDir = "$RootPath\archive_deleted_docs_22FEV"
$LogFile = "$RootPath\cleanup_log_22FEV.txt"

# Lista dos 77 arquivos a deletar
$FilesToDelete = @(
    # CATEGORY 1: DELIVERY/STATUS/REPORTS (15)
    "AGENTES_AUTONOMOS_ENTREGA_21FEV.md",
    "AGENTES_FINAL_DELIVERY_21FEV.md",
    "BRIEFING_AGENTES_AUTONOMOS_22FEV.md",
    "BRIEFING_FINAL_VALIDATION_21FEV.md",
    "DELIVERY_F08_SUMMARY.md",
    "DELIVERY_SUMMARY.txt",
    "DELIVERY_SUMMARY_F12_SPRINT_20FEV.md",
    "ENTREGA_FINAL_F12_AGENTES.md",
    "ENTREGA_PHASE_3_BACKTEST_21FEV.md",
    "ENTREGA_SISTEMA_REUNIOES.txt",
    "EXECUTION_PHASE_1_SUMMARY.md",
    "F06_F07_DELIVERY_REPORT.md",
    "F08_DELIVERY_REPORT.md",
    "F09_DELIVERY_REPORT.md",
    "FINAL_DELIVERY_SUMMARY.md",

    # CATEGORY 2: DECISÕES/EXECUTIVO (12)
    "AUTHORIZATION_OPÇÃO_C_20FEV.txt",
    "BACKLOG_ACOES_CRITICAS_20FEV.md",
    "DASHBOARD_EXECUTIVO_20FEV.md",
    "DIAGNOSTICO_EXECUTIVO_20FEV.md",
    "DIRECTOR_BRIEF_20FEV.md",
    "EXECUTIVE_SUMMARY.txt",
    "PHASE_3_EXECUTIVE_DECISION_REPORT.md",
    "PHASE_3_RISK_CLEARANCE_STATUS.md",
    "RELATORIO_COMITE_REUNIAO_21FEV_2026.md",
    "RELATORIO_FINAL_F12_SPRINT.md",
    "RESUMO_EXECUCAO_FINAL.md",
    "RESUMO_FINAL_PRODUCAO.md",

    # CATEGORY 3: PHASE REPORTS (15)
    "CONSOLIDADO_CICLO_IMPLEMENTACAO.md",
    "CONSOLIDADO_FEVEREIRO_2026.md",
    "DAILY_SPRINT_REPORT_F12_DAY1.md",
    "DAILY_SPRINT_REPORT_F12_DAY2.md",
    "F12_KICKOFF_SUMMARY.md",
    "FINAL_VALIDATION_CONSOLIDATED.json",
    "FINAL_VALIDATION_SIGN_OFF_21FEV.md",
    "PHASE_4_READINESS_REPORT.json",
    "PHASE_4_READINESS_REPORT.py",
    "PHASE4_FINAL_READINESS_REPORT.json",
    "PHASE4_FINAL_STATUS.json",
    "PHASE4_HANDOFF_EXECUTIVO.md",
    "PHASE4_REVALIDATION_READINESS.md",

    # CATEGORY 4: SYNC/DOCUMENTATION (6)
    "DOCUMENTATION_SYNC_SUMMARY_20FEV.md",
    "SYNC_PHASE3_DOCUMENTATION_UPDATE.md",
    "SYNC_SUMMARY_20FEV_2026.md",
    "SYNC_SUMMARY_21FEV_LEARNING.md",
    "SYNC_DOCS_21FEV_2026.md",
    "PROMPT_ATUALIZA_DOCS_RESUMO.md",

    # CATEGORY 5: JSON STATUS FILES (9)
    "AGENTES_DELIVERY_STATUS_FINAL.json",
    "AGENTS_DELIVERY_STATUS.json",
    "F12B_VALIDATION_STATUS.json",
    "FINAL_ML_OPERATIONAL_VALIDATION_JSON.json",
    "FINAL_ML_VALIDATION_OUTPUT.json",
    "FINAL_SWE_TECHNICAL_VALIDATION.json",
    "FINAL_VALIDATION_CONSOLIDATED.json",
    "INTEGRATION_STATUS.json",
    "PRE_FLIGHT_STATUS.json",

    # CATEGORY 6: MISCELLANEOUS (20+)
    "ADMINISTRACAO_NOVOS_7_PARES.md",
    "ARVORE_DECISAO_MODOS.md",
    "CARTAO_CONSULTA_IMPRESSAO.md",
    "CHECKLIST_FINAL_EXECUTIVO.txt",
    "COMECE_AQUI.md",
    "CONCURRENT_TRAINING_BUGFIX.md",
    "CONCURRENT_TRAINING_GUIDE.md",
    "CONCURRENT_TRAINING_TESTING.md",
    "CORRECTIONS_AND_ACTIVATIONS.md",
    "LEIA_ME_PRIMEIRO.md",
    "COPILOT_INDUCTION.md",
    "FRAMEWORK_FINAL_SUMMARY.txt",
    "GUIA_INICIO_LIVE_TREINAMENTO_APRENDIZAGEM.md",
    "GUIA_PPO_TRAINING_PHASE4.md",
    "IMPLEMENTATION_SUMMARY.md",
    "IMPLEMENTATION_SUMMARY_OPPORTUNITY_LEARNING.md",
    "IMPLEMENTATION_SUMMARY_STAY_OUT.md",
    "INDEX_REFERENCE.txt",
    "INDICE_GUIAS.md",
    "MARKDOWN_LINT_FINAL_REPORT.md",
    "ML_OPERATIONS_CHECKLIST.md",
    "ML_OPERATIONS_FINAL_DELIVERY.json",
    "ML_OPERATIONS_FINAL_STATUS.txt",
    "ML_PRE_FLIGHT_CHECKLIST.md",
    "ML_TEAM_HANDOFF.md",
    "ML_VALIDATION_COMPLETION_SUMMARY.txt",
    "OPERACAO_C_GUIA_TRANSPARENTE.md",
    "OPERATOR_GO_AHEAD.txt",
    "OPERATOR_GUIDE_STAY_OUT_LEARNING.md",
    "OPERATOR_MANUAL.md",
    "OPERATOR_QUICKSTART.md",
    "OPTION2_STATUS.md",
    "ORCHESTRATOR_DELIVERY_SUMMARY.md",
    "ORCHESTRATOR_USAGE_GUIDE.md",
    "PAINEL_MONITORAMENTO_21FEV_2026.md",
    "RL_TRAINING_GUIDE.md",
    "START_HERE.txt",
    "SUMARIO_EXECUTIVO_VALIDACAO.txt",
    "SWE_FINAL_SIGN_OFF.txt",
    "SWE_INTEGRATION_STATUS.txt",
    "TRAINING_WEEK_OPERATIONS.md",
    "VALIDACAO_CONFIGURACAO.md",
    "VISAO_COMPLETA_SISTEMA.txt"
)

# Criar archive dir
if (!(Test-Path $ArchiveDir)) {
    New-Item -ItemType Directory -Path $ArchiveDir | Out-Null
    Write-Host "✅ Criado diretório archive: $ArchiveDir"
}

# Log header
$LogContent = @"
===== CLEANUP LOG - Root Documentation Files =====
Data: 22 FEV 2026
Owner: Facilitador/Git Master

INSTRUCOES:
- Arquivos encontrados sao movidos para archive
- Se arquivo nao existe, é registrado como SKIPPED
- Ao final, todos os arquivos podem ser deletados permanentemente
- Git rastreara delecao com historico intacto

RESUMO DE DELECAO:
===================================================
"@

Add-Content -Path $LogFile -Value $LogContent

$DeletedCount = 0
$SkippedCount = 0

foreach ($File in $FilesToDelete) {
    $FilePath = Join-Path -Path $RootPath -ChildPath $File

    if (Test-Path $FilePath) {
        # Arquivo existe - mover para archive
        try {
            Move-Item -Path $FilePath -Destination $ArchiveDir -Force
            Write-Host "OK: $File"
            Add-Content -Path $LogFile -Value "OK DELETADO: $File"
            $DeletedCount++
        } catch {
            Write-Host "ERRO ao deletar $File : $_"
            Add-Content -Path $LogFile -Value "ERRO: $File"
        }
    } else {
        # Arquivo nao existe
        Write-Host "SKIP: $File (nao existe)"
        Add-Content -Path $LogFile -Value "SKIP: $File"
        $SkippedCount++
    }
}

# Log footer
$LogFooter = "
===============================================================
RESUMO FINAL:
Deletados: $DeletedCount arquivos
Nao encontrados: $SkippedCount arquivos
Total processado: $($DeletedCount + $SkippedCount)
Data: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')
===============================================================

PROXIMOS PASSOS:
1. Revisar arquivos em archive_deleted_docs_22FEV/
2. Se OK - deletar permanentemente
3. Atualizar README.md
4. Commit: [SYNC] Cleanup root

REFERENCIA: docs/DECISIONS.md #1
"

Add-Content -Path $LogFile -Value $LogFooter

Write-Host ""
Write-Host "===== CLEANUP COMPLETO ====="
Write-Host "Deletados: $DeletedCount"
Write-Host "Nao encontrados: $SkippedCount"
Write-Host "Log: $LogFile"
Write-Host "Archive: $ArchiveDir"
