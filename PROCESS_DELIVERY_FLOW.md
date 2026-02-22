# Fluxo de Entrega de Pacotes - crypto-futures-agent

Este documento descreve o processo estratégico, tático e operacional para a entrega de pacotes (funcionalidades/correções) aos desenvolvedores e, consequentemente, ao projeto.

## 1. Nível Estratégico (O "Quê" e o "Porquê")
*Foco: Visão de longo prazo, objetivos de negócio e alinhamento com o roadmap.*

*   **Definição de Requisitos de Alto Nível:** O gestor estratégico identifica necessidades baseadas no mercado de cripto (futuros), feedback de usuários ou lacunas tecnológicas.
*   **Análise de Viabilidade e Valor:** Cada "pacote" de trabalho é avaliado quanto ao seu impacto no ROI (Retorno sobre Investimento) e riscos sistêmicos (ex: segurança de chaves API).
*   **Priorização no Roadmap:** O pacote é inserido no `ROADMAP.md` com uma estimativa de cronograma macro.
*   **Literatura:** Baseado em *Strategic Management* (Ansoff, Porter) e *Value-Driven Development*.

## 2. Nível Tático (O "Como" e o "Quando")
*Foco: Planejamento de releases, arquitetura e organização das tarefas.*

*   **Quebra de Épicos em User Stories:** O pacote estratégico é decomposto em tarefas menores no `backlog/`.
*   **Design de Arquitetura:** Definição de como a nova funcionalidade se integra ao `core/` ou `agent/` sem quebrar o `ARCHITECTURE_DIAGRAM.md`.
*   **Planejamento de Sprint/Ciclo:** Atribuição de tarefas a desenvolvedores específicos e definição de prazos intermediários.
*   **Gestão de Riscos:** Definição de planos de contingência e testes de integração necessários (conforme `BEST_PRACTICES.md`).
*   **Literatura:** Baseado em *Agile/Scrum* (Schwaber, Sutherland) e *Software Architecture* (Clean Architecture, DDD).

## 3. Nível Operacional (A Execução)
*Foco: Codificação, testes, revisão e entrega técnica.*

*   **Desenvolvimento (Coding):** O desenvolvedor segue a `COMMIT_MESSAGE_POLICY.md` e os padrões do projeto.
*   **Testes Automatizados:** Criação de testes unitários e de integração (ex: `test_*.py`).
*   **Code Review (Pull Requests):** Submissão do código para revisão por pares ou pelo gestor, garantindo qualidade e segurança.
*   **CI/CD e Validação:** Execução automática de linters (`fix_all_markdown_lint.py`) e validação de integridade.
*   **Documentação:** Atualização de READMEs, `CHANGELOG.md` e atas de reunião (`ATA_REUNIAO_*.md`).
*   **Entrega (Merge):** O pacote é oficialmente "entregue" ao ramo principal (`main`).
*   **Literatura:** Baseado em *DevOps* (The Phoenix Project, Accelerate) e *GitHub Flow*.

---
*Assinado: Gestor Estratégico (@jadergreiner / @copilot)*