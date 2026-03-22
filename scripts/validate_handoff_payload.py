from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.handoff_payload_validator import parse_handoff_text, validate_handoff_payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida formato e tamanho de payload para handoffs TL->DA e DA->PM"
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["tl_da", "da_pm"],
        help="Stage de handoff a validar",
    )
    parser.add_argument(
        "--json-file",
        type=Path,
        help="Arquivo JSON com payload estruturado",
    )
    parser.add_argument(
        "--text-file",
        type=Path,
        help="Arquivo texto com linhas no formato chave: valor",
    )
    return parser


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json_file and args.text_file:
        raise ValueError("forneca_apenas_um_formato")
    if not args.json_file and not args.text_file:
        raise ValueError("forneca_json_file_ou_text_file")

    if args.json_file:
        raw = args.json_file.read_text(encoding="utf-8")
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError("json_payload_deve_ser_objeto")
        return loaded

    text = args.text_file.read_text(encoding="utf-8")
    return parse_handoff_text(text)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        payload = _load_payload(args)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "is_valid": False,
                    "errors": [f"erro_entrada: {exc}"],
                },
                ensure_ascii=True,
            )
        )
        return 2

    result = validate_handoff_payload(args.stage, payload)
    print(
        json.dumps(
            {
                "is_valid": result.is_valid,
                "stage": result.stage,
                "payload_size_chars": result.payload_size_chars,
                "errors": result.errors,
            },
            ensure_ascii=True,
        )
    )
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
