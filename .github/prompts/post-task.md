2. Prompt Otimizado para Copilot (Foco em Python)
Copie e use este prompt para garantir que o Copilot respeite as boas práticas de engenharia Python ao finalizar uma task:

Contexto: Finalizei a task [NOME_DA_TASK] em Python.

Ações de Arquiteto:

Code Review Interno: Verifique se segui a PEP 8 e se usei Type Hints em todas as novas funções/classes.

Data Models: Se alterei modelos SQLAlchemy, Django ORM ou classes Pydantic, atualize o data_models.md com os novos campos e tipos.

Arquitetura (Imports): Verifique se não criei importações circulares ou violei camadas (ex: lógica de negócio dentro de uma rota FastAPI/Flask). Atualize o architecture.md.

Testes: Garanta que a task incluiu testes em pytest. Se não, sugira os casos de teste básicos.

Backlog & Docs: Marque a task no BACKLOG.md e atualize o ROADMAP.md. Gere o registro no CHANGELOG.md focando no impacto técnico.

Saída: Apresente o resumo das alterações nos arquivos de documentação e valide se a estrutura do código está "Pythonic".