"""
Gerenciador de Checkpoints com Criptografia Fernet

Módulo responsável por serializar, criptografar e recuperar modelos PPO
durante treinamento. Utiliza Fernet (criptografia simétrica) para proteger
checkpoints e mantém histórico completo com rastreabilidade.

Atributos críticos:
- Criptografia: Fernet com chave em variável de ambiente
- Serializador: joblib (preserva tipos complexos NumPy)
- Backup: Cópia plaintext em diretório isolado (apenas para recuperação)
- Validação: SHA256 para integridade + metadata com timestamp
"""

import os
import json
import hashlib
import joblib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Gerencia lifecycle completo de checkpoints PPO com criptografia.

    Responsabilidades:
    - Salvar modelo + métricas com Fernet encryption
    - Carregar e validar integridade de checkpoints
    - Listar checkpoints filtrados por métrica
    - Limpeza de checkpoints antigos com retenção configurável
    - Backup plaintext isolado (uso emergencial apenas)
    """

    def __init__(
        self,
        checkpoint_dir: str = "checkpoints/ppo_models",
        backup_plaintext_dir: str = "checkpoints/ppo_backup_emergency",
        encryption_key_env: str = "PPO_CHECKPOINT_KEY",
        keep_last_n: int = 10,
    ):
        """
        Inicializa gerenciador de checkpoints.

        Args:
            checkpoint_dir: Diretório para salvar checkpoints criptografados
            backup_plaintext_dir: Dir isolado para backup emergencial (sem crypto)
            encryption_key_env: Nome da var de ambiente contendo chave Fernet
            keep_last_n: Número de checkpoints recentes a manter

        Raises:
            ValueError: Se chave de encryption não está em ambiente
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.backup_dir = Path(backup_plaintext_dir)
        self.keep_last_n = keep_last_n

        # Criar diretórios
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Carregar chave de criptografia
        cipher_key = os.getenv(encryption_key_env)
        if not cipher_key:
            raise ValueError(
                f"Variável de ambiente {encryption_key_env} não definida. "
                f"Gere com: from cryptography.fernet import Fernet; "
                f"print(Fernet.generate_key().decode())"
            )
        self.cipher = Fernet(cipher_key.encode() if isinstance(cipher_key, str) else cipher_key)

        logger.info(
            f"CheckpointManager inicializado em {checkpoint_dir} "
            f"com retenção de últimos {keep_last_n} checkpoints"
        )

    def save_checkpoint(
        self,
        model: Any,
        step: int,
        metrics: Dict[str, float],
        encrypt: bool = True,
    ) -> Tuple[str, str]:
        """
        Salva checkpoint com modelo, métricas e integridade validada.

        Args:
            model: Modelo PPO (stable_baselines3.PPO)
            step: Número de steps de treinamento
            metrics: Dict com métricas {sharpe, loss, kl_div, entropy, ...}
            encrypt: Se True, criptografa com Fernet; se False, apenas serializa

        Returns:
            Tupla (caminho_criptografado, caminho_backup_plaintext)

        Raises:
            IOError: Se falhar ao escrever arquivo
            ValueError: Se modelo ou métricas inválidos
        """
        if not isinstance(metrics, dict):
            raise ValueError("metrics deve ser um dicionário")

        timestamp = datetime.utcnow().isoformat()
        checkpoint_name = f"ppo_step_{step:06d}_{timestamp.replace(':', '-')[:16]}"

        # Serializar modelo + metadata
        checkpoint_data = {
            "step": step,
            "timestamp": timestamp,
            "model": model,
            "metrics": metrics,
            "checkpoint_name": checkpoint_name,
        }

        try:
            # Serializar com joblib
            serialized = joblib.dumps(checkpoint_data, compress=3)

            # Calcular SHA256 para integridade
            sha256_hash = hashlib.sha256(serialized).hexdigest()
            checkpoint_data["sha256"] = sha256_hash

            # Serializar novamente com hash
            serialized = joblib.dumps(checkpoint_data, compress=3)

            # Criptografar se solicitado
            if encrypt:
                encrypted_data = self.cipher.encrypt(serialized)
                checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.joblib.enc"
                with open(checkpoint_path, "wb") as f:
                    f.write(encrypted_data)
                logger.info(f"Checkpoint criptografado salvo: {checkpoint_path}")
            else:
                checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.joblib"
                with open(checkpoint_path, "wb") as f:
                    f.write(serialized)
                logger.warning(f"Checkpoint NÃO criptografado: {checkpoint_path}")

            # Salvar plaintext backup em diretório isolado (emergência apenas)
            backup_path = self.backup_dir / f"{checkpoint_name}_backup.joblib"
            with open(backup_path, "wb") as f:
                f.write(serialized)
            logger.debug(f"Backup plaintext salvo (emergência): {backup_path}")

            # Salvar metadata em JSON para auditoria
            metadata_path = self.checkpoint_dir / f"{checkpoint_name}.json"
            with open(metadata_path, "w") as f:
                json.dump(
                    {
                        "step": step,
                        "timestamp": timestamp,
                        "metrics": metrics,
                        "sha256": sha256_hash,
                        "encrypted": encrypt,
                        "checkpoint_file": str(checkpoint_path),
                        "backup_file": str(backup_path),
                    },
                    f,
                    indent=2,
                )

            return str(checkpoint_path), str(backup_path)

        except Exception as e:
            logger.error(f"Falha ao salvar checkpoint passo {step}: {e}")
            raise

    def load_checkpoint(
        self,
        checkpoint_path: str,
        decrypt: bool = True,
        validate_hash: bool = True,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Carrega checkpoint validando integridade e descriptografando.

        Args:
            checkpoint_path: Caminho do arquivo .joblib.enc ou .joblib
            decrypt: Se True, descriptografa; se False, lê plaintext direto
            validate_hash: Se True, valida SHA256 antes de retornar

        Returns:
            Tupla (modelo, metadata_dict)

        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se falhar descriptografia ou validação de hash
        """
        checkpoint_path = Path(checkpoint_path)

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint não encontrado: {checkpoint_path}")

        try:
            with open(checkpoint_path, "rb") as f:
                raw_data = f.read()

            # Descriptografar se necessário
            if decrypt and checkpoint_path.suffix == ".enc":
                serialized = self.cipher.decrypt(raw_data)
                logger.info(f"Checkpoint descriptografado: {checkpoint_path}")
            else:
                serialized = raw_data
                logger.info(f"Checkpoint carregado (plaintext): {checkpoint_path}")

            # Desserializar
            checkpoint_data = joblib.loads(serialized)

            # Validar hash se solicitado
            if validate_hash and "sha256" in checkpoint_data:
                expected_hash = checkpoint_data.pop("sha256")
                recalc_hash = hashlib.sha256(
                    joblib.dumps(checkpoint_data, compress=3)
                ).hexdigest()

                if expected_hash != recalc_hash:
                    raise ValueError(
                        f"Validação SHA256 falhou: "
                        f"esperado={expected_hash[:8]}... "
                        f"calculado={recalc_hash[:8]}..."
                    )
                logger.info(f"SHA256 validado: {expected_hash[:8]}...")

            model = checkpoint_data.pop("model")
            metadata = checkpoint_data

            return model, metadata

        except Exception as e:
            logger.error(f"Falha ao carregar checkpoint {checkpoint_path}: {e}")
            raise

    def list_checkpoints_by_metric(
        self,
        metric: str = "sharpe",
        top_n: int = 5,
        sort_order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """
        Lista checkpoints ordenados por métrica especificada.

        Args:
            metric: Nome da métrica (sharpe, loss, kl_div, entropy, etc)
            top_n: Número máximo de resultados
            sort_order: "desc" (maior melhor) ou "asc" (menor melhor)

        Returns:
            Lista de dicts com (checkpoint_path, step, timestamp, métrica_valor)
        """
        results = []

        for json_file in sorted(self.checkpoint_dir.glob("*.json")):
            try:
                with open(json_file, "r") as f:
                    metadata = json.load(f)

                if metric in metadata.get("metrics", {}):
                    results.append({
                        "checkpoint_file": metadata["checkpoint_file"],
                        "step": metadata["step"],
                        "timestamp": metadata["timestamp"],
                        "metric_value": metadata["metrics"][metric],
                        "all_metrics": metadata["metrics"],
                    })
            except Exception as e:
                logger.warning(f"Erro ao ler metadata {json_file}: {e}")

        # Ordenar
        reverse = sort_order == "desc"
        results.sort(key=lambda x: x["metric_value"], reverse=reverse)

        return results[:top_n]

    def validate_checkpoint(self, checkpoint_path: str) -> bool:
        """
        Valida integridade de checkpoint sem carregar modelo (rápido).

        Args:
            checkpoint_path: Caminho do checkpoint

        Returns:
            True se válido, False caso contrário
        """
        try:
            checkpoint_path = Path(checkpoint_path)

            if not checkpoint_path.exists():
                logger.warning(f"Arquivo não existe: {checkpoint_path}")
                return False

            with open(checkpoint_path, "rb") as f:
                raw_data = f.read()

            # Tentar descriptografar
            if checkpoint_path.suffix == ".enc":
                try:
                    self.cipher.decrypt(raw_data)
                except Exception as e:
                    logger.error(f"Falha ao descriptografar: {e}")
                    return False

            logger.info(f"Checkpoint válido: {checkpoint_path}")
            return True

        except Exception as e:
            logger.error(f"Validação falhou: {e}")
            return False

    def cleanup_old_checkpoints(self, keep_last_n: Optional[int] = None) -> int:
        """
        Remove checkpoints antigos mantendo apenas os últimos N.

        Args:
            keep_last_n: Override do padrão definido no __init__

        Returns:
            Número de checkpoints deletados
        """
        keep = keep_last_n or self.keep_last_n
        deleted = 0

        json_files = sorted(self.checkpoint_dir.glob("*.json"))

        if len(json_files) > keep:
            for old_json in json_files[:-keep]:
                try:
                    # Deletar JSON + checkpoint associado
                    checkpoint_file = None
                    with open(old_json, "r") as f:
                        metadata = json.load(f)
                        checkpoint_file = metadata.get("checkpoint_file")
                        backup_file = metadata.get("backup_file")

                    old_json.unlink()
                    if checkpoint_file and Path(checkpoint_file).exists():
                        Path(checkpoint_file).unlink()
                    if backup_file and Path(backup_file).exists():
                        Path(backup_file).unlink()

                    deleted += 1
                    logger.info(f"Checkpoint antigo deletado: {old_json.stem}")

                except Exception as e:
                    logger.warning(f"Erro ao deletar {old_json}: {e}")

        logger.info(f"Limpeza concluída: {deleted} checkpoints removidos")
        return deleted
