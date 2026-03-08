import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG_PATH = REPO_ROOT / "docs" / "BACKLOG.md"


def _task_blocks(markdown: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^###\s+TAREFA\s+([^\n]+)$", markdown, flags=re.MULTILINE))
    blocks: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        blocks.append((match.group(1).strip(), markdown[start:end]))
    return blocks


def _is_path_like(token: str) -> bool:
    normalized = token.strip()
    if "/" in normalized or "\\" in normalized:
        return True
    return bool(re.search(r"\.[A-Za-z0-9]+$", normalized))


def test_concluded_backlog_tasks_have_existing_evidence_paths() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    blocks = _task_blocks(text)
    assert blocks, "No task blocks found in docs/BACKLOG.md"

    for task_name, block in blocks:
        status_match = re.search(r"^Status:\s*(.+)$", block, flags=re.MULTILINE)
        assert status_match is not None, f"Missing Status line in task: {task_name}"
        status = status_match.group(1).strip()
        if not status.startswith("CONCLUIDA"):
            continue

        assert "Evidencias:" in block, f"Missing Evidencias section in concluded task: {task_name}"
        evidence_section = block.split("Evidencias:", maxsplit=1)[1]
        evidence_paths = re.findall(r"`([^`]+)`", evidence_section)
        assert evidence_paths, f"Missing evidence paths in concluded task: {task_name}"

        for rel_path in evidence_paths:
            normalized = rel_path.strip().rstrip(".,")
            if not normalized:
                continue
            if not _is_path_like(normalized):
                continue
            if "*" in normalized or "?" in normalized:
                matches = list(REPO_ROOT.glob(normalized))
                if matches:
                    continue
                parent = (REPO_ROOT / normalized).parent.resolve()
                assert parent.exists(), (
                    f"Wildcard evidence parent does not exist for task '{task_name}': {normalized}"
                )
                continue

            absolute = (REPO_ROOT / normalized).resolve()
            assert absolute.exists(), (
                f"Evidence path does not exist for task '{task_name}': {normalized}"
            )
