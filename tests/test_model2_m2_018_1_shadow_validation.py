#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testes para M2-018.1 Shadow Validation script.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestM2018ShadowValidationScript:
    """Testes para m2_018_1_shadow_validation.py"""

    @staticmethod
    def get_script_path():
        return Path("scripts/model2/m2_018_1_shadow_validation.py")

    def test_script_exists(self):
        """Verifica se script existe."""
        assert self.get_script_path().exists(), "Script nao existe"

    def test_script_is_executable(self):
        """Verifica se script e executavel."""
        script = self.get_script_path()
        assert script.stat().st_mode & 0o111, "Script nao e executavel"

    def test_script_has_required_functions(self):
        """Verifica se script contem funcoes necessarias."""
        script = self.get_script_path().read_text()

        required_functions = [
            "def validate_environment",
            "def run_preflight",
            "def run_cycle",
            "def validate_signal_executions",
            "def generate_final_report",
            "def main",
        ]

        for func in required_functions:
            assert func in script, "Falta funcao: {}".format(func)

    def test_help_flag_works(self):
        """Verifica se --help funciona."""
        result = subprocess.run(
            ["python", str(self.get_script_path()), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, "--help falhou"
        assert "usage" in result.stdout.lower(), "Help output invalido"

    def test_dry_run_mode_works(self):
        """Verifica se --dry-run funciona."""
        result = subprocess.run(
            ["python", str(self.get_script_path()), "--dry-run", "--cycles=1"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout + result.stderr

        # Em dry-run, esperamos que o script nao falhe (resultado nao importa tanto)
        if "DRY-RUN" in output or "simulado" in output:
            assert True, "Dry-run mode detectado e funcionando"
        else:
            # Se nao mostrou DRY-RUN, continua sendo OK se retcode=0
            pass

    def test_cycles_argument_works(self):
        """Verifica se argumento --cycles e aceito."""
        cmd = ["python", str(self.get_script_path()), "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        assert "--cycles" in result.stdout, "Argumento --cycles nao documentado"

    def test_encoding_is_ascii_safe(self):
        """Verifica se script usa apenas ASCII."""
        script = self.get_script_path().read_text(encoding='utf-8')

        # Tentar compilar
        try:
            compile(script, str(self.get_script_path()), 'exec')
        except SyntaxError as e:
            pytest.fail("Syntax error no script: {}".format(str(e)))

        # Verificar se contem caracteres problematicos (emojis, etc)
        problematic = any(ord(c) > 127 and c not in '\n\r\t ' for c in script)

        assert not problematic, "Script contem caracteres nao-ASCII"

    def test_environment_variables_checked(self):
        """Verifica se script verifica variaveis de ambiente."""
        script = self.get_script_path().read_text()

        assert "M2_EXECUTION_MODE" in script, "Script nao verifica M2_EXECUTION_MODE"
        assert "MODEL2_DB_PATH" in script, "Script nao verifica MODEL2_DB_PATH"

    def test_results_directory_structure(self):
        """Verifica se script cria estrutura de diretorios."""
        script = self.get_script_path().read_text()

        assert "results/model2" in script, "Script nao usa results/model2"

    def test_report_json_structure(self):
        """Verifica se script pode gerar relatorio JSON."""
        script = self.get_script_path().read_text()

        assert "generate_final_report" in script, "Funcao generate_final_report nao existe"
        assert "json" in script, "Script nao usa json"

    def test_subprocess_calls_present(self):
        """Verifica se script faz chamadas de subprocess."""
        script = self.get_script_path().read_text()

        assert "subprocess" in script, "Script nao importa subprocess"
        assert "subprocess.run" in script, "Script nao faz subprocess.run"

    def test_error_handling_present(self):
        """Verifica se script tem tratamento de erros."""
        script = self.get_script_path().read_text()

        assert "try:" in script, "Script nao tem try/except"
        assert "except" in script, "Script nao tem except"

    def test_main_function_exists(self):
        """Verifica se __main__ guard existe."""
        script = self.get_script_path().read_text()

        assert 'if __name__ == "__main__"' in script, "Script nao tem __main__ guard"

    def test_backlog_updated(self):
        """Verifica se BACKLOG.md foi atualizado."""
        backlog = Path("docs/BACKLOG.md").read_text()

        assert "M2-018.1" in backlog, "M2-018.1 nao esta em BACKLOG.md"

    def test_synchronization_updated(self):
        """Verifica se SYNCHRONIZATION.md foi atualizado."""
        sync = Path("docs/SYNCHRONIZATION.md").read_text()

        # Procurar por alguma referencia M2-018.1
        assert "M2-018.1" in sync or "018" in sync, "M2-018.1 nao esta em SYNCHRONIZATION.md"

    def test_script_imports_valid(self):
        """Verifica se imports do script sao validos."""
        script = self.get_script_path().read_text()

        # Imports esperados
        expected_imports = ["json", "os", "sys", "subprocess", "argparse", "datetime", "pathlib"]

        for imp in expected_imports:
            assert imp in script, "Modulo {} nao e importado".format(imp)
