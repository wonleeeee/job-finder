#!/usr/bin/env python3
"""Tracker helpers for the Notion-backed pipeline.

OPTIONAL TOOL. The contract itself lives in `schemas/contract.json` — this
script reads that file, it does not define it. Agents read the same file, so the
system works without Python; running these commands just gives you *mechanical*
checks instead of judgement calls.

  contract   pretty-print schemas/contract.json      → agents can read the JSON directly
  stable-id  deterministic dedup slug                → spec in schemas/stable-id.md
  status     pipeline dashboard      (needs NOTION_TOKEN)
  audit      hygiene check           (needs NOTION_TOKEN)  ← hardest to replace
  export     dump every row to JSON  (needs NOTION_TOKEN)  ← remote backup

`export` matters most: remote state cannot be backed up by copying files, and
hooks/on_update.md requires a dump before any remote migration.

Stdlib only. Usage: python3 scripts/notion_tracker.py <command> [args]
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "notion_databases.json"
CONTRACT_PATH = ROOT / "schemas" / "contract.json"


# --- Contract (data, not code) --------------------------------------------

def contract() -> dict:
    if not CONTRACT_PATH.exists():
        raise SystemExit(f"missing {CONTRACT_PATH} — the contract is data; restore it from git")
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8-sig"))


def _entries(d: dict) -> list[tuple[str, Any]]:
    """Real entries only — `$comment` keys carry prose for humans, not data."""
    return [(k, v) for k, v in d.items() if not k.startswith("$")]


_C = contract()
WORKLANE: list[str] = _C["axes"]["worklane"]["values"]
WORKLANE_TERMINAL: set[str] = set(_C["axes"]["worklane"]["terminal"])
STAGE: list[str] = _C["axes"]["stage"]["values"]
CLOSED_REASON: list[str] = _C["enums"]["closed_reason"]["values"]
DISMISS_REASON: list[str] = _C["enums"]["dismiss_reason"]["values"]
SUBMIT_METHOD: list[str] = _C["enums"]["submit_method"]["values"]
EVENT_TYPE: list[str] = _C["enums"]["event_type"]["values"]
AGENT: list[str] = _C["enums"]["agent"]["values"]
LEVEL: list[str] = _C["enums"]["level"]["values"]
SPONSORSHIP: list[str] = _C["enums"]["sponsorship"]["values"]
SOURCE: list[str] = _C["enums"]["source"]["values"]
REQUIRED_JOB_PROPS: list[str] = _C["required"]["job"]
REQUIRED_EVENT_PROPS: list[str] = _C["required"]["event"]


# --- Config ---------------------------------------------------------------

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"missing {CONFIG_PATH}\n"
            "Run the provisioning hook first (hooks/provision.md) to create the\n"
            "Notion databases in your own workspace."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))


def db(name: str) -> dict:
    return load_config()["databases"][name]


# --- Stable IDs -----------------------------------------------------------
# Spec + worked examples: schemas/stable-id.md  (agents follow it when Python
# is unavailable — keep the two in sync).

def stable_id(company: str, role: str, posted: date | str | None = None) -> str:
    """Deterministic dedup key, e.g. 'anthropic-senior-backend-engineer-2026-04'."""
    if isinstance(posted, str):
        posted = date.fromisoformat(posted[:10])
    if posted is None:
        posted = date.today()
    parts = [_slug(company), _slug(role), posted.strftime("%Y-%m")]
    return "-".join(p for p in parts if p)


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().strip())
    return s.strip("-")[:40].strip("-")


# --- Validation -----------------------------------------------------------

def validate_job_props(props: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for k in REQUIRED_JOB_PROPS:
        if not props.get(k):
            errs.append(f"missing required field: {k!r}")

    if (w := props.get("worklane")) and w not in WORKLANE:
        errs.append(f"worklane {w!r} not in {WORKLANE}")
    if (st := props.get("stage")) and st not in STAGE:
        errs.append(f"stage {st!r} not in {STAGE}")

    # Cross-axis invariants — the reason the axes were split at all.
    if props.get("stage") == "lead" and props.get("worklane") == "submitted":
        errs.append("worklane=submitted requires stage != 'lead' (submitted means applied)")
    if props.get("stage") not in (None, "", "lead") and props.get("worklane") != "submitted":
        errs.append(f"stage={props.get('stage')!r} requires worklane='submitted'")
    if props.get("worklane") == "dismissed" and not props.get("dismiss_reason"):
        errs.append("worklane=dismissed requires dismiss_reason (feeds preference learning)")
    if (dr := props.get("dismiss_reason")) and dr not in DISMISS_REASON:
        errs.append(f"dismiss_reason {dr!r} not in {DISMISS_REASON}")
    if props.get("stage") == "closed" and not props.get("closed_reason"):
        errs.append("stage=closed requires closed_reason")
    if (cr := props.get("closed_reason")) and cr not in CLOSED_REASON:
        errs.append(f"closed_reason {cr!r} not in {CLOSED_REASON}")

    for key, allowed in (("Level", LEVEL), ("Sponsorship", SPONSORSHIP),
                         ("Source", SOURCE), ("submit_method", SUBMIT_METHOD)):
        if (v := props.get(key)) and v not in allowed:
            errs.append(f"{key} {v!r} not in {allowed}")

    rng = _C.get("ranges", {}).get("Match score", {})
    if (ms := props.get("Match score")) is not None and rng:
        if not rng["min"] <= float(ms) <= rng["max"]:
            errs.append(f"Match score {ms} not in {rng['min']}..{rng['max']}")
    return errs


def validate_event_props(props: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for k in REQUIRED_EVENT_PROPS:
        if not props.get(k):
            errs.append(f"missing required field: {k!r}")
    if (et := props.get("Event type")) and et not in EVENT_TYPE:
        errs.append(f"Event type {et!r} not in {EVENT_TYPE}")
    if (ag := props.get("Agent")) and ag not in AGENT:
        errs.append(f"Agent {ag!r} not in {AGENT}")
    if props.get("Event type") == "Stage Change" and not props.get("From → To"):
        errs.append("Stage Change events require 'From → To'")
    return errs


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Optional HTTP client (only when NOTION_TOKEN is set) -----------------

NOTION_VERSION = "2022-06-28"


class Notion:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("NOTION_TOKEN")
        if not self.token:
            raise RuntimeError("NOTION_TOKEN not set — export it or use the Notion MCP")

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"https://api.notion.com/v1/{path.lstrip('/')}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"notion {method} {path} -> {e.code} {e.read().decode()[:300]}")

    def query_all(self, which: str) -> list[dict]:
        """Every row, following pagination. Used by status/audit/export."""
        rows: list[dict] = []
        cursor: str | None = None
        while True:
            body: dict = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            r = self._req("POST", f"databases/{db(which)['database_id']}/query", body)
            rows += r.get("results", [])
            if not r.get("has_more"):
                return rows
            cursor = r.get("next_cursor")


def _sel(page: dict, prop: str) -> str:
    return (page["properties"].get(prop, {}).get("select") or {}).get("name", "")


def _title(page: dict, prop: str) -> str:
    return "".join(t.get("plain_text", "") for t in page["properties"].get(prop, {}).get("title", []))


def _text(page: dict, prop: str) -> str:
    return "".join(t.get("plain_text", "") for t in page["properties"].get(prop, {}).get("rich_text", []))


def _job_props(page: dict) -> dict:
    return {
        "Title": _title(page, "Title"),
        "Company": _text(page, "Company"),
        "worklane": _sel(page, "worklane"),
        "stage": _sel(page, "stage"),
        "Stable ID": _text(page, "Stable ID"),
        "Source": _sel(page, "Source"),
        "Level": _sel(page, "Level"),
        "Sponsorship": _sel(page, "Sponsorship"),
        "submit_method": _sel(page, "submit_method"),
        "dismiss_reason": _sel(page, "dismiss_reason"),
        "closed_reason": _sel(page, "closed_reason"),
    }


# --- CLI ------------------------------------------------------------------

def cmd_contract() -> int:
    c = _C
    try:
        cfg = load_config()
        print("# Databases")
        for name, d in cfg["databases"].items():
            print(f"  {name:13s} {d.get('data_source_id', '?')}  {d.get('url', '')}")
    except SystemExit as e:
        print(f"# Databases\n  (not provisioned — {e})")

    for axis, spec in _entries(c["axes"]):
        print(f"\n# {axis} — {spec['description']}")
        print("  " + " -> ".join(spec["flow"]))
        for k, v in spec.get("branches", {}).items():
            print(f"  branch: {k} — {v}")
        if spec.get("terminal"):
            print(f"  terminal: {', '.join(spec['terminal'])}")

    print("\n# Invariants")
    for inv in c["invariants"]:
        print(f"  {inv['rule']}")
        print(f"      why: {inv['why']}")

    print("\n# Enums")
    for name, spec in _entries(c["enums"]):
        print(f"  {name:16s} {', '.join(spec['values'])}")

    print("\n# Required")
    for kind, keys in c["required"].items():
        print(f"  {kind:16s} {', '.join(keys)}")
    print(f"\n(source: {CONTRACT_PATH.relative_to(ROOT)} — agents read this file directly)")
    return 0


def cmd_stable_id(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: stable-id <company> <role> [posted-date]", file=sys.stderr)
        return 2
    print(stable_id(argv[0], argv[1], argv[2] if len(argv) > 2 else None))
    return 0


def _connect() -> Notion | None:
    try:
        return Notion()
    except RuntimeError as e:
        print(f"NOTE: {e}", file=sys.stderr)
        print("Agents use the Notion MCP for live state — this command is for headless runs.", file=sys.stderr)
        return None


def cmd_status() -> int:
    n = _connect()
    if n is None:
        return 2
    jobs = n.query_all("jobs")
    by_lane: dict[str, int] = {}
    by_stage: dict[str, int] = {}
    for j in jobs:
        by_lane[_sel(j, "worklane")] = by_lane.get(_sel(j, "worklane"), 0) + 1
        by_stage[_sel(j, "stage")] = by_stage.get(_sel(j, "stage"), 0) + 1

    print(f"# worklane (my work) — {len(jobs)} rows")
    for w in WORKLANE:
        if by_lane.get(w):
            print(f"  {w:14s} {by_lane[w]}")
    print("\n# stage (external)")
    for s in STAGE:
        if by_stage.get(s):
            print(f"  {s:14s} {by_stage[s]}")

    print("\n# recent activity")
    events = n.query_all("activity_log")
    events.sort(key=lambda e: (e["properties"].get("Timestamp", {}).get("date") or {}).get("start", ""),
                reverse=True)
    for e in events[:10]:
        ts = (e["properties"].get("Timestamp", {}).get("date") or {}).get("start", "?")
        print(f"  {ts}  [{_sel(e, 'Event type')}/{_sel(e, 'Agent')}] {_title(e, 'Summary')}")
    return 0


def cmd_audit() -> int:
    """Hygiene check. Flags only — never mutates. Mirrors .claude/agents/tracker.md."""
    n = _connect()
    if n is None:
        return 2
    findings: list[str] = []
    for j in n.query_all("jobs"):
        props = _job_props(j)
        name = f"{props['Company'] or '?'} / {props['Title'] or '?'}"
        findings += [f"{name}: {e}" for e in validate_job_props(props)]
        if props["worklane"] in ("discovered", "proposed") and not props["submit_method"]:
            findings.append(f"{name}: submit_method missing — applicator cannot route it")

    for e in n.query_all("activity_log"):
        props = {
            "Summary": _title(e, "Summary"),
            "Timestamp": (e["properties"].get("Timestamp", {}).get("date") or {}).get("start", ""),
            "Event type": _sel(e, "Event type"),
            "Agent": _sel(e, "Agent"),
            "From → To": _text(e, "From → To"),
        }
        findings += [f"event {props['Summary'] or '?'}: {x}" for x in validate_event_props(props)]

    if not findings:
        print("OK  no hygiene issues found")
        return 0
    print(f"{len(findings)} issue(s) — flagged only, nothing was changed:")
    for f in findings[:40]:
        print(f"  - {f}")
    if len(findings) > 40:
        print(f"  ... {len(findings) - 40} more")
    return 1


def cmd_export(argv: list[str]) -> int:
    """Full dump. Remote state cannot be backed up by copying files."""
    n = _connect()
    if n is None:
        return 2
    out = Path(argv[0]) if argv else ROOT / "data" / "backups" / f"notion-{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "exported_at": now_iso(),
        "contract_version": _C["contractVersion"],
        "databases": {name: n.query_all(name) for name in ("jobs", "activity_log", "contacts")},
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = " · ".join(f"{k}={len(v)}" for k, v in payload["databases"].items())
    print(f"exported {counts} -> {out}")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, *rest = argv
    if cmd == "contract":
        return cmd_contract()
    if cmd == "stable-id":
        return cmd_stable_id(rest)
    if cmd == "status":
        return cmd_status()
    if cmd == "audit":
        return cmd_audit()
    if cmd == "export":
        return cmd_export(rest)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
