"""Utilitarios para leitura defensiva do arquivo temporario de dashboard M2."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

LOGGER = logging.getLogger("m2_live")


def _utc_now_iso() -> str:
    """Retorna timestamp UTC atual no formato ISO-8601 com sufixo Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def get_project_root() -> str:
    """Retorna o diretorio raiz do projeto."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def m2_tmp_path() -> str:
    """Retorna o caminho absoluto para logs/m2_tmp.json."""
    return os.path.join(get_project_root(), "logs", "m2_tmp.json")


def load_m2_tmp() -> dict:
    """Carrega o JSON de logs/m2_tmp.json de forma defensiva.

    Em caso de ausencia, retorna um placeholder. Em caso de JSON invalido,
    renomeia o arquivo corrompido para <orig>.corrupt.<timestamp> e retorna
    o placeholder.
    """
    path = m2_tmp_path()
    if not os.path.exists(path):
        LOGGER.warning("JSON nao encontrado em %s; retornando placeholder", path)
        return {
            "generated_at": _utc_now_iso(),
            "symbols": {},
            "note": "placeholder created because m2_tmp.json was missing",
        }

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        LOGGER.error("JSON invalido em %s: %s", path, str(e))
        corrupt_path = path + ".corrupt." + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        try:
            os.replace(path, corrupt_path)
            LOGGER.warning("Arquivo corrompido movido para %s", corrupt_path)
        except Exception as ex:
            LOGGER.error("Falha ao renomear arquivo corrompido: %s", str(ex))
        return {
            "generated_at": _utc_now_iso(),
            "symbols": {},
            "note": "placeholder created because m2_tmp.json was corrupt",
        }
    except Exception as e:
        LOGGER.exception("Erro ao ler %s: %s", path, str(e))
        raise
