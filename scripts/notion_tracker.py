#!/usr/bin/env python3
"""Tracker contract + helpers for the Notion-backed pipeline.

This module is the canonical reference for what every agent writes to the
Notion Jobs / Activity Log / Contacts databases. Agents call the Notion MCP
tools directly with payloads matching `validate_job_props` /
`validate_event_props`; this file is the contract they validate against.

Why a script and not agent instructions: stable-id generation, enum checks and
schema validation must be *deterministic*. If an LLM re-derives them each time,
dedup breaks and the contract drifts (DESIGN.md §9).

Stdlib only. Optional NOTION_TOKEN enables a thin HTTP client for headless use
(e.g. the nightly sweep). Without a token the CLI still prints the contract and
generates stable ids.

Usage:
    python3 scripts/notion_tracker.py contract               # enums + DB ids
    python3 scripts/notion_tracker.py stable-id <co> <role>  # deterministic slug
    python3 scripts/notion_tracker.py status                 # dashboard (needs token)
    python3 scripts/notion_tracker.py audit                  # hygiene check (needs token)
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

# --- Canonical enums (must match the Notion DB select options) -------------
#
# TWO AXES. Do not merge them into one column (DESIGN.md §4).
#   worklane = what *I* have done about this job     (automation happens here)
#   stage    = where the *company* has taken me      (humans drive this)

WORKLANE = [
    "discovered",   # job-hunter found it; user has not seen it
    "proposed",     # briefer put it in the weekly brief; awaiting approval
    "dismissed",    # user rejected it pre-application (terminal)
    "tailored",     # approved; resume tailored
    "ready",        # form filled, awaiting user confirmation to submit
    "needs_human",  # automation cannot submit; kit handed off
    "submitted",    # actually applied (terminal for this axis)
]
WORKLANE_TERMINAL = {"dismissed", "submitted"}

STAGE = [
    "lead",         # not applied yet — the whole worklane runs inside this
    "applied",
    "screening",
    "interview",
    "offer",
    "closed",
]
CLOSED_REASON = ["accepted", "rejected", "ghosted", "withdrawn"]

# Why a job was dismissed pre-application. Feeds the preference-learning loop
# (DESIGN.md §10-②) — keep this list small so counts stay meaningful.
DISMISS_REASON = [
    "location", "level", "comp", "domain", "company",
    "sponsorship", "stack", "no_response", "unspecified",
]

EVENT_TYPE = [
    "Discovered", "Proposed", "Approved", "Dismissed", "Tailored", "Applied",
    "Recruiter Reach", "Stage Change", "Interview Scheduled", "Interview Done",
    "Note", "Reject", "Offer", "Withdraw",
]

AGENT = [
    "Job Hunter", "Briefer", "Resume Tailor", "Applicator",
    "Interview Coach", "Tracker", "User",
]

LEVEL = ["Mid", "Senior", "Staff", "Unknown"]
SPONSORSHIP = ["Yes", "No", "Unknown"]
SOURCE = [
    "LinkedIn", "Company site", "Referral", "Recruiter",
    "Indeed", "Wellfound", "Levels.fyi", "Other",
]
# Judged at save time, not at submit time, so the user knows up front which
# ones will land on their plate (DESIGN.md §10-④).
SUBMIT_METHOD = ["auto-form", "assisted", "manual", "email"]


# --- Config ---------------------------------------------------------------

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"missing {CONFIG_PATH}\n"
            "Run the provisioning hook first (hooks/provision.md) to create the\n"
            "Notion databases in your own workspace."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def db(name: str) -> dict:
    return load_config()["databases"][name]


# --- Stable IDs -----------------------------------------------------------

def stable_id(company: str, role: str, posted: date | str | None = None) -> str:
    """Deterministic dedup key, e.g. 'anthropic-senior-backend-2026-04'."""
    if isinstance(posted, str):
        posted = date.fromisoformat(posted[:10])
    if posted is None:
        posted = date.today()
    parts = [_slug(company), _slug(role), posted.strftime("%Y-%m")]
    return "-".join(p for p in parts if p)


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:40]


# --- Validation -----------------------------------------------------------

REQUIRED_JOB_PROPS = ("Title", "Company", "worklane", "stage", "Stable ID", "Source")


def validate_job_props(props: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for k in REQUIRED_JOB_PROPS:
        if not props.get(k):
            errs.append(f"missing required field: {k!r}")

    if (w := props.get("worklane")) and w not in WORKLANE:
        errs.append(f"worklane {w!r} not in {WORKLANE}")
    if (st := props.get("stage")) and st not in STAGE:
        errs.append(f"stage {st!r} not in {STAGE}")

    # Cross-axis invariants — the whole point of splitting the axes.
    if props.get("stage") == "lead" and props.get("worklane") == "submitted":
        errs.append("worklane=submitted requires stage != 'lead' (submitted means applied)")
    if props.get("stage") not in (None, "lead") and props.get("worklane") != "submitted":
        errs.append(f"stage={props.get('stage')!r} requires worklane='submitted'")
    if props.get("worklane") == "dismissed" and not props.get("dismiss_reason"):
        errs.append("worklane=dismissed requires dismiss_reason (feeds preference learning)")
    if (dr := props.get("dismiss_reason")) and dr not in DISMISS_REASON:
        errs.append(f"dismiss_reason {dr!r} not in {DISMISS_REASON}")
    if props.get("stage") == "closed" and not props.get("closed_reason"):
        errs.append("stage=closed requires closed_reason")
    if (cr := props.get("closed_reason")) and cr not in CLOSED_REASON:
        errs.append(f"closed_reason {cr!r} not in {CLOSED_REASON}")

    if (lv := props.get("Level")) and lv not in LEVEL:
        errs.append(f"Level {lv!r} not in {LEVEL}")
    if (sp := props.get("Sponsorship")) and sp not in SPONSORSHIP:
        errs.append(f"Sponsorship {sp!r} not in {SPONSORSHIP}")
    if (src := props.get("Source")) and src not in SOURCE:
        errs.append(f"Source {src!r} not in {SOURCE}")
    if (sm := props.get("submit_method")) and sm not in SUBMIT_METHOD:
        errs.append(f"submit_method {sm!r} not in {SUBMIT_METHOD}")
    if (ms := props.get("Match score")) is not None and not 0 <= float(ms) <= 100:
        errs.append(f"Match score {ms} not in 0..100")
    return errs


def validate_event_props(props: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for k in ("Summary", "Timestamp", "Event type", "Agent"):
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

    def query_jobs(self, **filters: str) -> list[dict]:
        body: dict = {"page_size": 100}
        conds = [
            {"property": k, "select": {"equals": v}}
            for k, v in filters.items() if v
        ]
        if conds:
            body["filter"] = conds[0] if len(conds) == 1 else {"and": conds}
        r = self._req("POST", f"databases/{db('jobs')['database_id']}/query", body)
        return r.get("results", [])

    def query_recent_events(self, limit: int = 25) -> list[dict]:
        body = {
            "page_size": limit,
            "sorts": [{"property": "Timestamp", "direction": "descending"}],
        }
        r = self._req("POST", f"databases/{db('activity_log')['database_id']}/query", body)
        return r.get("results", [])


def _sel(page: dict, prop: str) -> str:
    return (page["properties"].get(prop, {}).get("select") or {}).get("name", "")


def _title(page: dict, prop: str) -> str:
    return "".join(t.get("plain_text", "") for t in page["properties"].get(prop, {}).get("title", []))


def _text(page: dict, prop: str) -> str:
    return "".join(t.get("plain_text", "") for t in page["properties"].get(prop, {}).get("rich_text", []))


# --- CLI ------------------------------------------------------------------

def cmd_contract() -> int:
    try:
        cfg = load_config()
        print("# Tracker contract\n")
        print("## Databases")
        for name, d in cfg["databases"].items():
            print(f"  - {name:13s}  {d.get('data_source_id', '?')}  ({d.get('url', '')})")
    except SystemExit as e:
        print("# Tracker contract\n")
        print(f"## Databases\n  (not provisioned) {e}".replace("\n", "\n  "))

    print("\n## worklane — my work (automation lives here)")
    print("  " + " -> ".join(w for w in WORKLANE if w not in ("dismissed", "needs_human")))
    print("  branches: dismissed (pre-application reject), needs_human (handoff)")
    print("  terminal: " + ", ".join(sorted(WORKLANE_TERMINAL)))
    print("\n## stage — external process")
    print("  " + " -> ".join(STAGE))
    print("  closed_reason: " + ", ".join(CLOSED_REASON))
    print("\n## Cross-axis invariants")
    print("  stage != 'lead'          <=> worklane == 'submitted'")
    print("  worklane == 'dismissed'   => dismiss_reason required")
    print("  stage == 'closed'         => closed_reason required")
    print("\n## dismiss_reason (preference-learning signal)\n  " + ", ".join(DISMISS_REASON))
    print("\n## Event types\n  " + ", ".join(EVENT_TYPE))
    print("\n## Agents\n  " + ", ".join(AGENT))
    print("\n## submit_method (judged at save time)\n  " + ", ".join(SUBMIT_METHOD))
    print("\n## Required Jobs props\n  " + ", ".join(REQUIRED_JOB_PROPS))
    print("\n## Required Activity Log props")
    print("  Summary, Timestamp, Event type, Agent")
    print("  (+ Job relation whenever the event is about a specific job)")
    print("  (+ 'From -> To' for Stage Change)")
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
        print("Use the Notion MCP from an agent for live state, or set NOTION_TOKEN.", file=sys.stderr)
        return None


def cmd_status() -> int:
    n = _connect()
    if n is None:
        return 2
    jobs = n.query_jobs()

    by_lane: dict[str, int] = {}
    by_stage: dict[str, int] = {}
    for j in jobs:
        by_lane[_sel(j, "worklane")] = by_lane.get(_sel(j, "worklane"), 0) + 1
        by_stage[_sel(j, "stage")] = by_stage.get(_sel(j, "stage"), 0) + 1

    print("# worklane (my work)")
    for w in WORKLANE:
        if by_lane.get(w):
            print(f"  {w:14s} {by_lane[w]}")
    print("\n# stage (external)")
    for s in STAGE:
        if by_stage.get(s):
            print(f"  {s:14s} {by_stage[s]}")

    print("\n# recent activity")
    for e in n.query_recent_events(10):
        p = e["properties"]
        ts = (p.get("Timestamp", {}).get("date") or {}).get("start", "?")
        print(f"  {ts}  [{_sel(e, 'Event type')}/{_sel(e, 'Agent')}] {_title(e, 'Summary')}")
    return 0


def cmd_audit() -> int:
    """Hygiene check. Flags only — never mutates. Mirrors tracker.md."""
    n = _connect()
    if n is None:
        return 2
    findings: list[str] = []
    for j in n.query_jobs():
        name = f"{_text(j, 'Company') or '?'} / {_title(j, 'Title') or '?'}"
        errs = validate_job_props({
            "Title": _title(j, "Title"),
            "Company": _text(j, "Company"),
            "worklane": _sel(j, "worklane"),
            "stage": _sel(j, "stage"),
            "Stable ID": _text(j, "Stable ID"),
            "Source": _sel(j, "Source"),
            "submit_method": _sel(j, "submit_method"),
            "dismiss_reason": _sel(j, "dismiss_reason"),
            "closed_reason": _sel(j, "closed_reason"),
        })
        findings += [f"{name}: {e}" for e in errs]
        if _sel(j, "worklane") in ("discovered", "proposed") and not _sel(j, "submit_method"):
            findings.append(f"{name}: submit_method missing — applicator cannot route it")

    if not findings:
        print("OK  no hygiene issues found")
        return 0
    print(f"{len(findings)} issue(s) — flagged only, nothing was changed:")
    for f in findings[:40]:
        print(f"  - {f}")
    if len(findings) > 40:
        print(f"  ... {len(findings) - 40} more")
    return 1


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
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
