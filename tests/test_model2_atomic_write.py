import json
from pathlib import Path

from scripts.model2.io_utils import atomic_write_json


def test_atomic_write_json_overwrites_file_atomically(tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    atomic_write_json(target, {"status": "first"}, ensure_ascii=True, indent=2)
    atomic_write_json(target, {"status": "second"}, ensure_ascii=True, indent=2)

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["status"] == "second"
    assert not any(item.suffix == ".tmp" for item in tmp_path.iterdir())
