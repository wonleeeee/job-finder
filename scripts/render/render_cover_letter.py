"""Render cover-letter.md -> cover-letter.html (same page style as render_html.py). stdlib only.

Run:  <PY> scripts/render/render_cover_letter.py data/cache/tailored/<stable-id>/
PDF: chrome --headless --print-to-pdf, or print from the browser.

Name, address and contact come from resume.json `basics` in the same folder. cover-letter.md may open
with a front-matter block for the letter head (every key optional; date defaults to today):

    ---
    date: October 7, 2026
    to: Acme Corp · Platform Engineering · Atlanta, GA
    re: Software Engineer III — req 12345
    ---
    Dear Hiring Manager,
    ...body paragraphs...
    Sincerely,
    Jane Doe

The salutation is the first line starting with "Dear". A closing paragraph ("Sincerely," / "Best regards," ...)
and a trailing signature block (the name, optionally followed by a contact line) are recognised and rendered
from resume.json instead. Anything after a line of "---" following the body is treated as notes and dropped.
"""
import datetime
import html
import re

from _common import MONTHS_LONG, link_label, load, location_line, primary_link, work_dir

CLOSINGS = re.compile(r"^(sincerely|best|best regards|kind regards|regards|respectfully|thank you)[,.]?$", re.I)


def split_front_matter(src):
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", src, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        src = src[m.end():]
    return meta, src


def main():
    d = work_dir()
    r, _ = load(d)
    b = r["basics"]
    meta, src = split_front_matter((d / "cover-letter.md").read_text(encoding="utf-8"))

    m = re.search(r"^(Dear [^\n]*)$", src, re.M)
    if not m:
        raise SystemExit("cover-letter.md: no salutation line starting with 'Dear'")
    salutation = m.group(1).strip()
    body = src[m.end():].split("\n---", 1)[0].strip()
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]

    # trailing signature block: starts with the name (a contact line may follow)
    if paras and paras[-1].splitlines()[0].strip() == b["name"]:
        paras.pop()
    closing = "Sincerely,"
    if paras:
        last = paras[-1].splitlines()
        if CLOSINGS.match(last[0].strip()):
            closing = last[0].strip()
            paras.pop()

    esc = html.escape
    contact = [esc(location_line(b)), esc(b.get("phone", "")), f'<a href="mailto:{esc(b["email"])}">{esc(b["email"])}</a>']
    link = primary_link(b)
    if link:
        contact.append(f'<a href="{esc(link)}">{esc(link_label(link))}</a>')
    contact_html = " · ".join(c for c in contact if c)

    today = datetime.date.today()
    date = meta.get("date") or f"{MONTHS_LONG[today.month - 1]} {today.day}, {today.year}"
    head = [f"<div>{esc(date)}</div>"]
    if meta.get("to"):
        head.append(f"<div>{esc(meta['to'])}</div>")
    if meta.get("re"):
        head.append(f'<div class="re">Re: {esc(meta["re"])}</div>')

    out = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{esc(b['name'])} — Cover Letter</title>
<style>
  @page {{ size: letter; margin: 0; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 8.5in; }}
  body {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 10.6pt; line-height: 1.42;
          color: #1a1a1a; padding: 0.7in 0.9in 0.6in; -webkit-print-color-adjust: exact; }}
  h1 {{ font-size: 19pt; font-weight: 700; letter-spacing: 0.5px; }}
  .contact {{ font-size: 9pt; color: #444; margin-top: 3px; }}
  .contact a {{ color: #444; text-decoration: none; }}
  .rule {{ border-bottom: 1.2px solid #2b4a6f; margin: 10px 0 22px; }}
  .meta {{ font-size: 10.2pt; color: #333; margin-bottom: 18px; }}
  .meta div + div {{ margin-top: 2px; }}
  .re {{ font-weight: 600; color: #2b4a6f; margin-top: 10px !important; }}
  p {{ margin-bottom: 11px; text-align: left; }}
  .sig {{ margin-top: 18px; }}
  .sig .name {{ font-weight: 600; margin-top: 2px; }}
</style></head><body>
<h1>{esc(b['name'])}</h1>
<div class="contact">{contact_html}</div>
<div class="rule"></div>
<div class="meta">
  {''.join(head)}
</div>
<p>{esc(salutation)}</p>
{''.join(f'<p>{esc(p)}</p>' for p in paras)}
<div class="sig"><div>{esc(closing)}</div><div class="name">{esc(b['name'])}</div></div>
</body></html>
"""
    with open(d / "cover-letter.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print(f"wrote {d / 'cover-letter.html'} ({len(paras)} paragraphs)")


if __name__ == "__main__":
    main()
