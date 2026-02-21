#!/usr/bin/env python3
"""
Template de Reunião de Board com 16 Membros
Define estrutura padrão de coleta de opiniões por especialidade

Cada Decisão segue este ciclo:
1️⃣ Apresentação do Tópico (5 min)
2️⃣ Ciclo de Opiniões — cada membro opina em sequência (40 min)
3️⃣ Síntese de Posições (5 min)
4️⃣ Discussão Aberta (10 min)
5️⃣ Votação Final — Angel toma decisão (5 min)
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PerguntaPorEspecialidade:
    """Pergunta estruturada para cada tipo de especialidade"""

    especialidade: str
    pergunta_principal: str
    sub_perguntas: List[str]
    criterios_avaliacao: List[str]
    impactos_esperados: List[str]


class TemplateReuniaoBoardMembros:
    """Template de reunião estruturada para 16 membros"""

    # Perguntas por especialidade para cada tipo de decisão
    PERGUNTAS_POR_ESPECIALIDADE = {
        "ML_TRAINING_STRATEGY": {  # Decision #2 exemplo
            "executiva": PerguntaPorEspecialidade(
                especialidade="Executiva (Angel)",
                pergunta_principal="Qual opção melhor equilibra ROI, timeline e risco?",
                sub_perguntas=[
                    "Qual é o custo de oportunidade cada dia de delay?",
                    "Qual opção protege melhor o capital investido?",
                    "Qual é seu apetite de risco para este trade-off?"
                ],
                criterios_avaliacao=[
                    "Retorno esperado em 90 dias",
                    "Drawdown máximo aceitável",
                    "Time-to-market vs. qualidade"
                ],
                impactos_esperados=[
                    "ROI projetado",
                    "Sharpe ratio esperado",
                    "Tempo até v1.0 live"
                ]
            ),

            "machine_learning": PerguntaPorEspecialidade(
                especialidade="Machine Learning (The Brain)",
                pergunta_principal="Qual opção garante melhor generalização e robustez?",
                sub_perguntas=[
                    "Qual opção implementa rigor científico (Walk-Forward validation)?",
                    "Qual minimiza overfitting e risk de regime shift?",
                    "Como cada opção se comporta em novo mercado?"
                ],
                criterios_avaliacao=[
                    "Walk-Forward Sharpe >0.3",
                    "Overfitting detection (train≈test)",
                    "Regime change detection capability"
                ],
                impactos_esperados=[
                    "Modelo robusto vs. frágil",
                    "Confiança em produção",
                    "Necessidade de retraining"
                ]
            ),

            "arquitetura": PerguntaPorEspecialidade(
                especialidade="Arquitetura (The Blueprint)",
                pergunta_principal="Qual opção é tecnicamente viável em timeline proposta?",
                sub_perguntas=[
                    "Qual opção requer refactoring de componentes críticos?",
                    "Qual impacta menos Gymnasium-Binance interop?",
                    "Qual escala melhor para 200 pares?"
                ],
                criterios_avaliacao=[
                    "Interoperabilidade mantida",
                    "Zero breaking changes",
                    "Horizontal scaling capability"
                ],
                impactos_esperados=[
                    "Tech debt criado/reduzido",
                    "Scalability preservada",
                    "Integration complexity"
                ]
            ),

            "infraestrutura_ml": PerguntaPorEspecialidade(
                especialidade="Infraestrutura ML (Arch)",
                pergunta_principal="Qual opção é exequível com nossos recursos de cluster?",
                sub_perguntas=[
                    "Quanto GPU/CPU cada opção consome?",
                    "Qual timeline é realista com hardware atual?",
                    "Qual é o custo operacional (cloud, storage)?"
                ],
                criterios_avaliacao=[
                    "CPU utilização <80%",
                    "Memory footprint <disponível",
                    "Training cost <orçamento"
                ],
                impactos_esperados=[
                    "Upgrades necessários",
                    "Despesa infrastructure",
                    "Risk de timeouts/crashes"
                ]
            ),

            "risco": PerguntaPorEspecialidade(
                especialidade="Risco (Guardian)",
                pergunta_principal="Qual opção minimiza risco de perdas em produção?",
                sub_perguntas=[
                    "Qual opção tem maior risco de margin call se falhar?",
                    "Qual precisa de mais circuit breakers?",
                    "Como cada opção se comporta em black swan?"
                ],
                criterios_avaliacao=[
                    "Max Drawdown expectativa",
                    "Margin call probability",
                    "Recovery capability"
                ],
                impactos_esperados=[
                    "Necessidade de hedges",
                    "Kill Switch triggers",
                    "Position size limits"
                ]
            ),

            "dados": PerguntaPorEspecialidade(
                especialidade="Dados (Flux)",
                pergunta_principal="Qual opção mantém integridade e performance dos dados?",
                sub_perguntas=[
                    "Qual opção causa mais risco de data leakage?",
                    "Qual precisa de mais Point-in-Time validation?",
                    "Qual afeta a performance F-12b?"
                ],
                criterios_avaliacao=[
                    "Feature consistency mantida",
                    "Look-ahead bias risk",
                    "Backtest performance"
                ],
                impactos_esperados=[
                    "Cache invalidation frequency",
                    "Database redesign needed",
                    "Pipeline latency"
                ]
            ),

            "qualidade": PerguntaPorEspecialidade(
                especialidade="Qualidade (Audit/QA)",
                pergunta_principal="Qual opção é mais testável e validável?",
                sub_perguntas=[
                    "Qual opção tem mais edge cases?",
                    "Qual requer menos chaos engineering para validar?",
                    "Qual tem melhor coverage alcançável?"
                ],
                criterios_avaliacao=[
                    "Test coverage >90%",
                    "Edge case identification",
                    "Regression risk"
                ],
                impactos_esperados=[
                    "QA timeline expansão",
                    "Test suite size",
                    "Release readiness confidence"
                ]
            ),

            "financeira": PerguntaPorEspecialidade(
                especialidade="Finanças (Dr. Risk)",
                pergunta_principal="Qual opção tem melhor trade-off custo/benefício?",
                sub_perguntas=[
                    "Qual é o custo real (infra + pessoal) por opção?",
                    "Qual opção libera capital mais rápido?",
                    "Qual tem melhor ROI em 90 dias?"
                ],
                criterios_avaliacao=[
                    "Total cost of ownership",
                    "Break-even timeline",
                    "ROI projeção realista"
                ],
                impactos_esperados=[
                    "Budget deployment",
                    "Capital efficiency",
                    "Shareholder returns"
                ]
            ),

            "trading": PerguntaPorEspecialidade(
                especialidade="Trading (Alpha)",
                pergunta_principal="Qual opção produz melhor execução e price action?",
                sub_perguntas=[
                    "Qual opção melhora order fill rates?",
                    "Qual reduz slippage?",
                    "Qual melhor captura SMC patterns?"
                ],
                criterios_avaliacao=[
                    "Fill rate expectativa",
                    "Slippage reduction",
                    "PnL per trade average"
                ],
                impactos_esperados=[
                    "Execution quality",
                    "Market microstructure edge",
                    "Win rate improvement"
                ]
            ),

            "produto": PerguntaPorEspecialidade(
                especialidade="Produto (Vision)",
                pergunta_principal="Qual opção melhor posiciona o produto no mercado?",
                sub_perguntas=[
                    "Qual opção cria melhor diferencial vs. concorrentes?",
                    "Qual é mais fácil de comunicar ao investidor?",
                    "Qual permite escala mais rápido?"
                ],
                criterios_avaliacao=[
                    "Market differentiation",
                    "Competitive edge clarity",
                    "Go-to-market simplicity"
                ],
                impactos_esperados=[
                    "Positioning strength",
                    "Sales narrative",
                    "Growth potential"
                ]
            ),

            "implementacao": PerguntaPorEspecialidade(
                especialidade="Implementação (Dev)",
                pergunta_principal="Qual opção é mais viável com código atual?",
                sub_perguntas=[
                    "Qual opção causa menos refactoring?",
                    "Qual reutiliza mais código existente?",
                    "Qual tem menos bugs esperados?"
                ],
                criterios_avaliacao=[
                    "Lines of code changed",
                    "Code reuse percentage",
                    "Complexity metrics"
                ],
                impactos_esperados=[
                    "Development effort hours",
                    "Code debt accumulation",
                    "Tech debt payoff needed"
                ]
            ),

            "documentacao": PerguntaPorEspecialidade(
                especialidade="Documentação (Audit/Docs)",
                pergunta_principal="Qual opção é mais fácil de documentar e rastrear?",
                sub_perguntas=[
                    "Qual opção mantém docs simples?",
                    "Qual requer mais diagramas/specs?",
                    "Qual sincroniza melhor com protocolo [SYNC]?"
                ],
                criterios_avaliacao=[
                    "Documentation complexity",
                    "[SYNC] tag compliance",
                    "Audit trail clarity"
                ],
                impactos_esperados=[
                    "Docs sync burden",
                    "Knowledge transfer ease",
                    "Regulatory compliance"
                ]
            ),

            "governanca": PerguntaPorEspecialidade(
                especialidade="Governança (Elo)",
                pergunta_principal="Qual opção alinha melhor stakeholders em decisão?",
                sub_perguntas=[
                    "Qual opção tem consensus melhor?",
                    "Qual opção mitiga conflito tech vs. finance?",
                    "Qual é mais fácil de reverter se falhar?"
                ],
                criterios_avaliacao=[
                    "Consensus level",
                    "Reversibility",
                    "Dependency clarity"
                ],
                impactos_esperados=[
                    "Stakeholder confidence",
                    "Decision stickiness",
                    "Pivot capability"
                ]
            ),

            "operacional": PerguntaPorEspecialidade(
                especialidade="Operacional (Planner)",
                pergunta_principal="Qual opção é mais acompanhável e controlável?",
                sub_perguntas=[
                    "Qual opção tem timeline mais claro?",
                    "Qual opção tem menos dependências críticas?",
                    "Qual opção permite incremental launches?"
                ],
                criterios_avaliacao=[
                    "Schedule clarity",
                    "Dependency complexity",
                    "Milestone definition"
                ],
                impactos_esperados=[
                    "Burndown stability",
                    "Risk trajectory",
                    "Escalation frequency"
                ]
            ),

            "conformidade": PerguntaPorEspecialidade(
                especialidade="Conformidade (Compliance)",
                pergunta_principal="Qual opção minimiza risco regulatório?",
                sub_perguntas=[
                    "Qual opção é mais auditável?",
                    "Qual opção cumpre com reqs crypto-financeiro?",
                    "Qual opção gera melhor audit trail?"
                ],
                criterios_avaliacao=[
                    "Audit trail completeness",
                    "Regulatory requirement coverage",
                    "Documentation standards"
                ],
                impactos_esperados=[
                    "Compliance risk level",
                    "Audit readiness",
                    "Regulatory approval ease"
                ]
            ),

            "estrategia": PerguntaPorEspecialidade(
                especialidade="Estratégia (Board Member)",
                pergunta_principal="Qual opção melhor se alinhas com visão de 5 anos?",
                sub_perguntas=[
                    "Qual opção oferece melhor opção estratégica futura?",
                    "Qual opção preserva máximo de flexibilidade?",
                    "Qual opção é mais resiliente em mudanças macro?"
                ],
                criterios_avaliacao=[
                    "Strategic alignment",
                    "Future optionality",
                    "Macro resilience"
                ],
                impactos_esperados=[
                    "Strategic positioning",
                    "Exit optionality",
                    "Pivot flexibility"
                ]
            ),
        }
    }

    @staticmethod
    def renderizar_pauta_reuniao(tipo_decisao: str) -> str:
        """Renderiza pauta de reunião estruturada por especialidade"""

        perguntas = TemplateReuniaoBoardMembros.PERGUNTAS_POR_ESPECIALIDADE.get(tipo_decisao, {})

        if not perguntas:
            return f"Tipo de decisão '{tipo_decisao}' não encontrado"

        md = []
        md.append("# 📋 PAUTA DE REUNIÃO — CICLO DE OPINIÕES\n")
        md.append(f"**Tipo de Decisão:** {tipo_decisao}\n")
        md.append(f"**Data/Hora:** {datetime.now().isoformat()}\n")
        md.append(f"**Total de Membros:** {len(perguntas)}\n")
        md.append(f"**Tempo Total:** ~65 minutos (4 min por membro)\n\n")

        md.append("---\n\n")
        md.append("## 🎯 SEQUÊNCIA DE OPINIÕES\n\n")

        ordem_apresentacao = [
            "executiva", "governanca", "produto", "financeira",
            "machine_learning", "infraestrutura_ml", "trading", "arquitetura",
            "dados", "implementacao", "qualidade", "risco",
            "documentacao", "operacional", "estrategia", "conformidade"
        ]

        for idx, especialidade in enumerate(ordem_apresentacao, 1):
            if especialidade not in perguntas:
                continue

            p = perguntas[especialidade]
            md.append(f"### {idx}. 💬 {p.especialidade}\n")
            md.append(f"**Pergunta Principal:** {p.pergunta_principal}\n\n")

            md.append("**Sub-Perguntas:**\n")
            for sub in p.sub_perguntas:
                md.append(f"  • {sub}\n")
            md.append("\n")

            md.append("**Critérios de Avaliação:**\n")
            for crit in p.criterios_avaliacao:
                md.append(f"  ✓ {crit}\n")
            md.append("\n")

            md.append("**Impactos Esperados:**\n")
            for imp in p.impactos_esperados:
                md.append(f"  📊 {imp}\n")
            md.append("\n---\n\n")

        return "".join(md)

    @staticmethod
    def template_formulario_opiniao(especialidade: str, tipo_decisao: str) -> Dict:
        """Retorna template de formulário para cada membro preencher"""

        perguntas = TemplateReuniaoBoardMembros.PERGUNTAS_POR_ESPECIALIDADE.get(tipo_decisao, {})
        p = perguntas.get(especialidade)

        if not p:
            return {}

        return {
            "especialidade": p.especialidade,
            "pergunta_principal": p.pergunta_principal,
            "sub_perguntas": p.sub_perguntas,
            "campos_resposta": {
                "posicao_final": {
                    "tipo": "enum",
                    "opcoes": ["FAVORÁVEL", "CONTRÁRIO", "NEUTRO", "CONDICIONAL"],
                    "descricao": "Sua posição final sobre a decisão"
                },
                "parecer_resumido": {
                    "tipo": "texto_longo",
                    "min_chars": 200,
                    "max_chars": 1000,
                    "descricao": "Resumo de sua análise (500 caracteres recomendado)"
                },
                "argumentos": {
                    "tipo": "lista_argumentos",
                    "formato": {"argumento": "...", "impacto": "..."},
                    "descricao": "Top 3 argumentos que fundamentam sua posição"
                },
                "prioridade": {
                    "tipo": "enum",
                    "opcoes": ["CRÍTICA", "ALTA", "MÉDIA", "BAIXA"],
                    "descricao": "Prioridade desta questão em sua especialidade"
                },
                "risco_apontado": {
                    "tipo": "texto_curto",
                    "descricao": "Qual é o maior risco que você enxerga?"
                },
                "observacoes": {
                    "tipo": "texto_livre",
                    "descricao": "Observações adicionais (opcional)"
                }
            }
        }


if __name__ == "__main__":
    template = TemplateReuniaoBoardMembros()

    # Exemplo: Renderizar pauta Decision #2
    pauta = template.renderizar_pauta_reuniao("ML_TRAINING_STRATEGY")
    print(pauta)

    # Salvar pauta em arquivo
    Path("reports").mkdir(exist_ok=True)
    with open("reports/pauta_decision_2.md", "w") as f:
        f.write(pauta)

    print("\n✅ Pauta salva em reports/pauta_decision_2.md")
