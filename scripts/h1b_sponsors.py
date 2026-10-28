#!/usr/bin/env python3
"""H-1B sponsor / transfer lookup from official US government data.

OPTIONAL TOOL for job-hunter's sponsorship filter. Two official sources:

  DOL OFLC LCA disclosure data  (dol.gov/agencies/eta/foreign-labor/performance)
      Every H-1B job (new, transfer, extension) needs a Labor Condition
      Application first, so this is the freshest, per-job view. The
      CHANGE_EMPLOYER column counts *transfer* positions directly.
  USCIS H-1B Employer Data Hub  (uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub)
      Petition approvals/denials per employer per fiscal year. CSV downloads
      exist for FY2009-2023; newer years must be exported by hand from the
      Tableau "Crosstab View" and dropped into .cache/h1b/uscis/.

Commands
  fetch  [--fy 2026] [--q 3]      download the DOL workbook into .cache/h1b/raw/
  build  <xlsx> [--fy --q]        stream-parse the workbook into .cache/h1b/lca_FY<fy>_Q<q>.csv
                                  Coverage varies: FY2026_Q3 held Oct 2025–Jun 2026 (cumulative),
                                  FY2025_Q4 held only Jul–Sep 2025. Build every file you want
                                  covered; overlapping cases are de-duplicated at query time.
  rank   [filters]                employers ranked by transfer (change-of-employer) LCAs
  lookup <name-regex>             everything we know about one employer

rank / lookup filters
  --state GA,TX        worksite state(s)
  --title "regex"      job title regex (case-insensitive)
  --naics 33,54        NAICS prefix(es) — 2..6 digits
  --exclude-naics 5613 drop NAICS prefix(es)
  --direct             drop staffing firms (NAICS 5613) and H-1B-dependent employers,
                       i.e. show companies that hire for themselves
  --fy 2026            restrict to one fiscal year (default: all built years)
  --min-transfer N     rank: hide employers with fewer transfer positions
  --top N              rank: rows to print (default 40)
  --all-status         include non-certified cases (default: Certified only)
  --json               machine-readable output

Stdlib only (xlsx is parsed as zip+XML). Build takes a few minutes for a
~1M-row workbook; rank/lookup read the slim CSV in seconds.
Usage: python3 scripts/h1b_sponsors.py <command> [args]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import ssl
import statistics
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / ".cache" / "h1b"   # 공공 데이터 캐시 — 개인정보 아님. 재생성 가능 (2026-10-21 data/h1b 에서 이동)
RAW = DATA / "raw"
USCIS_DIR = DATA / "uscis"

# DOL does not keep a stable URL pattern; known exact links first, then guesses.
DOL_KNOWN = {
    (2026, 3): "https://www.dol.gov//media/LCA_Disclosure_Data_FY2026_Q3.xlsx",
    (2025, 4): "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs/LCA_Disclosure_Data_FY2025_Q4.xlsx",
}
DOL_PATTERNS = [
    "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs/LCA_Disclosure_Data_FY{fy}_Q{q}.xlsx",
    "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs/FY{yy}Q{q}/LCA_Disclosure_Data_FY{fy}_Q{q}.xlsx",
    "https://www.dol.gov//media/LCA_Disclosure_Data_FY{fy}_Q{q}.xlsx",
]
USCIS_CSV = "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-{fy}.csv"

# Columns kept in the slim CSV (DOL header → slim name). Order matters.
KEEP = [
    ("CASE_NUMBER", "case"), ("CASE_STATUS", "status"), ("RECEIVED_DATE", "received"),
    ("DECISION_DATE", "decided"), ("VISA_CLASS", "visa"), ("JOB_TITLE", "title"),
    ("SOC_CODE", "soc"), ("SOC_TITLE", "soc_title"), ("FULL_TIME_POSITION", "full_time"),
    ("BEGIN_DATE", "begin"), ("TOTAL_WORKER_POSITIONS", "positions"),
    ("NEW_EMPLOYMENT", "new"), ("CONTINUED_EMPLOYMENT", "continued"),
    ("CHANGE_PREVIOUS_EMPLOYMENT", "change_prev"), ("NEW_CONCURRENT_EMPLOYMENT", "concurrent"),
    ("CHANGE_EMPLOYER", "transfer"), ("AMENDED_PETITION", "amended"),
    ("EMPLOYER_NAME", "employer"), ("TRADE_NAME_DBA", "dba"), ("EMPLOYER_CITY", "emp_city"),
    ("EMPLOYER_STATE", "emp_state"), ("EMPLOYER_FEIN", "fein"), ("NAICS_CODE", "naics"),
    ("WORKSITE_CITY", "ws_city"), ("WORKSITE_STATE", "ws_state"),
    ("WAGE_RATE_OF_PAY_FROM", "wage_from"), ("WAGE_RATE_OF_PAY_TO", "wage_to"),
    ("WAGE_UNIT_OF_PAY", "wage_unit"), ("PREVAILING_WAGE", "pw"), ("PW_WAGE_LEVEL", "pw_level"),
    ("H_1B_DEPENDENT", "h1b_dependent"), ("WILLFUL_VIOLATOR", "willful_violator"),
]
DATE_COLS = {"received", "decided", "begin"}
INT_COLS = {"positions", "new", "continued", "change_prev", "concurrent", "transfer", "amended"}
ANNUAL = {"Year": 1, "Month": 12, "Bi-Weekly": 26, "Week": 52, "Hour": 2080}


# ── helpers ───────────────────────────────────────────────────────────────────

def _ssl_ctx() -> ssl.SSLContext:
    # Corporate TLS inspection re-signs certs; fall back to unverified if needed.
    try:
        ctx = ssl.create_default_context()
        urllib.request.urlopen("https://www.dol.gov", context=ctx, timeout=15).close()
        return ctx
    except Exception:
        return ssl._create_unverified_context()


def _download(url: str, dest: Path) -> bool:
    ok = _download_urllib(url, dest)
    if not ok and shutil.which("curl"):
        # uscis.gov's CDN rejects python's TLS/urllib fingerprint but accepts curl.
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["curl", "-sS", "-L", "-k", "--fail", "--max-time", "900", "-o", str(dest), url])
        ok = r.returncode == 0 and dest.exists() and dest.stat().st_size > 0
        if not ok and dest.exists():
            dest.unlink()
    return ok


def _download_urllib(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "job-finder/1.0"})
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=60) as r:
            if r.status != 200:
                return False
            dest.parent.mkdir(parents=True, exist_ok=True)
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r  {done / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", file=sys.stderr)
            print(file=sys.stderr)
            return True
    except Exception as e:  # 404 raises HTTPError
        print(f"  {url} → {e}", file=sys.stderr)
        return False


def _col_index(ref: str) -> int:
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return n - 1


def _serial_to_date(v: str) -> str:
    try:
        return (datetime(1899, 12, 30) + timedelta(days=float(v))).strftime("%Y-%m-%d")
    except ValueError:
        return v


def _annual(row: dict) -> float | None:
    try:
        w = float(row["wage_from"] or 0)
    except ValueError:
        return None
    mult = ANNUAL.get(row["wage_unit"])
    return w * mult if w and mult else None


def _fmt_money(x: float | None) -> str:
    return f"${x / 1000:,.0f}k" if x else "-"


# ── build: xlsx → slim csv ────────────────────────────────────────────────────

def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    out: list[str] = []
    buf: list[str] = []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with z.open("xl/sharedStrings.xml") as f:
        for ev, el in ET.iterparse(f, events=("end",)):
            if el.tag == ns + "t":
                buf.append(el.text or "")
            elif el.tag == ns + "si":
                out.append("".join(buf))
                buf.clear()
                el.clear()
    return out


def _iter_rows(z: zipfile.ZipFile, sheet: str):
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    sst = _shared_strings(z)
    with z.open(sheet) as f:
        for ev, el in ET.iterparse(f, events=("end",)):
            if el.tag != ns + "row":
                continue
            cells: dict[int, str] = {}
            for c in el:
                ref = c.get("r", "")
                t = c.get("t")
                v = c.find(ns + "v")
                if t == "inlineStr":
                    is_ = c.find(ns + "is")
                    val = "".join(x.text or "" for x in is_.iter(ns + "t")) if is_ is not None else ""
                elif v is None:
                    val = ""
                elif t == "s":
                    val = sst[int(v.text)]
                else:
                    val = v.text or ""
                cells[_col_index(ref)] = val
            el.clear()
            yield cells


def cmd_build(args: argparse.Namespace) -> int:
    src = Path(args.xlsx)
    if not src.exists():
        print(f"no such file: {src}", file=sys.stderr)
        return 2
    m = re.search(r"FY_?(\d{4})_Q(\d)", src.name)
    fy = args.fy or (m and m.group(1))
    q = args.q or (m and m.group(2))
    if not (fy and q):
        print("cannot infer fiscal year/quarter from filename; pass --fy and --q", file=sys.stderr)
        return 2
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / f"lca_FY{fy}_Q{q}.csv"
    z = zipfile.ZipFile(src)
    sheet = next(n for n in sorted(z.namelist()) if n.startswith("xl/worksheets/sheet"))
    rows = _iter_rows(z, sheet)
    header = next(rows)
    hidx = {name: i for i, name in header.items()}
    missing = [src_col for src_col, _ in KEEP if src_col not in hidx]
    if missing:
        print(f"workbook lacks expected columns: {missing}", file=sys.stderr)
        return 2
    n = kept = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([slim for _, slim in KEEP])
        for cells in rows:
            if not cells.get(hidx["CASE_NUMBER"]):
                continue  # Excel pads the sheet with ~600k formatted-but-empty rows
            n += 1
            if cells.get(hidx["VISA_CLASS"], "") != "H-1B":
                continue
            rec = []
            for src_col, slim in KEEP:
                v = cells.get(hidx[src_col], "")
                if slim in DATE_COLS and v and v[0].isdigit() and "-" not in v:
                    v = _serial_to_date(v)
                elif slim in INT_COLS:
                    v = str(int(float(v))) if v else "0"
                rec.append(v.strip() if isinstance(v, str) else v)
            w.writerow(rec)
            kept += 1
            if n % 100000 == 0:
                print(f"\r  {n:,} rows read, {kept:,} H-1B kept", end="", file=sys.stderr)
    print(f"\n  wrote {out} ({kept:,} H-1B cases of {n:,} rows)", file=sys.stderr)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    fy, q = args.fy, args.q
    dest = RAW / f"LCA_Disclosure_Data_FY{fy}_Q{q}.xlsx"
    if dest.exists() and not args.force:
        print(f"already have {dest}; use --force to re-download", file=sys.stderr)
        return 0
    urls = [DOL_KNOWN[(fy, q)]] if (fy, q) in DOL_KNOWN else []
    urls += [p.format(fy=fy, yy=str(fy)[2:], q=q) for p in DOL_PATTERNS]
    for url in urls:
        print(f"trying {url}", file=sys.stderr)
        if _download(url, dest):
            print(f"saved {dest}\nnext: python3 scripts/h1b_sponsors.py build \"{dest}\"", file=sys.stderr)
            return 0
    print("no URL worked — open dol.gov/agencies/eta/foreign-labor/performance and download by hand "
          f"into {RAW}/", file=sys.stderr)
    return 1


def cmd_fetch_uscis(args: argparse.Namespace) -> int:
    dest = USCIS_DIR / f"uscis_FY{args.fy}.csv"
    if _download(USCIS_CSV.format(fy=args.fy), dest):
        print(f"saved {dest}", file=sys.stderr)
        return 0
    print("USCIS only publishes CSVs for FY2009-2023; for newer years export the Tableau "
          f"'Crosstab View' as CSV and save it as {dest}", file=sys.stderr)
    return 1


# ── query side ────────────────────────────────────────────────────────────────

def _load_cases(args: argparse.Namespace):
    files = sorted(DATA.glob("lca_FY*.csv"))
    if args.fy:
        files = [f for f in files if f.name.startswith(f"lca_FY{args.fy}_")]
    if not files:
        print(f"no built data in {DATA}. Run: fetch → build", file=sys.stderr)
        sys.exit(2)
    states = {s.strip().upper() for s in args.state.split(",")} if args.state else None
    title_re = re.compile(args.title, re.I) if args.title else None
    naics = tuple(n.strip() for n in args.naics.split(",")) if args.naics else None
    ex_naics = tuple(n.strip() for n in args.exclude_naics.split(",")) if args.exclude_naics else ()
    if args.direct:
        ex_naics += ("5613",)  # employment services = staffing / body shops
    seen: set[str] = set()  # DOL files sometimes overlap (cumulative vs quarterly); newest file wins
    for f in reversed(files):
        fy = re.search(r"FY(\d{4})", f.name).group(1)
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["case"] in seen:
                    continue
                seen.add(row["case"])
                if not args.all_status and row["status"] != "Certified":
                    continue
                if states and row["ws_state"].upper() not in states:
                    continue
                if title_re and not title_re.search(row["title"]):
                    continue
                if naics and not row["naics"].startswith(naics):
                    continue
                if ex_naics and row["naics"].startswith(ex_naics):
                    continue
                if args.direct and row["h1b_dependent"] == "Yes":
                    continue  # >15% H-1B workforce: almost always consultancies
                row["fy"] = fy
                yield row


def _aggregate(rows):
    agg: dict[str, dict] = {}
    for r in rows:
        key = r["fein"] or r["employer"].upper()
        a = agg.get(key)
        if a is None:
            a = agg[key] = {
                "fein": r["fein"], "names": Counter(), "cases": 0, "positions": 0,
                "transfer": 0, "new": 0, "continued": 0, "amended": 0,
                "states": Counter(), "titles": Counter(), "wages": [], "fys": set(),
                "naics": Counter(), "dependent": r["h1b_dependent"], "violator": r["willful_violator"],
            }
        a["names"][r["employer"]] += 1
        a["cases"] += 1
        for k in ("positions", "transfer", "new", "continued", "amended"):
            a[k] += int(r[k] or 0)
        a["states"][r["ws_state"]] += 1
        a["titles"][r["title"]] += 1
        a["naics"][r["naics"]] += 1
        a["fys"].add(r["fy"])
        if (w := _annual(r)) is not None:
            a["wages"].append(w)
    for a in agg.values():
        a["name"] = a["names"].most_common(1)[0][0]
        a["median_wage"] = statistics.median(a["wages"]) if a["wages"] else None
    return agg


def cmd_rank(args: argparse.Namespace) -> int:
    agg = _aggregate(_load_cases(args))
    ranked = sorted(agg.values(), key=lambda a: (a["transfer"], a["positions"]), reverse=True)
    ranked = [a for a in ranked if a["transfer"] >= args.min_transfer][: args.top]
    if args.json:
        print(json.dumps([{k: (sorted(v) if isinstance(v, set) else v) for k, v in a.items()
                           if k not in ("names", "wages", "states", "titles", "naics")}
                          | {"top_states": a["states"].most_common(3), "top_titles": a["titles"].most_common(5)}
                          for a in ranked], ensure_ascii=False, indent=1))
        return 0
    print(f"{'#':>3} {'transfer':>8} {'new':>5} {'total':>6} {'median':>7}  employer  [top worksite states]  top titles")
    for i, a in enumerate(ranked, 1):
        st = ",".join(f"{s}:{n}" for s, n in a["states"].most_common(3))
        tt = " | ".join(t[:38] for t, _ in a["titles"].most_common(3))
        print(f"{i:>3} {a['transfer']:>8} {a['new']:>5} {a['positions']:>6} {_fmt_money(a['median_wage']):>7}  "
              f"{a['name'][:40]}  [{st}]  {tt}")
    print(f"\n{len(agg):,} employers matched; showing {len(ranked)}. "
          "transfer = CHANGE_EMPLOYER positions on certified LCAs (FY "
          + ",".join(sorted({fy for a in agg.values() for fy in a['fys']})) + ")")
    return 0


def _uscis_rows(pattern: re.Pattern):
    for f in sorted(USCIS_DIR.glob("*.csv")):
        with open(f, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                name = row.get("Employer") or row.get("Employer (Petitioner) Name") or ""
                if pattern.search(name):
                    yield row


def cmd_lookup(args: argparse.Namespace) -> int:
    pat = re.compile(args.name, re.I)
    rows = [r for r in _load_cases(args) if pat.search(r["employer"]) or pat.search(r["dba"])]
    agg = _aggregate(rows)
    if args.json:
        print(json.dumps({"lca": [{k: v for k, v in a.items() if k not in ("names", "wages", "states", "titles", "naics")}
                                  | {"fys": sorted(a["fys"]), "top_states": a["states"].most_common(5),
                                     "top_titles": a["titles"].most_common(8)} for a in agg.values()],
                          "cases": rows[-50:], "uscis": list(_uscis_rows(pat))}, ensure_ascii=False, indent=1, default=str))
        return 0
    if not agg:
        print(f"no certified H-1B LCA matched /{args.name}/ in the built fiscal years "
              f"(try --all-status, or a looser pattern)")
    for a in sorted(agg.values(), key=lambda a: a["positions"], reverse=True):
        print(f"\n■ {a['name']}  (FEIN {a['fein'] or '?'}, NAICS {a['naics'].most_common(1)[0][0]})"
              f"  FY{','.join(sorted(a['fys']))}")
        if len(a["names"]) > 1:
            print("  aka: " + "; ".join(n for n, _ in a["names"].most_common(4)[1:]))
        print(f"  certified LCAs {a['cases']}  positions {a['positions']}  "
              f"→ transfer {a['transfer']} · new {a['new']} · extension {a['continued']} · amended {a['amended']}")
        print(f"  median offered wage {_fmt_money(a['median_wage'])}   "
              f"H-1B dependent: {a['dependent']}   willful violator: {a['violator']}")
        print("  worksites: " + ", ".join(f"{s} ({n})" for s, n in a["states"].most_common(6)))
        print("  titles:    " + " | ".join(f"{t} ({n})" for t, n in a["titles"].most_common(6)))
    recent = sorted(rows, key=lambda r: r["decided"], reverse=True)[: args.top]
    if recent:
        print(f"\n  most recent {len(recent)} certified cases:")
        for r in recent:
            kind = "transfer" if r["transfer"] != "0" else "new" if r["new"] != "0" else \
                "ext" if r["continued"] != "0" else "amend/other"
            print(f"   {r['decided']}  {kind:<9} {r['title'][:36]:<36} {r['ws_city']}, {r['ws_state']}"
                  f"  {_fmt_money(_annual(r))}  L{r['pw_level'] or '?'}")
    us = list(_uscis_rows(pat))
    if us:
        print("\n  USCIS Employer Data Hub (petition decisions; FY2009-23 lump transfers into 'Continuing'):")
        by_fy: dict[str, Counter] = defaultdict(Counter)
        for r in us:
            fy = r.get("Fiscal Year") or r.get("Fiscal Year ") or "?"
            for k, v in r.items():
                if k and ("Approval" in k or "Denial" in k):
                    try:
                        by_fy[fy][k.strip()] += int(v or 0)
                    except ValueError:
                        pass
        for fy in sorted(by_fy):
            print(f"   FY{fy}: " + "  ".join(f"{k}={v}" for k, v in by_fy[fy].items() if v))
    elif not USCIS_DIR.exists() or not any(USCIS_DIR.glob("*.csv")):
        print("\n  (no USCIS data; run fetch-uscis --fy 2023 or drop a Tableau export into .cache/h1b/uscis/)")
    return 0


# ── cli ───────────────────────────────────────────────────────────────────────

def _add_filters(p: argparse.ArgumentParser) -> None:
    p.add_argument("--state")
    p.add_argument("--title")
    p.add_argument("--naics")
    p.add_argument("--exclude-naics")
    p.add_argument("--direct", action="store_true",
                   help="drop staffing firms (NAICS 5613) and H-1B-dependent employers")
    p.add_argument("--fy")
    p.add_argument("--all-status", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--top", type=int, default=40)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch"); p.add_argument("--fy", type=int, default=2026); p.add_argument("--q", type=int, default=3)
    p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("fetch-uscis"); p.add_argument("--fy", type=int, default=2023); p.set_defaults(fn=cmd_fetch_uscis)
    p = sub.add_parser("build"); p.add_argument("xlsx"); p.add_argument("--fy"); p.add_argument("--q"); p.set_defaults(fn=cmd_build)
    p = sub.add_parser("rank"); _add_filters(p); p.add_argument("--min-transfer", type=int, default=1); p.set_defaults(fn=cmd_rank)
    p = sub.add_parser("lookup"); p.add_argument("name"); _add_filters(p); p.set_defaults(fn=cmd_lookup)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
