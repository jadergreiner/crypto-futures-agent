"""Escritor atomico de JSON para o arquivo temporario de dashboard M2."""

from __future__ import annotations

import json
import logging
import os
import tempfile

LOGGER = logging.getLogger("m2_live")


def atomic_write_json(target_path: str, data: dict) -> None:
    """Escreve data em target_path de forma atomica (sem estado inconsistente).

    Grava em arquivo temporario no mesmo diretorio e substitui atomicamente
    via os.replace, garantindo que o arquivo destino nunca fique incompleto.
    """
    dirpath = os.path.dirname(target_path)
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".m2_tmp_", dir=dirpath, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception as exc:
                LOGGER.debug("Falha ao remover arquivo temporario %s: %s", tmp_path, exc)
