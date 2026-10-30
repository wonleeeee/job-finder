#!/usr/bin/env python3
"""
Build machine-readable resume variants from resume.json. stdlib only.

Run:  <PY> scripts/render/build_machine_readable.py data/cache/tailored/<stable-id>/
Emits into <work folder>/machine/ :
    resume-ats.html        -> print to resume-ats.pdf (text-selectable, 11pt Arial, 0.75in)
    resume-designed.html   -> same facts and parser-safe rules, set for a human eye (2 pages max)
    resume-ats.docx        -> minimal OOXML, single column, no tables/boxes (Taleo/Workday preference)
    resume-ats.txt         -> plain text for paste-into-textarea fields and legacy parsers
    resume-llm.md          -> Markdown for LLM/RAG-based parsers
    resume-jsonresume.json -> JSON Resume schema (jsonresume.org)

Sanitization applied to every output (ATS spec):
    no arrows, no multiplication sign, no en/em dashes, no bullet glyphs other than "- ",
    no smart quotes, no icons, no tables, no columns, no header/footer, standard section names,
    "Month YYYY" date format so parsers can compute years of experience.
    Glyphs in resume.json are translated to ASCII (ASCII table below); anything still non-ASCII is reported.

render.json `bold` (optional) lists phrases to bold in resume-designed.html, matched after sanitizing.
"""

import json
import os
import zipfile

from _common import (auth_line, availability, edu_when, fmt_date, load, primary_link, skill_label,
                     work_dir)

ASCII = [
    (" → ", " to "), ("→", " to "), ("×", "x"), (" — ", " - "), (" – ", " - "), ("—", "-"), ("–", "-"),
    ("•", "-"), ("▹", "-"), ("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), ("…", "..."),
    (" · ", ", "), ("·", ","), ("≈", "~"), ("≥", ">="), ("≤", "<="), (" ", " "),
]
COUNTRIES = {"US": "United States", "KR": "South Korea", "CA": "Canada"}


def clean(text):
    for a, b in ASCII:
        text = text.replace(a, b)
    return text


# ---------------------------------------------------------------- content ---

def extract(r, opts):
    """resume.json -> flat, sanitized content used by every output."""
    b = r["basics"]
    loc = b.get("location", {})
    place = ", ".join(x for x in (loc.get("city"), loc.get("region"), COUNTRIES.get(loc.get("country"), loc.get("country"))) if x)
    avail = availability(b)
    auth = auth_line(b, opts)
    basics = {
        "name": b["name"],
        "title": clean(b.get("headline", "")),
        "location": place,
        "remote": avail[:1].upper() + avail[1:] if avail else "",
        "phone": b.get("phone", ""),
        "email": b["email"],
        "linkedin": primary_link(b),
        "authorization": clean(f"US work authorization: {auth}") if auth else "",
        "city": loc.get("city", ""), "region": loc.get("region", ""), "country": loc.get("country", ""),
    }
    work = [{
        "company": clean(e["company"]),
        "title": clean(e["role"]),
        "location": clean(e.get("location", "")),
        "start": fmt_date(e["start_date"], long=True),
        "end": fmt_date(e.get("end_date"), long=True),
        "iso_start": e["start_date"][:7],
        "iso_end": e["end_date"][:7] if e.get("end_date") else None,
        "bullets": [clean(bl["text"]) for bl in e["bullets"]],
    } for e in r["experience"]]
    skills = [(skill_label(k), clean(", ".join(it["name"] + (f" ({it['years']} years)" if it.get("years") else "") for it in items)))
              for k, items in r.get("skills", {}).items()]
    education = [{
        "institution": clean(ed["institution"]),
        "degree": clean(ed["degree"]),
        "field": clean(ed.get("field", "").split(" — ")[0]),
        "when": clean(edu_when(ed, long=True)),
        "iso_start": ed["start_date"][:7] if ed.get("start_date") else None,
        "iso_end": ed["end_date"][:7] if ed.get("end_date") else None,
        "gpa": ed.get("gpa", ""),
        # an in-progress degree's highlights are status notes, not honors
        "highlights": [clean(h) for h in ed.get("highlights", [])] if ed.get("end_date") else [],
    } for ed in r.get("education", [])]
    langs = [(clean(l["name"]), clean(l["proficiency"])) for l in r.get("languages", [])]
    return basics, clean(b.get("summary", "")), work, skills, education, langs


def contact_lines(B):
    return [B[k] for k in ("location", "phone", "email", "linkedin", "remote", "authorization") if B[k]]


def edu_meta(ed):
    return ("Graduated %s" % ed["when"] if ed["iso_end"] else ed["when"]) + (", GPA %s" % ed["gpa"] if ed["gpa"] else "")


# ------------------------------------------------------------------- text ---

def build_txt(B, summary, work, skills, education, langs):
    L = [B["name"], B["title"], ""] + contact_lines(B)
    L += ["", "SUMMARY", "", summary, "", "WORK EXPERIENCE"]
    for job in work:
        L += ["", job["title"], job["company"], job["location"], "%s - %s" % (job["start"], job["end"]), ""]
        L += ["- " + b for b in job["bullets"]]
    L += ["", "SKILLS", ""] + ["%s: %s" % s for s in skills]
    L += ["", "EDUCATION"]
    for ed in education:
        L += ["", "%s in %s" % (ed["degree"], ed["field"]), ed["institution"], edu_meta(ed)]
        L += ["- " + h for h in ed["highlights"]]
    if langs:
        L += ["", "LANGUAGES", ""] + ["%s: %s" % l for l in langs]
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------- markdown ---

def build_md(B, summary, work, skills, education, langs):
    L = ["# %s" % B["name"], "", B["title"], ""]
    for label, k in (("Location", "location"), ("Phone", "phone"), ("Email", "email"), ("LinkedIn", "linkedin"),
                     ("Availability", "remote"), ("Work authorization", "authorization")):
        if B[k]:
            L.append("- %s: %s" % (label, B[k]))
    L += ["", "## Summary", "", summary, "", "## Work Experience"]
    for job in work:
        L += ["", "### %s" % job["title"], "", "- Company: %s" % job["company"], "- Location: %s" % job["location"],
              "- Dates: %s - %s" % (job["start"], job["end"]), ""]
        L += ["- %s" % b for b in job["bullets"]]
    L += ["", "## Skills", ""] + ["- **%s:** %s" % s for s in skills]
    L += ["", "## Education"]
    for ed in education:
        L += ["", "### %s in %s" % (ed["degree"], ed["field"]), "", "- Institution: %s" % ed["institution"],
              "- %s" % edu_meta(ed)]
        L += ["- %s" % h for h in ed["highlights"]]
    if langs:
        L += ["", "## Languages", ""] + ["- %s: %s" % l for l in langs]
    L.append("")
    return "\n".join(L)


# ------------------------------------------------------------ json resume ---

def build_jsonresume(B, summary, work, skills, education, langs):
    profiles = []
    if B["linkedin"]:
        profiles.append({"network": "LinkedIn", "username": B["linkedin"].rstrip("/").rsplit("/", 1)[-1],
                         "url": B["linkedin"]})
    return json.dumps({
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": {
            "name": B["name"], "label": B["title"], "email": B["email"], "phone": B["phone"],
            "url": B["linkedin"], "summary": summary,
            "location": {"city": B["city"], "region": B["region"], "countryCode": B["country"]},
            "profiles": profiles,
        },
        "work": [{
            "name": j["company"], "position": j["title"], "location": j["location"], "startDate": j["iso_start"],
            **({"endDate": j["iso_end"]} if j["iso_end"] else {}),
            "highlights": j["bullets"],
        } for j in work],
        "education": [{
            "institution": ed["institution"], "studyType": ed["degree"], "area": ed["field"],
            **({"startDate": ed["iso_start"]} if ed["iso_start"] else {}),
            **({"endDate": ed["iso_end"]} if ed["iso_end"] else {}),
            **({"score": ed["gpa"]} if ed["gpa"] else {}),
            "courses": ed["highlights"],
        } for ed in education],
        "skills": [{"name": cat, "keywords": [s.strip() for s in val.split(",")]} for cat, val in skills],
        "languages": [{"language": n, "fluency": f} for n, f in langs],
    }, indent=2, ensure_ascii=True)


# ------------------------------------------------------------------- html ---

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


ATS_CSS = """
  /* ATS spec: single column, Arial 11pt, 0.75in margins, no color,
     no tables, no text boxes, no header/footer, standard section names. */
  @page { size: letter; margin: 0.75in; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 11pt; line-height: 1.15; color: #000000; }
  h1 { font-size: 20pt; font-weight: bold; margin-bottom: 4pt; }
  .title { font-size: 12pt; margin-bottom: 8pt; }
  .contact { font-size: 11pt; margin-bottom: 4pt; }
  h2 { font-size: 14pt; font-weight: bold; margin-top: 14pt; margin-bottom: 6pt; }
  h3 { font-size: 12pt; font-weight: bold; margin-top: 10pt; }
  .meta { font-size: 11pt; margin-bottom: 4pt; }
  ul { margin: 0 0 0 18pt; }
  li { margin-bottom: 5pt; }
  p { margin-bottom: 6pt; }
"""


def build_html(B, summary, work, skills, education, langs):
    P = ['<!DOCTYPE html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
         '<title>%s - Resume (ATS)</title>' % esc(B["name"]), '<style>%s</style>' % ATS_CSS, '</head>', '<body>']
    P.append("<h1>%s</h1>" % esc(B["name"]))
    P.append('<div class="title">%s</div>' % esc(B["title"]))
    P += ['<div class="contact">%s</div>' % esc(c) for c in contact_lines(B)]

    P += ["<h2>Summary</h2>", "<p>%s</p>" % esc(summary), "<h2>Work Experience</h2>"]
    for job in work:
        P.append("<h3>%s</h3>" % esc(job["title"]))
        P.append('<div class="meta">%s</div>' % esc(job["company"]))
        P.append('<div class="meta">%s</div>' % esc(job["location"]))
        P.append('<div class="meta">%s - %s</div>' % (esc(job["start"]), esc(job["end"])))
        P += ["<ul>"] + ["<li>%s</li>" % esc(b) for b in job["bullets"]] + ["</ul>"]

    P.append("<h2>Skills</h2>")
    P += ["<p><b>%s:</b> %s</p>" % (esc(c), esc(v)) for c, v in skills]

    P.append("<h2>Education</h2>")
    for ed in education:
        P.append("<h3>%s in %s</h3>" % (esc(ed["degree"]), esc(ed["field"])))
        P.append('<div class="meta">%s</div>' % esc(ed["institution"]))
        P.append('<div class="meta">%s</div>' % esc(edu_meta(ed)))
        if ed["highlights"]:
            P += ["<ul>"] + ["<li>%s</li>" % esc(h) for h in ed["highlights"]] + ["</ul>"]

    if langs:
        P.append("<h2>Languages</h2>")
        P += ["<p>%s: %s</p>" % (esc(n), esc(l)) for n, l in langs]

    P.append("</body>\n</html>\n")
    return "\n".join(P)


# --------------------------------------------------- designed (hybrid) html ---
#
# Same facts as the ATS outputs, same parser-safe discipline (single column, no
# tables, standard headings, "Month YYYY" dates, ASCII only), but set for a human
# eye in the house style and allowed to run to 2 pages.

DESIGNED_CSS = """
  /* House style, sized for two pages. Parser-affecting rules kept:
     single column, no tables, no text boxes, no header/footer,
     standard section names, Month YYYY dates, ASCII text only. */
  @page { size: letter; margin: 0.75in; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    font-size: 10.5pt; line-height: 1.34; color: #1a1a1a;
    -webkit-print-color-adjust: exact;
  }
  h1 { font-size: 22pt; font-weight: bold; letter-spacing: 0.3px; }
  .headline { font-size: 11.5pt; font-weight: bold; color: #2b4a6f; margin-top: 3pt; }
  .contact { font-size: 10pt; color: #444; margin-top: 4pt; }
  h2 {
    font-size: 11pt; font-weight: bold; text-transform: uppercase; letter-spacing: 1.3px;
    color: #2b4a6f; border-bottom: 1.2px solid #2b4a6f;
    margin: 15pt 0 7pt; padding-bottom: 2pt;
    break-after: avoid; page-break-after: avoid;
  }
  h2:first-of-type { margin-top: 13pt; }
  .job { margin-bottom: 11pt; }
  .job-head { break-after: avoid; page-break-after: avoid; }
  .role { font-size: 11.5pt; font-weight: bold; color: #111; }
  .meta { font-size: 10pt; color: #555; margin-top: 1pt; }
  ul { margin: 5pt 0 0 16pt; }
  li { margin-bottom: 4.5pt; padding-left: 2pt; break-inside: avoid; page-break-inside: avoid; }
  .skill { margin-bottom: 4pt; }
  .skill b { color: #2b4a6f; }
  .edu { margin-bottom: 6pt; }
  .edu-head { display: flex; justify-content: space-between; align-items: baseline; }
  .edu-sub { font-size: 10pt; color: #444; margin-top: 2pt; }
  b, strong { font-weight: bold; }
"""


def emphasize(text, bold, found):
    """esc() first, then wrap bold targets. `found` collects matches so the caller can report misses."""
    out = esc(text)
    for phrase in bold:
        target = esc(phrase)
        if target in out:
            out = out.replace(target, "<b>%s</b>" % target, 1)
            found.add(phrase)
    return out


def build_designed_html(B, summary, work, skills, education, langs, bold):
    found = set()
    P = ['<!DOCTYPE html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
         '<title>%s - Resume</title>' % esc(B["name"]), '<style>%s</style>' % DESIGNED_CSS, '</head>', '<body>']

    P.append("<h1>%s</h1>" % esc(B["name"]))
    P.append('<div class="headline">%s</div>' % esc(B["title"]))
    line1 = [x for x in (B["location"], B["remote"], B["authorization"]) if x]
    line2 = [x for x in (B["phone"], B["email"], B["linkedin"].replace("https://www.", "").rstrip("/")) if x]
    P += ['<div class="contact">%s</div>' % esc(" | ".join(l)) for l in (line1, line2) if l]

    P += ["<h2>Summary</h2>", "<p>%s</p>" % emphasize(summary, bold, found), "<h2>Work Experience</h2>"]
    for job in work:
        P += ['<div class="job">', '<div class="job-head">', '<div class="role">%s</div>' % esc(job["title"])]
        P.append('<div class="meta">%s</div>' % esc(" | ".join(x for x in (
            job["company"], job["location"], "%s - %s" % (job["start"], job["end"])) if x)))
        P.append('</div>')
        P += ["<ul>"] + ["<li>%s</li>" % emphasize(b, bold, found) for b in job["bullets"]] + ["</ul>", "</div>"]

    P.append("<h2>Skills</h2>")
    P += ['<div class="skill"><b>%s:</b> %s</div>' % (esc(c), esc(v)) for c, v in skills]

    P.append("<h2>Education</h2>")
    for ed in education:
        P += ['<div class="edu">', '<div class="edu-head">',
              '<div class="role">%s in %s</div>' % (esc(ed["degree"]), esc(ed["field"])),
              '<div class="meta">%s</div>' % esc(edu_meta(ed).replace(", GPA", " | GPA")), '</div>',
              '<div class="meta">%s</div>' % esc(ed["institution"])]
        if ed["highlights"]:
            P.append('<div class="edu-sub">%s</div>' % esc(" | ".join(ed["highlights"])))
        P.append('</div>')

    if langs:
        P.append("<h2>Languages</h2>")
        P.append('<div class="skill">%s</div>' % esc(" | ".join("%s: %s" % l for l in langs)))

    P += ["</body>", "</html>"]

    if bold:
        missing = [x for x in bold if x not in found]
        if missing:
            print("WARNING bold target never matched: %s" % missing)
        else:
            print("bold targets matched        : %d/%d" % (len(found), len(bold)))
    return "\n".join(P)


# ------------------------------------------------------------------- docx ---

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def para(text, size=22, bold=False, after=80, indent=0):
    """size is half-points: 22 = 11pt. after/indent are twips."""
    ind = '<w:ind w:left="%d" w:hanging="%d"/>' % (indent, 180 if indent else 0)
    return (
        '<w:p><w:pPr><w:spacing w:after="%d" w:line="264" w:lineRule="auto"/>%s</w:pPr>'
        '<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>%s'
        '<w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr>'
        '<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
        % (after, ind, "<w:b/>" if bold else "", size, size, esc(text))
    )


def build_docx_xml(B, summary, work, skills, education, langs):
    X = [para(B["name"], size=40, bold=True, after=40), para(B["title"], size=24, after=120)]
    X += [para(c, after=20) for c in contact_lines(B)]

    X += [para("Summary", size=28, bold=True, after=80), para(summary, after=140)]

    X.append(para("Work Experience", size=28, bold=True, after=80))
    for job in work:
        X.append(para(job["title"], size=24, bold=True, after=20))
        X.append(para(job["company"], after=20))
        X.append(para(job["location"], after=20))
        X.append(para("%s - %s" % (job["start"], job["end"]), after=60))
        X += [para("- " + b, after=80, indent=360) for b in job["bullets"]]
        X.append(para("", after=60))

    X.append(para("Skills", size=28, bold=True, after=80))
    X += [para("%s: %s" % s, after=80) for s in skills]

    X.append(para("Education", size=28, bold=True, after=80))
    for ed in education:
        X.append(para("%s in %s" % (ed["degree"], ed["field"]), size=24, bold=True, after=20))
        X.append(para(ed["institution"], after=20))
        X.append(para(edu_meta(ed), after=60))
        X += [para("- " + h, after=40, indent=360) for h in ed["highlights"]]

    if langs:
        X.append(para("Languages", size=28, bold=True, after=80))
        X += [para("%s: %s" % l, after=40) for l in langs]

    sect = ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" '
            'w:header="0" w:footer="0" w:gutter="0"/></w:sectPr>')

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>' + "".join(X) + sect + '</w:body></w:document>')


def write_docx(path, content):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", build_docx_xml(*content))


# ------------------------------------------------------------------- main ---

def main():
    d = work_dir()
    r, opts = load(d)
    content = extract(r, opts)
    out = d / "machine"
    os.makedirs(out, exist_ok=True)
    files = {
        "resume-ats.txt": build_txt(*content),
        "resume-llm.md": build_md(*content),
        "resume-jsonresume.json": build_jsonresume(*content),
        "resume-ats.html": build_html(*content),
        "resume-designed.html": build_designed_html(*content, bold=opts.get("bold", [])),
    }
    for name, body in files.items():
        with open(out / name, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        print("wrote %-26s %6d bytes" % (name, len(body.encode("utf-8"))))

    docx_path = out / "resume-ats.docx"
    write_docx(docx_path, content)
    print("wrote %-26s %6d bytes" % ("resume-ats.docx", os.path.getsize(docx_path)))

    # guard: nothing outside ASCII may reach a text output (the ASCII table above missed a glyph)
    for name in ("resume-ats.txt", "resume-llm.md", "resume-ats.html", "resume-designed.html"):
        hits = sorted({c for c in files[name] if ord(c) > 127})
        status = "OK" if not hits else "FOUND " + " ".join("U+%04X" % ord(c) for c in hits)
        print("charcheck %-24s %s" % (name, status))


if __name__ == "__main__":
    main()
