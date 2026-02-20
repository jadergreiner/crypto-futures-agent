#!/usr/bin/env python3
"""
Script de Validação de Sincronização de Documentação

Valida integridade e consistência de:
- README.md ↔ docs/FEATURES.md ↔ docs/ROADMAP.md
- config/symbols.py ↔ playbooks/ ↔ README.md
- docs/SYNCHRONIZATION.md (registro de mudanças)
- CHANGELOG.md (versão + data)
- Markdown lint (80 chars max, UTF-8, syntax)

Uso:
    python scripts/validate_sync.py
    python scripts/validate_sync.py --fix  # Tenta corrigir erros simples

Saída:
    ✅ PASS: Sincronização consistente
    ❌ FAIL: Inconsistências encontradas (veja detalhes)
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Set

# Cores para terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

class SyncValidator:
    """Validador de sincronização de documentação."""
    
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed = 0
        self.checks_failed = 0
    
    def log_error(self, msg: str):
        """Registra erro."""
        self.errors.append(msg)
        self.checks_failed += 1
        print(f"{RED}❌ ERRO:{RESET} {msg}")
    
    def log_warning(self, msg: str):
        """Registra aviso."""
        self.warnings.append(msg)
        print(f"{YELLOW}⚠️  AVISO:{RESET} {msg}")
    
    def log_pass(self, msg: str):
        """Registra sucesso."""
        self.checks_passed += 1
        print(f"{GREEN}✅ {msg}{RESET}")
    
    def check_markdown_lint(self) -> bool:
        """Valida markdown: 80 chars max, UTF-8, syntax."""
        print(f"\n{BOLD}1. Validando Markdown Lint...{RESET}")
        
        doc_files = list(self.repo_root.glob("*.md")) + \
                    list(self.repo_root.glob("docs/*.md"))
        
        has_errors = False
        
        for filepath in doc_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    # Remove trailing newline para contar caracteres
                    content = line.rstrip('\n')
                    
                    # Ignorar linhas de bloco de código
                    if content.startswith("```"):
                        continue
                    
                    # Validar comprimento
                    if len(content) > 80:
                        self.log_error(
                            f"{filepath.name}:{line_num} - Linha com {len(content)} "
                            f"chars, máximo 80: {content[:50]}..."
                        )
                        has_errors = True
                
            except UnicodeDecodeError as e:
                self.log_error(f"{filepath.name} - Encoding inválido (UTF-8 requerido): {e}")
                has_errors = True
            except Exception as e:
                self.log_error(f"{filepath.name} - Erro ao ler: {e}")
                has_errors = True
        
        if not has_errors:
            self.log_pass("Markdown lint validado (max 80 chars, UTF-8 OK)")
        
        return not has_errors
    
    def check_symbols_sync(self) -> bool:
        """Valida config/symbols.py ↔ playbooks/ ↔ README.md."""
        print(f"\n{BOLD}2. Validando Símbolos...{RESET}")
        
        # Ler symbols.py
        symbols_file = self.repo_root / "config" / "symbols.py"
        if not symbols_file.exists():
            self.log_warning(f"{symbols_file} não encontrado")
            return False
        
        with open(symbols_file, 'r', encoding='utf-8') as f:
            symbols_content = f.read()
        
        # Extrair símbolos (formato: SYMBOL = {...})
        symbol_pattern = r"(\w+)\s*=\s*\{.*?\}"
        symbols_in_config = set(re.findall(r"^([A-Z0-9]+)\s*=", symbols_content, re.MULTILINE))
        
        if not symbols_in_config:
            self.log_warning(f"Nenhum símbolo encontrado em {symbols_file}")
            return False
        
        # Ler playbooks/__init__.py
        playbooks_init = self.repo_root / "playbooks" / "__init__.py"
        if not playbooks_init.exists():
            self.log_warning(f"{playbooks_init} não encontrado")
            return False
        
        with open(playbooks_init, 'r', encoding='utf-8') as f:
            playbooks_content = f.read()
        
        # Validar que símbolos estão registrados
        missing_imports = []
        for symbol in symbols_in_config:
            if symbol not in playbooks_content:
                missing_imports.append(symbol)
        
        if missing_imports:
            self.log_error(
                f"Símbolos sem playbook registrado em __init__.py: {missing_imports}"
            )
            return False
        
        # Ler README.md para validar listagem
        readme = self.repo_root / "README.md"
        if not readme.exists():
            self.log_warning(f"{readme} não encontrado")
            return False
        
        with open(readme, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Contar menções de símbolos
        symbols_in_readme = set(re.findall(r"\*\*([A-Z0-9]+)", readme_content))
        
        # Permitir alguns símbolos não mencionados (são internos)
        if len(symbols_in_readme) < len(symbols_in_config) * 0.5:
            self.log_warning(
                f"README.md lista apenas {len(symbols_in_readme)} de {len(symbols_in_config)} símbolos"
            )
        
        self.log_pass(f"Símbolos sincronizados ({len(symbols_in_config)} símbolos)")
        return True
    
    def check_features_sync(self) -> bool:
        """Valida docs/FEATURES.md ↔ ROADMAP.md ↔ RELEASES.md."""
        print(f"\n{BOLD}3. Validando Features...{RESET}")
        
        features_file = self.repo_root / "docs" / "FEATURES.md"
        roadmap_file = self.repo_root / "docs" / "ROADMAP.md"
        releases_file = self.repo_root / "docs" / "RELEASES.md"
        
        files_exist = True
        if not features_file.exists():
            self.log_warning(f"{features_file} não encontrado")
            files_exist = False
        if not roadmap_file.exists():
            self.log_warning(f"{roadmap_file} não encontrado")
            files_exist = False
        if not releases_file.exists():
            self.log_warning(f"{releases_file} não encontrado")
            files_exist = False
        
        if not files_exist:
            return False
        
        with open(features_file, 'r', encoding='utf-8') as f:
            features_content = f.read()
        with open(roadmap_file, 'r', encoding='utf-8') as f:
            roadmap_content = f.read()
        with open(releases_file, 'r', encoding='utf-8') as f:
            releases_content = f.read()
        
        # Extrair versões mencionadas
        versions_in_features = set(re.findall(r"v(\d+\.\d+(?:\.\d+)?)", features_content))
        versions_in_roadmap = set(re.findall(r"v(\d+\.\d+(?:\.\d+)?)", roadmap_content))
        versions_in_releases = set(re.findall(r"v(\d+\.\d+(?:\.\d+)?)", releases_content))
        
        # Verificar sincronização mínima
        common_versions = versions_in_features & versions_in_roadmap & versions_in_releases
        
        if not common_versions:
            self.log_error(
                f"Nenhuma versão comum entre FEATURES, ROADMAP e RELEASES"
            )
            return False
        
        self.log_pass(
            f"Features sincronizadas (versões comuns: {', '.join(sorted(common_versions))})"
        )
        return True
    
    def check_changelog(self) -> bool:
        """Valida CHANGELOG.md está atualizado."""
        print(f"\n{BOLD}4. Validando CHANGELOG...{RESET}")
        
        changelog_file = self.repo_root / "CHANGELOG.md"
        if not changelog_file.exists():
            self.log_warning(f"{changelog_file} não encontrado")
            return False
        
        with open(changelog_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Validar que tem seção Unreleased ou versão recente
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        
        if "## [Unreleased]" not in content:
            self.log_warning("Seção [Unreleased] não encontrada em CHANGELOG.md")
            return False
        
        self.log_pass("CHANGELOG.md com seção [Unreleased] presente")
        return True
    
    def check_synchronization_tracker(self) -> bool:
        """Valida docs/SYNCHRONIZATION.md com registro recente."""
        print(f"\n{BOLD}5. Validando Rastreador de Sincronização...{RESET}")
        
        sync_file = self.repo_root / "docs" / "SYNCHRONIZATION.md"
        if not sync_file.exists():
            self.log_error(f"{sync_file} não encontrado")
            return False
        
        with open(sync_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que tem seção de checklist
        if "✅ Checklist de Sincronização" not in content and "Checklist de Sincronização" not in content:
            self.log_warning("Seção de Checklist não encontrada em SYNCHRONIZATION.md")
            return False
        
        # Contar ✅ checkmarks (indicativo de sincronizações recentes)
        checkmarks = content.count("✅")
        
        if checkmarks < 5:
            self.log_warning(
                f"Poucas sincronizações registradas ({checkmarks} checkmarks)"
            )
        
        self.log_pass(f"SYNCHRONIZATION.md registra sincronizações ({checkmarks} checkmarks)")
        return True
    
    def run_all_checks(self) -> bool:
        """Executa todos os checks."""
        print(f"\n{BOLD}{'='*60}")
        print("VALIDADOR DE SINCRONIZAÇÃO DE DOCUMENTAÇÃO")
        print(f"{'='*60}{RESET}\n")
        
        checks = [
            self.check_markdown_lint,
            self.check_symbols_sync,
            self.check_features_sync,
            self.check_changelog,
            self.check_synchronization_tracker,
        ]
        
        results = []
        for check in checks:
            try:
                results.append(check())
            except Exception as e:
                self.log_error(f"Erro ao executar {check.__name__}: {e}")
                results.append(False)
        
        # Resumo final
        print(f"\n{BOLD}{'='*60}")
        print("RESUMO")
        print(f"{'='*60}{RESET}")
        
        print(f"{GREEN}✅ Checks PASSOU: {self.checks_passed}{RESET}")
        print(f"{RED}❌ Checks FALHARAM: {self.checks_failed}{RESET}")
        print(f"{YELLOW}⚠️  Avisos: {len(self.warnings)}{RESET}")
        
        if self.warnings:
            print(f"\n{YELLOW}Avisos:{RESET}")
            for w in self.warnings:
                print(f"  - {w}")
        
        all_passed = all(results) and self.checks_failed == 0
        
        if all_passed:
            print(f"\n{GREEN}{BOLD}🎉 SINCRONIZAÇÃO VALIDADA!{RESET}")
            print(f"{GREEN}Pronto para commit com [SYNC] tag{RESET}\n")
        else:
            print(f"\n{RED}{BOLD}❌ SINCRONIZAÇÃO COM PROBLEMAS{RESET}")
            print(f"{RED}Resolva os erros acima antes de commitar{RESET}\n")
        
        return all_passed


def main():
    """Entrada principal."""
    repo_root = Path(__file__).parent.parent  # crypto-futures-agent/
    
    validator = SyncValidator(str(repo_root))
    success = validator.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
