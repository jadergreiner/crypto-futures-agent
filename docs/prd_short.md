PRD — Agente Especialista em Posições Short de Futuros de Criptomoedas na Binance

Versão: 1.0
Data: 21‑03‑2026
Autor: Arquiteto de Soluções Sênior
Versão do Produto: 0.1.0

Referências Internas:

PRD original
 — documento base de requisitos para o autotrader forex.
[REGRAS_DE_NEGOCIO.md], [ARQUITETURA_ALVO.md], [ADRs.md] — definem regras de risco, arquiteturas e decisões adotadas no projeto.

Referências Externas (pesquisa de modelos ML):

A publicação da revista Applied Sciences propõe um sistema de negociação de portfólio de criptomoedas (CPTS) para o mercado de futuros da Binance. O modelo utiliza a técnica de Advantage Actor‑Critic (A2C) com análise de variância (ANOVA) para construir carteiras em múltiplos timeframes (10, 30, 60 min e diário). Nos testes com 18 criptomoedas negociadas na Binance (jan 2022–dez 2023) observaram‑se diferenças estatísticas entre operações de alta frequência e baixa frequência. Durante o treinamento, ativos de alta frequência renderam 16–17 %, enquanto na fase de teste as carteiras de baixa frequência obtiveram retorno médio de 43 %. O estudo também demonstra que utilizar RL em conjunto com análise estatística melhora a otimização das carteiras.
Pesquisa recente sobre Deep Reinforcement Learning para trading de criptomoedas evidencia o risco de backtest overfitting. Os autores propõem um teste de hipótese para detectar agentes superajustados e rejeitá‑los. Em um experimento com 10 criptomoedas (05/2022–06/2022) os agentes menos superajustados apresentaram retornos superiores à média de mercado e ao índice S&P DBM.
Um modelo híbrido LSTM + XGBoost para previsão de preços de criptomoedas mostrou que combinar a extração sequencial de características do LSTM com a capacidade do XGBoost de modelar relações não lineares melhora o desempenho. Avaliado em Bitcoin, Ethereum, Dogecoin e Litecoin, o híbrido superou modelos independentes e métodos tradicionais, com erro absoluto médio menor e maior adaptabilidade.
Artigo empírico comparando CNN‑LSTM, Temporal Convolutional Network e ARIMA para previsão da direção do preço do Bitcoin demonstrou que a combinação CNN–LSTM com seleção de características (Boruta) atingiu acurácia de 82,44 %. Backtests de estratégias long & short mostraram retorno anual acumulado de 6 654 % usando previsões de maior acurácia, reforçando o potencial dos modelos de deep learning quando associados a controle de risco.
Uma revisão sistemática publicada na Array evidencia que as arquiteturas RNN, LSTM, CNN e modelos híbridos estão na vanguarda da predição de mercado. A revisão destaca desafios como ruído nos dados, overfitting e falta de interpretabilidade, e salienta a necessidade de mecanismos de regularização e avaliação robusta.
Para gerenciamento de risco em trading algorítmico, sete estratégias são recomendadas: dimensionamento inteligente de posição, diversificação, stop‑loss, controle de drawdown, ajustes conforme volatilidade, controle de risco do modelo e monitoramento em tempo real.
Em outra pesquisa sobre otimização de portfólio com DRL, um agente behaviorally informed integra vieses como aversão à perda e excesso de confiança em um modelo actor–critic. O framework utiliza a rede TimesNet para prever regimes de mercado e alternar entre comportamentos. Esse agente obteve maior retorno ajustado ao risco do que carteiras Markowitz e RL neutro, reforçando que incorporar princípios de finanças comportamentais aumenta a robustez dos modelos.

1. Visão do Produto

Desenvolver um agente autônomo especializado em posições short para futuros de criptomoedas na Binance. O produto identifica, avalia e executa oportunidades de venda a descoberto em ativos de alta liquidez (BTCUSDT, ETHUSDT, etc.) utilizando técnicas avançadas de machine learning e deep reinforcement learning. Seu objetivo é capturar movimentos de queda preservando capital através de gestão de risco rigorosa e auditoria completa.

Diferenciais:

Foco em short: enquanto o PRD original cobre operações long e algoritmos híbridos, este agente é otimizado para posições vendidas, considerando custos de funding, alavancagem e peculiaridades das taxas de futuros.
Previsão temporal híbrida: incorpora modelos sequenciais (LSTM) e árvores de decisão (XGBoost) para prever direções de preço e volatilidade.
Reinforcement learning com ajuste de comportamento: usa algoritmos actor–critic (A2C/PPO) treinados em múltiplos timeframes e integra mecanismos de controle de overfitting e vieses comportamentais.
Gerenciamento de risco automatizado: aplica limites de exposição, stop‑loss, hard cap diário, controle de drawdown e kill switch de modelo. Usa dimensionamento de posição e diversificação conforme recomendações de best‑practice.
Compatível com arquitetura existente: reutiliza a infraestrutura do projeto (BaseAutoTrader, pipelines, auditoria), adaptando‑a ao ecossistema Binance e a contratos perpétuos.
2. Problema que Resolve
Dor do Trader Solução Proposta
Exposição excessiva a movimentos de alta: traders de criptomoedas podem perder oportunidades ao só negociar comprado. O agente short identifica tendências de queda e executa posições vendidas de forma sistemática, permitindo lucrar em mercados baixistas e proteger ganhos.
Volatilidade extrema e alavancagem: contratos futuros são altamente voláteis; posições vendidas podem ser liquidadas rapidamente se a gestão de risco falhar. Implementa hard caps diários e controle de drawdown; stop‑loss automático de 2× o risco inicial; dimensionamento de posição baseado na volatilidade atual.
Dificuldade de prever quedas: modelos tradicionais respondem mal a inversões rápidas de mercado. Combinação de LSTM (captura dependências de longo prazo) com XGBoost (captura relações não lineares e incorpora variáveis exógenas) melhora a acurácia das previsões.
Superajuste e perda de performance ao vivo: muitos bots apresentam excelentes resultados em backtest, mas falham ao vivo. Aplica teste de hipótese para detectar modelos superajustados e rejeitá‑los; utiliza shadow mode e kill switch já existentes para acompanhar o modelo sem impactar produção.
Falta de adaptação ao regime de mercado: comportamentos irracionais (aversão à perda, excesso de confiança) influenciam as quedas bruscas. Integra abordagens de DRL comportamental (BBAPT) que adaptam a política com base no regime de mercado e nos vieses observados.
3. Público‑Alvo
Usuário primário: trader individual (autor do projeto) com conta Futures na Binance.
Perfil técnico: programador Python com conhecimento de mercado de criptomoedas.
Ambiente: Windows 11 ou Linux (WSL), acesso à API da Binance Futures, operação 24/7.
4. Escopo do Produto
4.1 Ativos Suportados

Iniciar com 10 criptomoedas de alta liquidez na Binance Futures (BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT, DOGEUSDT, DOTUSDT, AVAXUSDT, LINKUSDT), podendo expandir. Cada ativo será configurado com múltiplos timeframes (5 min, 15 min, 1 h, diário) com base em resultados de pesquisa que mostraram diferença de performance entre frequências.

4.2 Estratégias de Operação
Estratégia Status Descrição
Short rules‑based Piloto Sinais gerados por regras técnicas (médias móveis, RSI, MACD). Atua somente na venda quando critérios de sobrecompra são atendidos.
Short ML (LSTM + XGBoost) Piloto Previsão de probabilidade de queda nos próximos n candles utilizando LSTM para séries temporais e XGBoost para variáveis adicionais (sentimento, funding rate, open interest).
Short RL (A2C/PPO) Pesquisa Agente actor–critic que aprende políticas de venda/fechamento a partir de estados que incluem OHLCV, funding, base, ordens em aberto e features geradas; inspirado no CPTS de A2C.
BBAPT Short (DRL comportamental) Pesquisa futura Extensão do DRL comportamental que incorpora vieses de aversão à perda e excesso de confiança; adapta posição de acordo com regimes de mercado previsos via TimesNet.
4.3 Exclusões de Escopo
Negociação de contratos long/short simultâneos: este agente foca exclusivamente em posições vendidas.
Integração com broker MT5: toda execução será via API Binance REST/websocket; o agente reutilizará a infraestrutura de gerenciamento de risco, mas não se conecta ao MetaTrader.
5. Requisitos Funcionais
5.1 Pipeline de Execução (ShortAutoTrader)
RF‑S01: O novo autotrader deve herdar de BaseAutoTrader e passar pelos 12 gates de risco existentes antes de enviar qualquer ordem de venda.
RF‑S02: Adicionar gate “Funding e Alavancagem”: verifica se o funding rate previsto nas próximas 8 h favorece posições vendidas (funding negativo ou neutro). Se funding positivo elevado (> 0,05 %) bloqueia abertura de short.
RF‑S03: Implementar controle de exposição específico: limite máximo de 3 posições short simultâneas por ativo e 6 por moeda base (equivalente ao limite long do PRD original).
RF‑S04: Adicionar verificação de base e term structure: impede short quando a base (diferença entre preço spot e futuro) é negativa, reduzindo risco de contango.
RF‑S05: Persistir todas as transições de estado no pipeline de sinais, indicando que se trata de uma posição short.
RF‑S06: Integrar stop‑loss automático ajustado para shorts: cut = entrada + 2 × (stop_loss − entrada), ativando fechamento imediato quando a perda exceder 2 × o risco inicial.
RF‑S07: Suporte ao shadow mode para o modelo de previsão: durante a fase de piloto, as decisões de short via ML/RL são monitoradas em paralelo sem enviar ordens reais, permitindo avaliar acurácia, retornos e falso‑positivo antes de liberar para produção.
5.2 Gerenciamento de Risco
RF‑S08: Dimensionamento dinâmico de posição baseado em volatilidade (ATR) e capital em risco: arriscar no máximo 1 % do saldo por operação, ajustando o tamanho do contrato conforme a distância ao stop.
RF‑S09: Hard cap diário de 3 ordens short por ativo por operador e limitação de drawdown diário em 5 % do saldo.
RF‑S10: Diversificação direcional: se > 80 % das posições totais estiverem na mesma direção (neste caso 100 % short), bloquear novas entradas.
RF‑S11: Monitoramento de volatilidade: em períodos de alta volatilidade (> 2 × a média de 30 dias), reduzir tamanho das posições pela metade.
RF‑S12: Controle de risco do modelo: rejeitar modelos com probabilidade de overfitting superior a 10 % conforme teste de hipótese; kill switch se concordância shadow < 50 %.
5.3 Machine Learning e Aprendizado
RF‑S13: Construir modelo híbrido LSTM + XGBoost para previsão de queda nos próximos k períodos.
Entrada LSTM: janelas de OHLCV normalizadas, indicadores técnicos (RSI, MACD), funding rate, open interest e volume de trades agressivos.
Entrada XGBoost: variáveis agregadas de sentimento (Twitter, Google Trends), dados macroeconômicos (CPI, FOMC), taxas de juros, volatilidade implícita e saídas da LSTM (estados ocultos).
Treinamento: janela de 2022–2025; validação walk‑forward; avaliação com MAPE e RMSE; meta de MAPE < 2 %.
RF‑S14: Desenvolver agente RL do tipo A2C ou PPO com reward baseado em P&L líquido, penalizando posições mantidas quando o funding favorece a compra. O agente usará múltiplos timeframes (10 min, 30 min, 60 min, diário), replicando a abordagem de A2C do estudo CPTS.
O estado do ambiente incluirá: retornos logarítmicos, indicadores técnicos, funding, base, índices de volatilidade (VIX cripto), posição atual e margin ratio.
A política será otimizada via policy gradient com entropia para estimular exploração.
RF‑S15: Adicionar camada de DRL comportamental (BBAPT) como pesquisa futura: integrar parâmetros de aversão à perda e excesso de confiança variáveis conforme regime de mercado previsto via TimesNet.
RF‑S16: Retreino incremental semanal, acionado quando: (i) o volume de novos episódios > 50; (ii) o Sharpe cair abaixo de 1,5; ou (iii) houver mudança significativa no regime de mercado.
6. Requisitos Não‑Funcionais
ID Requisito Meta
RNF‑S01 Segurança de contas Utilizar API keys com permissões restritas, armazenadas em variáveis de ambiente; sem gravação em código.
RNF‑S02 Confiabilidade 100 % das ordens devem passar pelos gates; falha em qualquer gate deve provocar fail‑closed.
RNF‑S03 Desempenho Ciclo de análise e decisão por ativo ≤ 20 s; latência de execução de ordem ≤ 300 ms.
RNF‑S04 Observabilidade Logs estruturados por operação com identificação de ativo, timestamp, timeframe, modelo utilizado e métricas de risco; alertas em < 60 s para eventos críticos (stop‑loss, falha de API).
RNF‑S05 Manutenibilidade Código modular, seguindo padrões do projeto original; documentação em português; cobertura de testes ≥ 30 %.
RNF‑S06 Regulamentação O agente deve impedir qualquer operação quando detetar que a jurisdição do usuário proíbe derivativos ou quando a Binance restringe posições para o país.
7. Arquitetura Técnica
7.1 Camadas
+----------------------------------------------+
| Entrada e Orquestração (ShortAutoTrader)     |
+----------------------------------------------+
| Camada de Previsão (LSTM+XGBoost)            |
|   -> extração de features temporais          |
|   -> modelagem de relação não linear         |
+----------------------------------------------+
| Camada de Decisão RL                         |
|   -> algoritmo A2C/PPO (ou BBAPT)            |
|   -> avaliação do estado e emissão de ação   |
+----------------------------------------------+
| Camada de Risco                              |
|   -> gates 1–12 + gates específicos (funding |
|      e base)                                 |
+----------------------------------------------+
| Camada de Execução Binance API               |
|   -> envio/cancelamento de ordens            |
|   -> sincronização de posições               |
+----------------------------------------------+
| Camada de Persistência                       |
|   -> SQLite ou PostgreSQL: sinais, ordens,   |
|      episódios, auditoria                    |
+----------------------------------------------+
| Camada de Monitoramento e Feedback           |
|   -> dashboards, alertas multi‑canal         |
|   -> *shadow mode*, retreino automático      |
+----------------------------------------------+
7.2 Tecnologias
Linguagem: Python 3.10+.
Bibliotecas ML: TensorFlow/Keras ou PyTorch para LSTM; XGBoost para booster; stable‑baselines3 para RL (PPO/A2C); TimesNet para previsão de regimes.
Dados: Binance REST/WebSocket API (dados de futuros), coletas complementares (Santiment, CryptoQuant) via APIs públicas.
Persistência: SQLite para protótipo; considerar PostgreSQL para produção de alto volume.
Orquestração: Herança de BaseAutoTrader; scripts BAT e serviços systemd para agendamento.
8. Métricas de Sucesso
Acurácia da Previsão (ML): MAPE < 2 % e RMSE < 0,01 no conjunto de validação.
Retorno Ajustado ao Risco: Sharpe Ratio > 1,5 e Sortino Ratio > 2,0 nos backtests.
Max Drawdown: ≤ 10 % em qualquer janela de 30 dias.
Taxa de Overfitting: < 10 % dos agentes rejeitados por teste de hipótese de overfitting.
Tempo Médio entre Stop‑Loss: > 5 h; indica que stop‑loss não está ocorrendo com frequência excessiva.
Concordância Shadow vs. Real: ≥ 60 % antes de promover o modelo para produção.
9. Roadmap
Fase Período Entregas
Fase 1 – Planejamento e Coleta de Dados Abr 2026 Configurar integração com API Binance; coletar dados históricos (2022–2025) de preços, volumes, funding e open interest; montar base de dados; definir requisitos legais e de compliance.
Fase 2 – Desenvolvimento do Modelo ML Mai–Jun 2026 Construir e treinar LSTM + XGBoost; implementar pipeline de features; validar previsões; iniciar shadow mode para short rules‑based.
Fase 3 – Agente RL Prototipo Jul–Set 2026 Implementar ambiente RL; treinar agente A2C/PPO com backtesting; aplicar teste de overfitting e validar retornos comparando com estratégia igual‑pesos.
Fase 4 – Integração com BaseAutoTrader Out 2026 Criar classe ShortAutoTrader derivada de BaseAutoTrader; implementar gates de funding/base; adicionar limites de exposição e stop‑loss; logs estruturados.
Fase 5 – Piloto em Shadow Mode Nov 2026–Jan 2027 Executar o agente em ambiente real com ordens virtuais; coletar métricas de acurácia, Sharpe, drawdown; ajustar parâmetros.
Fase 6 – Lançamento Controlado Fev 2027 Ativar ordens reais com limites reduzidos; monitorar continuamente; retreino incremental semanal; incorporar DRL comportamental se aplicável.
10. Riscos e Mitigações
Risco Severidade Mitigação
Mudança de regime de mercado e alta volatilidade Alta Monitorar regime via TimesNet e ajustar alocação; reduzir tamanho das posições em volatilidade anômala; retreino contínuo.
Funding desfavorável e custos ocultos Alta Gate de funding e base; evitar operar quando o funding rate positivo torna a posição short cara.
Dados incompletos ou atraso de API Média Redundância de fontes de dados; fallback via serviços externos (ex. CryptoQuant); logs de latência.
Superajuste de modelos Alta Aplicar testes de hipótese e rejeitar agentes superajustados; validar no shadow mode antes de ativar.
Risco regulatório Média Verificar restrições de derivativos para a jurisdição do usuário; bloquear operações em períodos de alta incerteza regulatória.
Liquidação forçada por alavancagem Alta Definir margem de segurança; limitar leverage < 5× por padrão; ativar cut‑loss e monitorar colateral.
11. Considerações Finais

Este PRD define um novo agente autônomo focado em posições short na Binance Futures, reutilizando a infraestrutura robusta do projeto Analista Forex e incorporando avanços recentes em machine learning e deep reinforcement learning. A integração de modelos híbridos (LSTM + XGBoost), agentes actor–critic com múltiplos timeframes e mecanismos de controle de overfitting aumenta a confiabilidade das previsões e a capacidade de capturar movimentos de queda. Ao mesmo tempo, a arquitetura mantém padrões rígidos de segurança, auditoria e gestão de risco, essenciais para operar em um mercado altamente volátil e alavancado.

Aviso: Este documento descreve um sistema de pesquisa e automação para fins educacionais e de teste. A negociação de criptomoedas envolve risco significativo e não é recomendada para menores. O projeto deve obedecer às leis e diretrizes aplicáveis e não constitui aconselhamento financeiro.
