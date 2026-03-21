"""I/O helpers for Model 2.0 operational scripts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(
    output_path: str | Path,
    payload: Any,
    *,
    ensure_ascii: bool = True,
    indent: int = 2,
) -> Path:
    """Atomically persist JSON payload to avoid partially-written artifacts."""

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(target.parent),
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_file = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=ensure_ascii, indent=indent)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_file), str(target))
        return target
    finally:
        if tmp_file is not None and tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
