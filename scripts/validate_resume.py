#!/usr/bin/env python3
"""Validate a resume against schemas/master_resume.schema.json.

OPTIONAL TOOL. The system works without it — resume-curator validates by reading
the schema directly (see .claude/agents/resume-curator.md). Running this gives a
*mechanical* pass/fail instead of a very-likely-correct judgement, which matters
because the master resume is edited incrementally over months and silent schema
drift compounds.

Stdlib only. Uses `jsonschema` when installed (full Draft 2020-12 coverage) and
otherwise falls back to a built-in checker covering the subset this schema
actually uses: type, required, enum, const, minimum/maximum, minItems,
properties, items, additionalProperties, and nullable via type arrays.

Exit 0 = valid, 1 = invalid, 2 = could not run.
Run: python3 scripts/validate_resume.py [path/to/resume.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "master_resume.schema.json"
DEFAULT_RESUME = ROOT / "data" / "master_resume.json"

TYPE_MAP: dict[str, Any] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    py = TYPE_MAP.get(expected)
    if py is None:
        return True  # unknown type keyword — don't invent failures
    if py is not bool and isinstance(value, bool):
        return False  # bool is an int subclass; keep them distinct
    return isinstance(value, py)


def check(node: Any, schema: dict, path: str = "") -> list[str]:
    """Minimal JSON Schema checker for the subset this project uses."""
    errs: list[str] = []
    here = path or "/"

    if "const" in schema and node != schema["const"]:
        errs.append(f"{here}: {node!r} != const {schema['const']!r}")

    if "enum" in schema and node not in schema["enum"]:
        errs.append(f"{here}: {node!r} not in {schema['enum']}")

    if (t := schema.get("type")) is not None:
        allowed = t if isinstance(t, list) else [t]
        if not any(_type_ok(node, a) for a in allowed):
            errs.append(f"{here}: expected type {t}, got {type(node).__name__}")
            return errs  # wrong type — deeper checks would just be noise

    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if (m := schema.get("minimum")) is not None and node < m:
            errs.append(f"{here}: {node} < minimum {m}")
        if (m := schema.get("maximum")) is not None and node > m:
            errs.append(f"{here}: {node} > maximum {m}")

    if isinstance(node, dict):
        for key in schema.get("required", []):
            if key not in node:
                errs.append(f"{here}: missing required property {key!r}")
        props: dict = schema.get("properties", {})
        for key, value in node.items():
            if key in props:
                errs += check(value, props[key], f"{path}/{key}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{here}: unexpected property {key!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs += check(value, schema["additionalProperties"], f"{path}/{key}")

    if isinstance(node, list):
        if (m := schema.get("minItems")) is not None and len(node) < m:
            errs.append(f"{here}: {len(node)} items < minItems {m}")
        if isinstance(schema.get("items"), dict):
            for i, item in enumerate(node):
                errs += check(item, schema["items"], f"{path}/{i}")

    return errs


def validate(resume: dict, schema: dict) -> tuple[list[str], str]:
    """Returns (errors, which engine ran)."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return check(resume, schema), "builtin"
    validator = Draft202012Validator(schema)
    errs = []
    for e in sorted(validator.iter_errors(resume), key=lambda e: list(e.absolute_path)):
        pointer = "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else "/"
        errs.append(f"{pointer}: {e.message}")
    return errs, "jsonschema"


def main() -> int:
    resume_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_RESUME
    if not resume_path.exists():
        print(f"ERROR: resume not found: {resume_path}", file=sys.stderr)
        return 2
    if not SCHEMA_PATH.exists():
        print(f"ERROR: schema not found: {SCHEMA_PATH}", file=sys.stderr)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    resume = json.loads(resume_path.read_text(encoding="utf-8-sig"))
    errors, engine = validate(resume, schema)

    try:
        display = resume_path.relative_to(ROOT)
    except ValueError:
        display = resume_path
    note = "" if engine == "jsonschema" else "  [builtin checker — subset only]"

    if not errors:
        version = resume.get("meta", {}).get("version", "?")
        print(f"OK  {display}  (version {version}){note}")
        return 0

    print(f"FAIL  {display}  ({len(errors)} error(s)){note}")
    for err in errors[:5]:
        print(f"  {err}")
    if len(errors) > 5:
        print(f"  ... {len(errors) - 5} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
