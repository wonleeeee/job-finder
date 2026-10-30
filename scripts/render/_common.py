"""Shared helpers for the tailored-resume renderers. stdlib only.

Every renderer takes one argument — the work folder (data/cache/tailored/<stable-id>/) — and reads
resume.json (master schema, tailored subset) from it. No personal value lives in this code: name,
contact, address and work authorization all come from resume.json `basics`.

Optional `render.json` in the same folder tunes presentation without touching the schema
(master_resume.schema.json forbids extra top-level keys):

    {
      "sub_ids":     ["bullet-id", ...],          nest these bullets under the preceding bullet
      "auth_labels": {"US-H1B": "H-1B (transfer required)"},   override work_authorization labels
      "bold":        ["phrase", ...]              bold in the designed ATS html (warns if unmatched)
    }
"""
import json
import re
import sys
from pathlib import Path

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]

AUTH_LABELS = {
    "US-citizen": "U.S. citizen",
    "US-GC": "U.S. permanent resident",
    "US-H1B": "H-1B",
    "US-OPT": "F-1 OPT",
    "US-STEM-OPT": "F-1 STEM OPT",
    "US-TN": "TN",
    "US-L1": "L-1",
    "US-O1": "O-1",
}

SKILL_LABELS = {
    "languages": "Languages",
    "frameworks": "Frameworks",
    "databases": "Databases",
    "backend": "Backend",
    "frontend": "Front-end",
    "cloud_infrastructure": "Cloud & infra",
    "ci_cd": "CI/CD",
    "messaging_streaming": "Messaging & streaming",
    "core_strengths": "Core strengths",
    "manufacturing": "Manufacturing",
    "ai_engineering": "AI engineering",
    "delivery": "Delivery & ops",
}


def work_dir():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {Path(sys.argv[0]).name} <work folder, e.g. data/cache/tailored/<stable-id>/>")
    d = Path(sys.argv[1])
    if not d.is_dir():
        sys.exit(f"not a folder: {d}")
    return d


def load_json(path, required=True):
    if not path.exists():
        if required:
            sys.exit(f"missing: {path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load(d):
    """(resume, render options) from the work folder."""
    return load_json(d / "resume.json"), load_json(d / "render.json", required=False)


def fmt_date(iso, long=False):
    if not iso:
        return "Present"
    names = MONTHS_LONG if long else MONTHS
    return f"{names[int(iso[5:7]) - 1]} {iso[:4]}"


def edu_when(ed, long=False):
    """End date, or 'start – expected YYYY' from an 'expected completion ~YYYY' highlight."""
    if ed.get("end_date"):
        return fmt_date(ed["end_date"], long)
    start = fmt_date(ed["start_date"], long) if ed.get("start_date") else ""
    exp = next((h for h in ed.get("highlights", []) if "expected" in h), "")
    m = re.search(r"expected completion ~?(\d{4})", exp)
    tail = f"expected {m.group(1)}" if m else "Present"
    return f"{start} – {tail}" if start else tail


def auth_line(basics, opts):
    labels = {**AUTH_LABELS, **opts.get("auth_labels", {})}
    return " · ".join(labels.get(a, a) for a in basics.get("work_authorization", []))


def location_line(basics, with_address=True):
    loc = basics.get("location", {})
    parts = [loc.get("address")] if with_address and loc.get("address") else []
    parts += [p for p in (loc.get("city"), loc.get("region")) if p]
    return ", ".join(parts)


def availability(basics):
    loc = basics.get("location", {})
    bits = [w for w, on in (("remote", loc.get("remote_ok")), ("relocation", loc.get("willing_to_relocate"))) if on]
    return f"open to {' and '.join(bits)}" if bits else ""


def primary_link(basics):
    links = basics.get("links") or []
    return links[0]["url"] if links else ""


def link_label(url):
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def skill_label(key):
    return SKILL_LABELS.get(key, key.replace("_", " ").capitalize())


def group_by_company(experience):
    """Consecutive roles at the same company -> one group (a promotion reads as one block)."""
    groups = []
    for e in experience:
        if groups and groups[-1][0]["company"] == e["company"]:
            groups[-1].append(e)
        else:
            groups.append([e])
    return groups
