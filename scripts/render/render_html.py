"""Render resume.json -> resume.html + resume.md (letter, print-ready). stdlib only.

Run:  <PY> scripts/render/render_html.py data/cache/tailored/<stable-id>/
Writes into the same folder. PDF: chrome --headless --print-to-pdf, or print from the browser.

Sub-bullets: bullets listed in render.json `sub_ids` nest under the preceding (umbrella) bullet.
Education renders every entry; an in-progress degree shows "start – expected YYYY" from its highlights.
The contact line prints address, relocation openness and the work-authorization line — nothing hidden.
"""
import html
import re

from _common import (auth_line, edu_when, fmt_date, group_by_company, link_label, load, location_line,
                     primary_link, skill_label, work_dir)

NL = "\n"


def esc(s):
    return html.escape(s, quote=False).replace(" → ", "&nbsp;→&nbsp;").replace(" – ", "&nbsp;–&nbsp;")


def emph(text):
    """Bold a leading 'Label —' prefix on sub-bullets."""
    m = re.match(r"^([A-Z][^—]{3,40}) — (.*)$", text)
    if m:
        return f"<strong>{esc(m.group(1))}</strong> — {esc(m.group(2))}"
    return esc(text)


def bullets_html(bullets, sub_ids):
    parts = []
    open_sub = False
    for i, bl in enumerate(bullets):
        is_sub = bl["id"] in sub_ids
        nxt_sub = i + 1 < len(bullets) and bullets[i + 1]["id"] in sub_ids
        if is_sub:
            if not open_sub:
                parts.append("      <ul>" + NL)
                open_sub = True
            parts.append(f"        <li>{emph(bl['text'])}</li>" + NL)
            if not nxt_sub:
                parts.append("      </ul></li>" + NL)
                open_sub = False
        else:
            parts.append(f"    <li>{esc(bl['text'])}")
            if not nxt_sub:
                parts.append("</li>" + NL)
    return "".join(parts)


def main():
    d = work_dir()
    r, opts = load(d)
    sub_ids = set(opts.get("sub_ids", []))
    b = r["basics"]
    loc_line = location_line(b)
    if b.get("location", {}).get("willing_to_relocate"):
        loc_line += " · open to relocation"
    auth = auth_line(b, opts)
    link = primary_link(b)
    langs = " · ".join(f"{l['name']} ({l['proficiency']})" for l in r.get("languages", []))
    groups = group_by_company(r["experience"])
    edu = r.get("education", [])

    contact = [esc(loc_line), esc(b.get("phone", "")), f'<a href="mailto:{b["email"]}">{b["email"]}</a>']
    if link:
        contact.append(f'<a href="{link}">{link_label(link)}</a>')
    if auth:
        contact.append(f"Work authorization: {esc(auth)}")
    contact = " &nbsp;·&nbsp; ".join(c for c in contact if c)

    # ------------------------------------------------------------ HTML
    out = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{esc(b['name'])} — Resume</title>
<style>
  @page {{ size: letter; margin: 0; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 8.5in; }}
  body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 8.75pt; line-height: 1.18; color: #1a1a1a;
    padding: 0.25in 0.47in 0.18in;
    -webkit-print-color-adjust: exact;
  }}
  h1 {{ font-size: 19pt; font-weight: 700; letter-spacing: 0.5px; }}
  .headline {{ font-size: 10.3pt; font-weight: 600; color: #2b4a6f; margin-top: 2px; }}
  .contact {{ font-size: 8.7pt; color: #444; margin-top: 3px; }}
  .contact a {{ color: #444; text-decoration: none; }}
  .summary {{ margin-top: 5px; font-size: 9pt; color: #222; }}
  h2 {{
    font-size: 10pt; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px;
    color: #2b4a6f; border-bottom: 1.2px solid #2b4a6f; margin: 5px 0 3px; padding-bottom: 1px;
  }}
  .job {{ margin-bottom: 4px; }}
  .job-title .company {{ font-size: 10.2pt; }}
  .roles {{ margin-left: 0.16in; padding-left: 0.12in; border-left: 1.5px solid #c9d3de; }}
  .role-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-top: 3px; }}
  .role-header .role {{ font-size: 9.5pt; font-weight: 600; color: #333; }}
  .job-header {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .job-title {{ font-size: 10pt; font-weight: 700; }}
  .job-meta {{ font-size: 8.7pt; color: #555; white-space: nowrap; }}
  ul {{ margin: 2px 0 0 13px; }}
  li {{ margin-bottom: 2px; padding-left: 2px; }}
  ul ul {{ margin: 1.5px 0 1px 12px; }}
  ul ul li {{ margin-bottom: 1px; font-size: 8.8pt; }}
  .skills-grid {{ display: grid; grid-template-columns: 0.95in 1fr; row-gap: 2px; }}
  .skills-grid .cat {{ font-weight: 700; font-size: 8.9pt; }}
  .edu-header {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .edu-header + .edu-header {{ margin-top: 2px; }}
  .edu-detail {{ font-size: 8.9pt; color: #444; }}
  strong {{ font-weight: 700; }}
</style>
</head>
<body>

<h1>{esc(b['name'])}</h1>
<div class="headline">{esc(b.get('headline', '').replace('•', '·'))}</div>
<div class="contact">
  {contact}
</div>

<div class="summary">{esc(b.get('summary', ''))}</div>

<h2>Experience</h2>
"""]

    for roles in groups:
        first, last = roles[0], roles[-1]          # experience is newest-first
        span = f"{fmt_date(last['start_date'])} – {fmt_date(first.get('end_date'))}"
        meta = " · ".join(x for x in (first.get("location"), span) if x)
        out.append(f"""<div class="job">
  <div class="job-header">
    <div class="job-title"><span class="company">{esc(first['company'])}</span></div>
    <div class="job-meta">{esc(meta)}</div>
  </div>
  <div class="roles">
""")
        for e in roles:
            dates = f"{fmt_date(e['start_date'])} – {fmt_date(e.get('end_date'))}"
            out.append(f"""  <div class="role-header">
    <div class="role">{esc(e['role'])}</div>
    <div class="job-meta">{dates}</div>
  </div>
  <ul>
""")
            out.append(bullets_html(e["bullets"], sub_ids))
            out.append("  </ul>" + NL)
        out.append("  </div>" + NL + "</div>" + NL + NL)

    if r.get("skills"):
        out.append("<h2>Skills</h2>" + NL + '<div class="skills-grid">' + NL)
        for key, items in r["skills"].items():
            parts = [esc(it["name"] + (f" ({it['years']} yr)" if it.get("years") else "")) for it in items]
            out.append(f'  <div class="cat">{esc(skill_label(key))}</div><div>{" · ".join(parts)}</div>' + NL)
        out.append("</div>" + NL + NL)

    if edu:
        out.append("<h2>Education</h2>" + NL)
    for i, ed in enumerate(edu):
        field = esc(ed.get("field", "").split(" — ")[0])
        deg = ed["degree"].replace(" (in progress)", "")
        prog = " (in progress)" if "in progress" in ed["degree"] else ""
        tail = f", GPA {esc(ed['gpa'])}" if ed.get("gpa") else ""
        out.append(f"""<div class="edu-header">
  <div><strong>{esc(ed['institution'])}</strong> — {esc(deg)} {field}{prog}{tail}</div>
  <div class="job-meta">{edu_when(ed)}</div>
</div>
""")
        if ed.get("end_date"):  # completed degree: honors line; languages ride on the last one
            detail = esc(" · ".join(ed.get("highlights", [])))
            if i == len(edu) - 1 and langs:
                detail += f" &nbsp;·&nbsp; Languages: {esc(langs)}"
            out.append(f'<div class="edu-detail">{detail}</div>' + NL)

    out.append(NL + "</body>" + NL + "</html>" + NL)
    (d / "resume.html").write_text("".join(out), encoding="utf-8")
    print(f"wrote {d / 'resume.html'}")

    # ------------------------------------------------------------ Markdown
    contact_md = [loc_line, b.get("phone", ""), b["email"]]
    if link:
        contact_md.append(f"[{link_label(link)}]({link})")
    if auth:
        contact_md.append(f"Work authorization: {auth}")
    md = [f"# {b['name']}" + NL, f"**{b.get('headline', '').replace('•', '·')}**" + NL,
          " · ".join(c for c in contact_md if c) + NL,
          b.get("summary", "") + NL, "---" + NL, "## Experience" + NL]
    for roles in groups:
        first, last = roles[0], roles[-1]
        span = f"{fmt_date(last['start_date'])} – {fmt_date(first.get('end_date'))}"
        md.append(f"### {first['company']} — {' · '.join(x for x in (first.get('location'), span) if x)}" + NL)
        for e in roles:
            md.append(f"**{e['role']}** · {fmt_date(e['start_date'])} – {fmt_date(e.get('end_date'))}" + NL)
            for bl in e["bullets"]:
                md.append(("  - " if bl["id"] in sub_ids else "- ") + bl["text"])
            md.append("")
    if r.get("skills"):
        md += ["---" + NL, "## Skills" + NL, "| Category | |", "|---|---|"]
        for key, items in r["skills"].items():
            parts = [it["name"] + (f" ({it['years']}y)" if it.get("years") else "") for it in items]
            md.append(f"| **{skill_label(key)}** | {' · '.join(parts)} |")
        md.append("")
    if edu:
        md += ["---" + NL, "## Education" + NL]
    for ed in edu:
        gpa = f" · GPA {ed['gpa']}" if ed.get("gpa") else ""
        md.append(f"**{ed['institution']}** — {ed['degree']} {ed.get('field', '')} · {edu_when(ed)}{gpa}  ")
        if ed.get("end_date"):  # completed degree only; an in-progress degree shows just its title line
            md.append(" · ".join(ed.get("highlights", [])))
        md.append("")
    if langs:
        md += ["**Languages:** " + langs, ""]
    (d / "resume.md").write_text(NL.join(md), encoding="utf-8")
    print(f"wrote {d / 'resume.md'}")


if __name__ == "__main__":
    main()
