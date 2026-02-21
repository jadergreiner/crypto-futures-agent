#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Auto-Update Script
Sincroniza dados do dashboard com documentação oficial do projeto
Atualiza: dashboard_data.json a partir de STATUS_ATUAL.md, DECISIONS.md, etc.
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path

# Cores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def read_file(path):
    """Lê arquivo de forma segura"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"{Colors.WARNING}⚠️  Arquivo não encontrado: {path}{Colors.ENDC}")
        return ""
    except Exception as e:
        print(f"{Colors.FAIL}❌ Erro ao ler {path}: {e}{Colors.ENDC}")
        return ""

def extract_metrics_from_status(content):
    """Extrai métricas do STATUS_ATUAL.md"""
    metrics = []
    
    # Padrão para tabela de métricas
    pattern = r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|'
    matches = re.findall(pattern, content)
    
    for match in matches:
        metric_name, value, required, status = match
        metric_name = metric_name.strip()
        value = value.strip()
        required = required.strip()
        
        # Determinar status baseado em símbolos
        status_type = "bad"
        if "✅" in status or "OK" in status:
            status_type = "good"
        elif "❌" in status or "CRÍTICO" in status:
            status_type = "bad"
        
        metrics.append({
            "name": metric_name,
            "value": value,
            "required": required,
            "status": status_type
        })
    
    return metrics

def extract_decisions_from_file(content):
    """Extrai decisões do DECISIONS.md"""
    decisions = []
    
    # Procurar por padrões de decisão
    decision_pattern = r'## 🔔 DECISÃO #(\d+).*?\n\*\*Data:\*\*(.*?)\n.*?\*\*Status:\*\*(.*?)\n'
    matches = re.finditer(decision_pattern, content, re.DOTALL)
    
    for match in matches:
        decision_id = int(match.group(1))
        date = match.group(2).strip()
        status_text = match.group(3).strip()
        
        # Mapear status
        status = "pending"
        if "✅" in status_text or "APROVADO" in status_text:
            status = "approval"
        elif "IN PROGRESS" in status_text or "PROGRESSO" in status_text:
            status = "in-progress"
        
        decisions.append({
            "id": decision_id,
            "status": status,
            "date": date
        })
    
    return decisions

def extract_team_from_content(content):
    """Extrai informações de equipe da documentação - 12 membros"""
    team = [
        {
            "role": "📊 Investidor",
            "name": "Angel (Sócio-Majoritário & LP)",
            "status": "🆕 EXPANDIDO | VC/Trading Expertise",
            "priority": "critical",
            "specialties": ["Venture Capital", "Institutional Trading", "Risk Appetite", "Cost of Delay Analysis", "Go/No-Go Decisions", "Capital Allocation"],
            "veto_power": True,
            "decision_authority": "Strategic Direction, Go/No-Go Milestones, Capital Approval, Risk Appetite Setting"
        },
        {
            "role": "🎯 Facilitador",
            "name": "Elo (Agile Coach & Alinhamento)",
            "status": "🆕 EXPANDIDO | Governance & Sync Orchestration",
            "priority": "critical",
            "specialties": ["Agile Coaching", "Board Facilitation", "Comunicação Não-Violenta", "[SYNC] Enforcement", "Roadmap Orchestration", "Decision Making"],
            "veto_power": False,
            "decision_authority": "Documentação Governance, Protocol Enforcement, Meeting Facilitation, Stakeholder Alignment"
        },
        {
            "role": "📖 Doc Advocate",
            "name": "Audit (Guardião Docs & Auditoria)",
            "status": "🆕 EXPANDIDO | Docs-as-Code Specialist",
            "priority": "critical",
            "specialties": ["Markdown Avançado", "Docs-as-Code", "[SYNC] Protocol", "Auditoria Repositório", "Tech Writing", "Compliance"],
            "veto_power": False,
            "decision_authority": "Docs Governance, [SYNC] Protocol Enforcement, File Hierarchy, Onboarding"
        },
        {
            "role": "💼 Gerente de Projetos",
            "name": "Planner (Estrategista de Operações Ágeis)",
            "status": "🆕 EXPANDIDO | Gestão Ágil Avançada",
            "priority": "critical",
            "specialties": ["Ágil/Scrum/Kanban", "Timeline Orchestration", "Cost of Delay Analysis", "Stakeholder Communication", "GitHub Projects", "Burndown Tracking"],
            "veto_power": False,
            "decision_authority": "Timeline Management, Blocker Resolution, ROI Prioritization, Executive Reporting"
        },
        {
            "role": "🏗️ Arquiteto de Dados",
            "name": "Flux (10+ anos Time-Series)",
            "status": "✅ EXPANDIDO",
            "priority": "high",
            "specialties": [
                "Time-Series Management",
                "Parquet Optimization",
                "Feature Engineering (104 indicadores)",
                "Multi-Timeframe Consistency",
                "Data Integrity (Zero Look-Ahead Bias)",
                "Pipeline Performance"
            ],
            "veto_power": False,
            "decision_authority": "Data Pipeline Architecture, Cache Optimization, Feature Consistency, Data Quality Validation"
        },
        {
            "role": "🤖 Engenheiro ML",
            "name": "The Brain (8+ anos Data Science)",
            "status": "✅ EXPANDIDO | Especialista RL & Trading",
            "priority": "critical",
            "specialties": [
                "Reinforcement Learning (PPO) Optimization",
                "Feature Engineering (104 indicadores)",
                "Reward Shaping & Incentive Design",
                "Walk-Forward Validation (OOT testing)",
                "Overfitting Detection & Generalization",
                "Experiment Tracking & Reproducibility"
            ],
            "veto_power": False,
            "decision_authority": "RL Algorithm Design, Feature Quality, Reward Function, Model Validation, Training Strategy"
        },
        {
            "role": "💰 Head de Finanças & Risco",
            "name": "Dr. 'Risk' (22+ anos experiência)",
            "status": "🆕 NOVO | Integrado | Veto Power Ativo",
            "priority": "critical",
            "specialties": ["Binance Futures", "Derivativos Cripto", "Risk Quantitativo", "Hedge Strategies"],
            "veto_power": True,
            "decision_authority": "Decision #3 (Posições) + Risk Clearance Gates"
        },
        {
            "role": "💻 Tech Lead",
            "name": "The Blueprint (10+ anos System Design)",
            "status": "✅ EXPANDIDO | Arquiteto de Soluções",
            "priority": "critical",
            "specialties": [
                "Data Architecture Design (3-tier caching)",
                "System Integration & Interoperability (Gymnasium ≡ Binance)",
                "Operational Security & Resilience (Circuit Breakers, Kill Switches)",
                "Horizontal Scalability (16 → 200 pares = config change)",
                "Cloud Infrastructure Strategy",
                "Cost Optimization & Efficiency"
            ],
            "veto_power": False,
            "decision_authority": "System Architecture, Integration Strategy, Scalability Roadmap, Tech/Risk Trade-offs, Interop Validation"
        },
        {
            "role": "🛣️ Product Owner",
            "name": "Visão (Estrategista Produto)",
            "status": "🆕 NOVO | Roadmap & DoD",
            "priority": "critical",
            "specialties": ["Roadmap Planning", "Backlog Priorização", "Product Discovery", "Go-to-Market", "KPI Tracking"],
            "veto_power": False,
            "decision_authority": "Roadmap Execution, Feature Prioritization, DoD Definition"
        },
        {
            "role": "📈 Product Manager (Vision)",
            "name": "Estrategista Delivery | Fintech Expert",
            "status": "✅ EXPANDIDO | Feature Delivery Strategist",
            "priority": "critical",
            "specialties": [
                "Sprint Execution & Capacity Planning (story estimation, burndown, velocity)",
                "MoSCoW Prioritization (Must/Should/Could/Won't framework, scope negotiation)",
                "MVP & Iteração Rápida (hypothesis validation, release loops, feedback integration)",
                "Stakeholder Management (Tech↔Finance translation, escalation, trade-off communication)",
                "UX for Bots (structured logs, real-time dashboards, actionable alerts, audit trails)",
                "Roadmap Ownership (v0.4→v1.0 versioning, F-01→F-15 sequencing, dependency mapping)"
            ],
            "veto_power": False,
            "decision_authority": "Feature Prioritization, Sprint Breakdown, Roadmap Execution, Milestone Delivery, Blocker Resolution, MVP Validation"
        },
        {
            "role": "🛡️ Risk Manager",
            "name": "Guardian (10+ anos Derivativos)",
            "status": "✅ EXPANDIDO | Especialista Risco de Cauda",
            "priority": "critical",
            "specialties": [
                "Gestão de Exposição & Correlação",
                "Métricas de Risco de Cauda (Max DD, Consecutive Losses)",
                "Mecânicas de Liquidação (Binance leverage, ADL)",
                "Profit Guardian Mode & Circuit Breakers",
                "Validação de Sinais ML (Confidence threshold)",
                "Kelly Criterion & Dimensionamento Dinâmico"
            ],
            "veto_power": False,
            "decision_authority": "Risk Exposure Limits, Position Sizing, Kill Switch Activation, ML Signal Validation, Drawdown Protection"
        },
        {
            "role": "✅ Audit (QA Manager)",
            "name": "10+ anos Automation | Chaos Engineering",
            "status": "✅ EXPANDIDO | Especialista Testes Críticos",
            "priority": "critical",
            "specialties": [
                "pytest/unittest.mock (test automation mastery)",
                "Edge case detection (falta liquidez, timeouts, divergência)",
                "Data leakage detection (Point-in-Time validation, look-ahead bias)",
                "Chaos Engineering (simulate failures, latency, crashes)",
                "Stress testing (volatilidade extrema, circuit breaker validation)",
                "Metrics-driven QA (coverage, regression rate, MTTR, release gates)"
            ],
            "veto_power": False,
            "decision_authority": "Test Coverage Enforcement, Quality Gates (90%+ required), Backtest Integrity Validation, Release Readiness Certification, Edge Case Coverage Requirements"
        },
        {
            "role": "✅ The Implementer (Dev)",
            "name": "6+ anos Python/Finanças | Core Engineer",
            "status": "✅ EXPANDIDO | Engenheiro de Software Sênior",
            "priority": "critical",
            "specialties": [
                "Python fluente (decoradores, geradores, context managers, POO)",
                "Data wrangling (Pandas vectorization, K-line manipulation, 104 indicadores)",
                "Testes automatizados (pytest, unittest.mock, E2E testing, 100% coverage)",
                "API Binance mastery (Futures, Spot, WebSocket, rate limiting, error handling)",
                "Performance optimization (Big-O analysis, profiling, caching, parallelization)",
                "Resilience & error handling (exponential backoff, circuit breaker, graceful degradation)"
            ],
            "veto_power": False,
            "decision_authority": "Feature Implementation Authority (F-01→F-15), Code Quality Gates (100% coverage critical), Performance Optimization Decisions, API Integration Strategy, Refactoring Approval"
        },
        {
            "role": "🤖 Tech Lead & AI Architect",
            "name": "Arch (10+ Data Eng + 5+ HFT RL)",
            "status": "✅ NOVO | RL & PPO Specialist",
            "priority": "critical",
            "specialties": [
                "Reinforcement Learning (PPO) — Domínio total de hyperparameters, entropy bonus, clip ratio tuning",
                "Gymnasium Environment Design (F-12a) — State/action space, observation normalization, latency optimization",
                "Feature Engineering & Data Leakage Detection (F-04) — 104 indicators audit, point-in-time validation, look-ahead bias prevention",
                "Model Monitoring & Drift Detection — Training stability metrics, inference monitoring, A/B testing framework",
                "Curriculum Learning & Training Strategy — Progressive difficulty, warm-up vs. online learning, exploration vs. exploitation",
                "Statistical Validation & Backtesting Rigor — Out-of-sample testing, walk-forward analysis, Sharpe bootstrap confidence intervals"
            ],
            "veto_power": False,
            "decision_authority": "Reward Shaping (F-11), PPO Training Strategy, Gymnasium Environment Validation, Feature Leakage Audit, Model Convergence Gates, Statistical Validation Rigor"
        },
        {
            "role": "📉 Senior Crypto Trader",
            "name": "Alpha (10.000+ horas | SMC Specialist)",
            "status": "✅ NOVO | Price Action & Signal Validator",
            "priority": "critical",
            "specialties": [
                "Smart Money Concepts (SMC) — BOS, CHoCH, Order Blocks, Fair Value Gaps identification",
                "Liquidez & Stop Loss Mapping — Equal Highs/Lows, Premium/Discount zones, Liquidity Sweeps",
                "Multi-Timeframe Analysis (MTF) — D1→H4→H1/M15 alignment, regime detection",
                "Gerenciamento de Trade & R:R — Risk/Reward 1:3+ ratio, entry precision, sniper discipline",
                "Price Action & Harmonic Patterns — Rejections, wicks, breakouts, trend/retests, W-bottoms/M-tops",
                "Signal Validation & Confluence Scoring — Multi-signal veto, quality >quantity, checklist rigor"
            ],
            "veto_power": False,
            "decision_authority": "Signal Validation & Approval, Price Action Analysis, R:R Ratio Enforcement, Multi-Timeframe Alignment, Confluence Scoring, Market Regime Detection"
        },
        {
            "role": "🏛️ Conselheiro Estratégico",
            "name": "15+ anos VC/FinTech | Board Member",
            "status": "✅ NOVO | Membro Conselho Externo",
            "priority": "critical",
            "specialties": [
                "Market & competitive intelligence (trend analysis, TAM, unit economics)",
                "Governance & risk management (board decision frameworks, capital allocation)",
                "Scaling & business model (go-to-market, multi-asset expansion, revenue strategy)",
                "Team & organization (hiring, incentive alignment, succession planning)",
                "Investor relations (quarterly updates, fundraising strategy, LP communication)",
                "Crisis management (regulatory, breach, liquidation response)"
            ],
            "veto_power": False,
            "decision_authority": "Strategic direction, Capital allocation, Investor relations, Board meeting agenda, Regulatory/crisis decisions"
        },
        {
            "role": "🔍 Auditor Independente",
            "name": "12+ anos Big 4 | Compliance & Audit",
            "status": "✅ NOVO | Membro Auditoria Externo",
            "priority": "critical",
            "specialties": [
                "Integridade de dados (validation, reconciliation, point-in-time reconstruction)",
                "Rastreabilidade de decisões (audit logs, blockchain-style trails, approval workflows)",
                "Conformidade regulatória (Binance ToS, AML/KYC, GDPR, reporting)",
                "Prevenção de fraude (segregation of duties, access controls, change management)",
                "Avaliação de risco (control gaps, single points of failure, disaster recovery)",
                "Incident response (playbook validation, forensic analysis, regulatory reporting)"
            ],
            "veto_power": False,
            "decision_authority": "Audit findings, Control validation, Compliance certification, Third-party risk assessment, Incident reporting"
        }
    ]
    
    return team

def update_dashboard_data(project_root="."):
    """Atualiza dashboard_data.json com dados atualizados"""
    
    print(f"{Colors.HEADER}{Colors.BOLD}🔄 Sincronizando Dashboard...{Colors.ENDC}\n")
    
    # Caminhos
    status_path = Path(project_root) / "docs" / "STATUS_ATUAL.md"
    decisions_path = Path(project_root) / "docs" / "DECISIONS.md"
    dashboard_json_path = Path(project_root) / "dashboard_data.json"
    
    # Carregar dados base
    with open(dashboard_json_path, 'r', encoding='utf-8') as f:
        dashboard_data = json.load(f)
    
    # Atualizar timestamp
    dashboard_data["project"]["updated"] = datetime.now().isoformat()
    
    # Ler arquivos
    status_content = read_file(str(status_path))
    decisions_content = read_file(str(decisions_path))
    
    # Extrair métricas
    if status_content:
        print(f"{Colors.OKBLUE}📊 Extraindo métricas de STATUS_ATUAL.md...{Colors.ENDC}")
        metrics = extract_metrics_from_status(status_content)
        if metrics:
            dashboard_data["metrics"][0]["items"] = metrics
            print(f"{Colors.OKGREEN}✅ {len(metrics)} métricas atualizadas{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠️  Nenhuma métrica encontrada{Colors.ENDC}")
    
    # Extrair decisões
    if decisions_content:
        print(f"{Colors.OKBLUE}🎯 Extraindo decisões de DECISIONS.md...{Colors.ENDC}")
        decisions = extract_decisions_from_file(decisions_content)
        if decisions:
            # Mesclar com dados existentes
            for decision in decisions:
                for existing_decision in dashboard_data["decisions"]:
                    if existing_decision["id"] == decision["id"]:
                        existing_decision["status"] = decision["status"]
                        existing_decision["date"] = decision["date"]
                        break
            print(f"{Colors.OKGREEN}✅ {len(decisions)} decisões atualizadas{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠️  Nenhuma decisão encontrada{Colors.ENDC}")
    
    # Atualizar equipe (incluindo Doc Advocate)
    print(f"{Colors.OKBLUE}👥 Atualizando equipe com Doc Advocate...{Colors.ENDC}")
    dashboard_data["team"] = extract_team_from_content(status_content)
    print(f"{Colors.OKGREEN}✅ Equipe atualizada ({len(dashboard_data['team'])} membros){Colors.ENDC}")
    
    # Salvar dados atualizados
    with open(dashboard_json_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}✅ Dashboard sincronizado com sucesso!{Colors.ENDC}")
    print(f"{Colors.OKCYAN}📁 Arquivo: {dashboard_json_path}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}🕐 Atualizado: {dashboard_data['project']['updated']}{Colors.ENDC}\n")
    
    return True

if __name__ == "__main__":
    try:
        # Executar sincronização
        update_dashboard_data(project_root=".")
        print(f"{Colors.OKGREEN}🎉 Execução completada!{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Erro na sincronização: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
