from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TLReproductionPlan:
    item_id: str
    pytest_targets: tuple[str, ...]
    mypy_targets: tuple[str, ...]
    commands: tuple[str, ...]
    evidence_checklist: tuple[str, ...]


def build_tl_reproduction_plan(
    *,
    item_id: str,
    changed_files: Iterable[str],
    pytest_targets: Iterable[str] | None = None,
) -> TLReproductionPlan:
    normalized_item_id = item_id.strip()
    if not normalized_item_id:
        raise ValueError("item_id_invalido")

    files = [path.strip() for path in changed_files if path.strip()]
    if not files:
        raise ValueError("changed_files_vazio")

    derived_pytest_targets = _derive_pytest_targets(files)
    if pytest_targets is None:
        selected_pytest_targets = derived_pytest_targets
    else:
        selected_pytest_targets = tuple(path.strip() for path in pytest_targets if path.strip())

    if not selected_pytest_targets:
        raise ValueError("pytest_targets_vazio")
    if any(target == "tests/" for target in selected_pytest_targets):
        raise ValueError("pytest_target_suite_total_proibido")

    mypy_targets = _derive_mypy_targets(files)
    if not mypy_targets:
        raise ValueError("mypy_targets_vazio")

    pytest_cmd = "pytest -q " + " ".join(selected_pytest_targets)
    mypy_cmd = "mypy --strict " + " ".join(mypy_targets)
    commands = (pytest_cmd, mypy_cmd)
    checklist = (
        "reproduzir_pytest_escopo_item",
        "reproduzir_mypy_modulos_alterados",
        "registrar_evidencias_no_handoff_tl",
    )

    return TLReproductionPlan(
        item_id=normalized_item_id,
        pytest_targets=selected_pytest_targets,
        mypy_targets=mypy_targets,
        commands=commands,
        evidence_checklist=checklist,
    )


def _derive_pytest_targets(files: list[str]) -> tuple[str, ...]:
    targets = tuple(path for path in files if path.startswith("tests/") and path.endswith(".py"))
    return targets


def _derive_mypy_targets(files: list[str]) -> tuple[str, ...]:
    module_paths = []
    for path in files:
        if not path.endswith(".py"):
            continue
        if path.startswith("tests/"):
            continue
        if path.startswith("core/") or path.startswith("scripts/"):
            module_paths.append(path)
    return tuple(module_paths)
