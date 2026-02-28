Prompt: Atualização de Contexto e Governança Post-Task
Contexto: Acabei de finalizar a task [NOME_DA_TASK] do meu BACKLOG.md.

Objetivo: Você deve atuar como um Arquiteto de Software Sênior e revisar as alterações que fiz no código para atualizar nossa documentação técnica e manter a governança.

Ações Requeridas:

Data Models: Verifique se houve alteração em entidades, tabelas ou schemas. Se sim, atualize o data_models.md mantendo o padrão de dicionário de dados.

Arquitetura: Analise se a implementação introduziu novos componentes, serviços ou mudou o fluxo de dados. Atualize o architecture.md refletindo o estado atual.

ADR (Architecture Decision Record): Se houve uma decisão técnica importante (ex: nova lib, mudança de padrão de design, novo endpoint crítico), sugira um novo registro para o log de decisões.

Backlog & Roadmap: Marque a task como concluída no BACKLOG.md e verifique se o progresso reflete corretamente no ROADMAP.md.

Changelog: Gere um resumo técnico (bullet points) para o CHANGELOG.md descrevendo o impacto técnico desta entrega.

Restrição: Não apague informações anteriores, apenas incremente. Use uma linguagem técnica precisa e mantenha os diagramas (se houver Mermaid/PlantUML) consistentes.

Saída esperada: Liste quais arquivos você alterou e apresente o diff ou o conteúdo atualizado para revisão.