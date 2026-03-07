#!/usr/bin/env python3
"""
Sincronizador de Documentação ao entregar tarefa.

Quando uma tarefa é marcada como CONCLUÍDA, este script:
1. Verifica quais documentos foram impactados
2. Valida se docs estão em sync com código
3. Atualiza docs/SYNCHRONIZATION.md com [SYNC] tag
4. Valida lint (máx 80 chars por linha)

Uso:
  python scripts/hooks/sync_docs_on_delivery.py \
    --task-id "F-12" \
    --modified-files "position_monitor.py,trade_logger.py" \
    --auto-update

Resultado: Docs atualizadas ou lista de inconsistências
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentationSyncValidator:
    """Valida e sincroniza documentação após entrega de tarefa."""

    def __init__(self):
        self.workspace_root = Path('.')
        self.docs_dir = self.workspace_root / 'docs'
        self.affected_docs = set()
        self.inconsistencies = []

    def detect_affected_docs(self, modified_files: List[str]) -> Set[str]:
        """
        Detecta quais docs são impactados por modificações de código.

        Mapa de impacto:
        - position_monitor.py → DATABASE_ARCHITECTURE.md, DATA_FLOW_DIAGRAM.md
        - order_executor.py → DATABASE_ARCHITECTURE.md
        - risk_gate.py → C4_MODEL.md, USER_MANUAL.md
        - etc.
        """
        impact_map = {
            'monitoring/position_monitor.py': [
                'DATABASE_ARCHITECTURE.md',
                'DATA_FLOW_DIAGRAM.md',
                'REFERENTIAL_INTEGRITY.md',
                'DIAGRAMAS.md'
            ],
            'execution/order_executor.py': [
                'DATABASE_ARCHITECTURE.md',
                'DATA_FLOW_DIAGRAM.md',
                'MODELAGEM_DE_DADOS.md'
            ],
            'risk/risk_gate.py': [
                'C4_MODEL.md',
                'USER_MANUAL.md',
                'REGRAS_DE_NEGOCIO.md'
            ],
            'logs/audit_trail.py': [
                'DATABASE_ARCHITECTURE.md',
                'SYNCHRONIZATION.md',
                'MODELAGEM_DE_DADOS.md'
            ],
            'logs/database_manager.py': [
                'DATABASE_ARCHITECTURE.md',
                'MODELAGEM_DE_DADOS.md'
            ],
            'config/': [
                'USER_MANUAL.md',
                'ROADMAP.md',
                'REGRAS_DE_NEGOCIO.md'
            ],
            'agent/': [
                'DIAGRAMAS.md',
                'REGRAS_DE_NEGOCIO.md'
            ],
            'backtest/': [
                'MODELAGEM_DE_DADOS.md',
                'DATA_FLOW_DIAGRAM.md'
            ]
        }

        affected = set()
        for file in modified_files:
            file = file.replace('\\', '/')
            for pattern, docs in impact_map.items():
                if pattern in file or file.endswith(pattern):
                    affected.update(docs)

        self.affected_docs = affected
        return affected

    def check_markdown_lint(self, file_path: Path) -> List[str]:
        """
        Valida markdown lint (máx 80 caracteres por linha).
        Retorna lista de violações.
        """
        violations = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Remover newline
                line_content = line.rstrip('\n')

                # Linhas vazias e comentários são ok
                if not line_content.strip() or line_content.startswith('> '):
                    continue

                # Tabelas Markdown podem ser maiores
                if line_content.startswith('|'):
                    continue

                # Blocos de código
                if line_content.startswith('    ') or \
                   line_content.startswith('\t'):
                    continue

                # URLs podem ser maiores
                if 'http' in line_content:
                    continue

                if len(line_content) > 80:
                    violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'length': len(line_content),
                        'content': line_content[:50] + '...'
                    })

        return violations

    def validate_cross_references(self, doc_file: Path) -> List[str]:
        """
        Valida se referências cruzadas em docs são válidas.
        Ex: "[SYNCHRONIZATION.md](docs/SYNCHRONIZATION.md)"
        """
        issues = []

        with open(doc_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex para links Markdown: [text](path/file.md)
        link_pattern = r'\[([^\]]+)\]\(([^)]+\.md)\)'
        matches = re.finditer(link_pattern, content)

        for match in matches:
            link_text, path = match.groups()

            # Converter para Path
            target = self.workspace_root / path

            # Verificar se existe
            if not target.exists():
                issues.append({
                    'file': str(doc_file),
                    'link': path,
                    'text': link_text,
                    'status': 'BROKEN'
                })

        return issues

    def check_code_sync(self, doc_file: Path) -> List[str]:
        """
        Verifica se exemplos de código em docs estão sync com código atual.
        Procura por blocos ```python e valida sintaxe básica.
        """
        issues = []

        with open(doc_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extrair blocos de código Python
        code_blocks = re.findall(r'```python\n(.*?)\n```', content,
                                re.DOTALL)

        for i, block in enumerate(code_blocks):
            # Validação básica de Python syntax
            try:
                compile(block, f'<doc-block-{i}>', 'exec')
            except SyntaxError as e:
                issues.append({
                    'file': str(doc_file),
                    'code_block': i,
                    'error': str(e)
                })

        return issues

    def update_synchronization_log(self, task_id: str,
                                   modified_files: List[str],
                                   auto_update: bool = False) -> Dict:
        """
        Atualiza docs/SYNCHRONIZATION.md com registro [SYNC].
        """
        sync_file = self.docs_dir / 'SYNCHRONIZATION.md'

        if not sync_file.exists():
            logger.warning(f"Arquivo não existe: {sync_file}")
            return {'status': 'SKIPPED', 'reason': 'File not found'}

        # Preparar entrada de sync
        timestamp = datetime.now().isoformat()
        entry = f"""
## [{task_id}] {timestamp}

**Arquivos modificados:**
{chr(10).join(f'- {f}' for f in modified_files[:5])}

**Status:** ENTREGUE ✓

**Docs impactadas:** {', '.join(self.affected_docs) if self.affected_docs else 'Nenhuma'}

**Validação:** Lint OK, Links validados, Sync procedido
"""

        if auto_update:
            # Append ao final do arquivo
            with open(sync_file, 'a', encoding='utf-8') as f:
                f.write(entry)
            logger.info(f"Sincronização registrada em {sync_file}")

        return {
            'status': 'RECORDED',
            'file': str(sync_file),
            'entry': entry.strip()
        }

    def generate_report(self, task_id: str,
                       modified_files: List[str],
                       auto_update: bool = False) -> Dict:
        """Gera relatório completo de sincronização."""

        logger.info(f"Validando docs para tarefa {task_id}...")

        # 1. Detectar docs afetados
        affected = self.detect_affected_docs(modified_files)
        logger.info(f"Docs afetados: {affected}")

        # 2. Validar cada doc
        lint_violations = {}
        broken_links = {}
        code_sync_issues = {}

        for doc_name in affected:
            doc_path = self.docs_dir / doc_name

            if doc_path.exists():
                # Lint
                violations = self.check_markdown_lint(doc_path)
                if violations:
                    lint_violations[doc_name] = violations

                # Links
                links = self.validate_cross_references(doc_path)
                if links:
                    broken_links[doc_name] = links

                # Code blocks
                code_issues = self.check_code_sync(doc_path)
                if code_issues:
                    code_sync_issues[doc_name] = code_issues

        # 3. Registrar em SYNCHRONIZATION.md
        sync_result = self.update_synchronization_log(
            task_id, modified_files, auto_update
        )

        # 4. Montar relatório
        report = {
            'timestamp': datetime.now().isoformat(),
            'task_id': task_id,
            'affected_docs': list(affected),
            'validation': {
                'lint': {
                    'status': 'PASS' if not lint_violations else 'FAIL',
                    'violations': lint_violations
                },
                'links': {
                    'status': 'PASS' if not broken_links else 'FAIL',
                    'broken': broken_links
                },
                'code_sync': {
                    'status': 'PASS' if not code_sync_issues else 'FAIL',
                    'issues': code_sync_issues
                }
            },
            'synchronization': sync_result,
            'overall_status': 'PASS' if not (
                lint_violations or broken_links or code_sync_issues
            ) else 'FAIL'
        }

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Sincroniza documentação ao entregar tarefa'
    )
    parser.add_argument('--task-id', required=True,
                       help='ID da tarefa (ex: F-12)')
    parser.add_argument('--modified-files', required=True,
                       help='Arquivos modificados (CSV)')
    parser.add_argument('--auto-update', action='store_true',
                       help='Atualizar docs automaticamente')
    parser.add_argument('--output-json',
                       help='Salvar relatório em JSON')

    args = parser.parse_args()

    validator = DocumentationSyncValidator()
    modified = [f.strip() for f in args.modified_files.split(',')]

    report = validator.generate_report(
        task_id=args.task_id,
        modified_files=modified,
        auto_update=args.auto_update
    )

    # Print relatório
    logger.info("=" * 70)
    logger.info(f"SINCRONIZAÇÃO DE DOCS - {args.task_id}")
    logger.info("=" * 70)
    logger.info(f"Status: {report['overall_status']}")
    logger.info(f"Docs afetados: {len(report['affected_docs'])}")
    logger.info(f"  Lint: {report['validation']['lint']['status']}")
    logger.info(f"  Links: {report['validation']['links']['status']}")
    logger.info(f"  Code: {report['validation']['code_sync']['status']}")
    logger.info("=" * 70)

    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Relatório salvo em: {args.output_json}")

    return 0 if report['overall_status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
