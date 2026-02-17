# Instruções para o GitHub Copilot

Estas instruções orientam mudanças neste repositório `crypto-futures-agent`.

## Objetivo
- Priorizar segurança operacional, previsibilidade e rastreabilidade.
- Evitar mudanças amplas sem necessidade.
- Fazer correções na causa raiz, não apenas paliativos.

## Idioma
- Manter o idioma do projeto sempre em português.
- Escrever documentação, comentários, mensagens de log e textos de interface em português.
- Permitir termos técnicos em inglês apenas quando forem nomes próprios, APIs, bibliotecas ou padrões amplamente usados.

## Stack e organização
- Linguagem principal: Python.
- Módulos importantes:
  - `agent/`: lógica de RL, ambiente e reward.
  - `execution/`: execução de ordens.
  - `data/`: clientes e coleta de dados (Binance, macro, sentimento).
  - `risk/` e `monitoring/`: controles de risco e monitoramento.
  - `backtest/`: backtesting e walk-forward.
  - `playbooks/`: regras por símbolo.
  - `tests/`: testes automatizados.

## Regras de implementação
- Manter mudanças pequenas, focadas e compatíveis com o estilo existente.
- Não renomear APIs públicas, arquivos ou funções sem necessidade explícita.
- Não adicionar dependências novas se houver solução local simples.
- Não inserir credenciais, chaves de API ou segredos em código, logs ou docs.
- Evitar hardcode de parâmetros sensíveis de risco; preferir `config/`.
- Preservar compatibilidade entre modos `paper` e `live`.

## Regras de domínio (trading/risk)
- Nunca remover validações de risco existentes para “fazer funcionar”.
- Qualquer alteração em sizing, alavancagem, stop, liquidação, margem ou reward deve:
  - manter comportamento seguro por padrão;
  - ter fallback conservador em caso de erro/ausência de dados;
  - registrar decisão relevante de forma auditável.
- Em caso de dúvida, preferir bloquear operação a assumir risco extra.

## Logs e observabilidade
- Reutilizar o padrão de logging existente em `monitoring/`.
- Logs devem ser úteis para diagnóstico e curtos o suficiente para operação contínua.
- Não gerar ruído excessivo em loops de alta frequência.

## Testes e validação
- Sempre que alterar lógica, rodar ao menos os testes mais próximos do escopo alterado.
- Quando aplicável, usar:
  - `pytest -q`
  - ou teste específico, por exemplo: `pytest -q tests/test_new_symbols.py`
- Não corrigir testes não relacionados sem solicitação explícita.

## Estilo de código
- Seguir padrões já usados no repositório (nomes, imports, estrutura).
- Evitar comentários óbvios e variáveis de uma letra.
- Preferir funções pequenas e com responsabilidade clara.
- Tratar erros de integração externa com mensagens úteis e fallback seguro.

## Documentação
- Atualizar documentação apenas quando houver impacto real de comportamento/configuração.
- Para mudanças relevantes em risco/reward/execução, considerar atualizar arquivos em `docs/`.

## O que evitar
- Não criar funcionalidades “nice to have” fora do pedido.
- Não alterar arquitetura inteira para resolver problema local.
- Não executar ações destrutivas (ex.: apagar dados, cancelar ordens em massa) sem solicitação explícita.
