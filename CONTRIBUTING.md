# Guia de Contribuição

Obrigado por contribuir com o `crypto-futures-agent`.

## 🌐 Idioma do Projeto

- O idioma oficial deste projeto é **português**.
- Escreva documentação, comentários, mensagens de log e textos de interface em português.
- Use inglês apenas para termos técnicos consolidados (APIs, bibliotecas, protocolos e nomes próprios).

## ✅ Diretrizes Gerais

- Mantenha mudanças pequenas, focadas e alinhadas ao escopo solicitado.
- Não remova validações de risco existentes para contornar problemas.
- Não inclua segredos, credenciais ou chaves de API em código, logs ou documentação.
- Sempre que alterar lógica, execute os testes mais próximos da mudança.

## 🧪 Testes

- Rodar suíte completa: `pytest -q`
- Rodar teste específico (exemplo): `pytest -q tests/test_new_symbols.py`
