from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any
import yaml

@dataclass(frozen=True)
class LogFile:
    """Representa um arquivo de log com seus metadados."""
    path: str
    level: str
    timestamp: datetime

class LogRotationManager:
    """
    Gerencia a política de retenção de logs com base em regras de um arquivo de configuração.
    """
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy

    @classmethod
    def from_config_file(cls, config_path: str) -> "LogRotationManager":
        """Cria uma instância a partir de um arquivo de configuração YAML."""
        with open(config_path, "r") as f:
            policy = yaml.safe_load(f)
        return cls(policy)

    def plan_retention_actions(self, log_files: List[LogFile]) -> List[Dict[str, Any]]:
        """
        Gera um plano de ações (MANTER ou EXCLUIR) para uma lista de arquivos de log.
        """
        actions = []
        retention_days = self.policy.get("retention_days", {})

        for log_file in log_files:
            retention_period = retention_days.get(log_file.level, 7) # Default 7 days
            age = (datetime.now() - log_file.timestamp).days

            if age > retention_period:
                actions.append({"action": "DELETE", "file": log_file})
            else:
                actions.append({"action": "KEEP", "file": log_file})
        
        return actions
