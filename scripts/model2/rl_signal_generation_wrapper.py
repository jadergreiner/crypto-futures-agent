"""Wrapper para RL Signal Generation na pipeline diária."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_rl_signal_generation(
    *,
    model2_db_path: Path | str,
    timeframe: str = "H4",
    symbols: list[str] | None = None,
    ppo_checkpoint: Path | str | None = None,
    dry_run: bool = False,
    output_dir: Path | str | None = None,
) -> Dict[str, Any]:
    """
    Executar geração de sinais com suporte RL.

    Usa subprocess para isolar dependências de stable_baselines3.

    Args:
        model2_db_path: Caminho do banco modelo2
        timeframe: Timeframe (H4, H1, M5)
        symbols: Lista de símbolos (opcional)
        ppo_checkpoint: Checkpoint PPO customizado (opcional)
        dry_run: Modo simulado
        output_dir: Diretório de saída

    Returns:
        Resultado do processamento
    """

    script_path = REPO_ROOT / "scripts" / "model2" / "rl_signal_generation.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--model2-db-path", str(model2_db_path),
        "--timeframe", timeframe,
    ]

    if ppo_checkpoint:
        cmd.extend(["--ppo-checkpoint", str(ppo_checkpoint)])

    if symbols:
        cmd.extend(["--symbols", ",".join(symbols)])

    if dry_run:
        cmd.append("--dry-run")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check if successful
        if result.returncode == 0:
            # Try to parse JSON from stdout
            lines = result.stdout.strip().split('\n')

            # Find the JSON object (starts with '{' and is valid JSON)
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()
                if line.startswith('{'):
                    try:
                        json_result = json.loads(line)
                        return json_result
                    except json.JSONDecodeError:
                        continue

        # If couldn't parse, check stderr for RL signal output file
        output_lines = result.stderr.strip().split('\n')
        for line in output_lines:
            if "Resultado salvo:" in line or "output_file" in line:
                # Try to extract path and read file
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        potential_path = parts[-1].strip()
                        if Path(potential_path).exists():
                            with open(potential_path) as f:
                                return json.load(f)
                    except:
                        pass

        # Fallback: return generic success with subprocess output
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "message": "RL signal generation executed (output parse issue)",
            "return_code": result.returncode,
            "env_note": "Check result files in results/model2/runtime/model2_rl_signals_*.json"
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "RL signal generation timeout (60s)",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


if __name__ == '__main__':
    # Test
    result = run_rl_signal_generation(
        model2_db_path="db/modelo2.db",
        timeframe="H4",
        dry_run=True,
    )
    print(json.dumps(result, indent=2))
