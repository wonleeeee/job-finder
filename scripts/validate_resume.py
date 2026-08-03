#!/usr/bin/env python3
"""Validate data/master_resume.json against schemas/master_resume.schema.json.

Exit 0 on success, 1 on failure. Prints first 5 errors with JSON pointers.
Run: python3 scripts/validate_resume.py [path/to/resume.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "master_resume.schema.json"
DEFAULT_RESUME = ROOT / "data" / "master_resume.json"


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: pip install jsonschema", file=sys.stderr)
        return 2

    resume_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_RESUME
    if not resume_path.exists():
        print(f"ERROR: resume not found: {resume_path}", file=sys.stderr)
        return 2
    if not SCHEMA_PATH.exists():
        print(f"ERROR: schema not found: {SCHEMA_PATH}", file=sys.stderr)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text())
    resume = json.loads(resume_path.read_text())

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(resume), key=lambda e: e.path)

    try:
        display = resume_path.relative_to(ROOT)
    except ValueError:
        display = resume_path

    if not errors:
        print(f"OK  {display}  (version {resume.get('meta', {}).get('version', '?')})")
        return 0

    print(f"FAIL  {display}  ({len(errors)} error(s))")
    for err in errors[:5]:
        pointer = "/" + "/".join(str(p) for p in err.absolute_path) if err.absolute_path else "/"
        print(f"  {pointer}: {err.message}")
    if len(errors) > 5:
        print(f"  ... {len(errors) - 5} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
