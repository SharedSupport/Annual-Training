#!/usr/bin/env python3
"""
extract_binder.py — build the training site's content from the paper binder folders.

The folder tree is a far better source than the digital binder's PDF bookmarks:

  * The seven numbered folders match the printed table of contents exactly. The
    bookmarks in the InDesign export did not — they had 9 entries, invented a
    standalone MANDT section, omitted Independent Trainings, and pinned Med
    Admin to a single page.
  * Each policy is its own file with its revision date in the filename, so the
    site can show staff what they're reading and when it was last revised.
  * Several files here are NEWER than the digital binder (built 03/04/2026):
    Abuse Policy 7.10.26, Fleet Safety Program 07.13.26, Community
    Participation July2026. The paper binder is the more current source.

Duplicates: every section carries an "Easy Print …" and/or "… Packet" file that
is the same content concatenated with cover pages — confirmed by identical
character counts. Those aren't extracted as reading content; they become the
section's printable download.

Usage:
  python extract_binder.py "Annual Training - Paper Binder" --out content
"""

import argparse
import html as _html
import json
import re
import unicodedata
from pathlib import Path

import pymupdf

SECTION_TITLES = {
    "1 - DRC Policies": "DRC: Policies",
    "2 - Incident Management": "Incident Management & Abuse",
    "3 - Drivers Safety": "Driver's Safety",
    "4 - Disaster Prep": "Disaster Preparedness",
    "5 - Independent Trainings": "Independent Trainings",
    "6 - Alternative Routes": "Alternative Routes",
    "7 - Med Admin Review": "Medication Administration",
}

# Files deliberately kept off the site. Reasons stay in the code so a future
# re-run doesn't quietly reinstate them.
EXCLUDE = {
    "How to use DCI cheet sheet":
        "DCI is retired - time & attendance now lives in iCM. Superseded by "
        "the Time & Attendance help guide linked on the section page.",
}

# Wording fixed on the site because the source document is out of date. Each
# entry must match exactly once, or extraction warns - a silent no-op after a
# source revision would put the stale text back in front of staff.
#
# These are display-level overrides. The underlying PDF still says the old
# thing, so every entry here is also a source edit someone owes.
CORRECTIONS = {
    "HEAVY HITTER LIST": [
        ("DCI clock in and clock out",
         "iCM clock in and clock out",
         "DCI is retired - time & attendance now lives in iCM"),
    ],
}

# External resources shown alongside a section's documents.
LINKS = {
    "independent-trainings": [
        {
            "title": "Time & Attendance help guide",
            "url": "https://sharedsupport.github.io/ICM-STA-Guide",
            "blurb": "How to clock in, clock out, and record mileage in iCM. "
                     "Replaces the old DCI cheat sheet.",
        },
    ],
}

SECTION_COLORS = {
    "drc-policies": "#8E6FA8",
    "incident-management-abuse": "#9A8C3C",
    "drivers-safety": "#A8447C",
    "disaster-preparedness": "#2F3E6B",
    "independent-trainings": "#B03A2E",
    "alternative-routes": "#4E8C8A",
    "medication-administration": "#7A1521",
}

# Trailing revision dates in filenames, e.g. "Abuse Policy Updated 7.10.26".
# Month names are whitelisted, or "SexualityPolicy2019" parses "Policy2019"
# as a date.
MONTHS = ("January|February|March|April|May|June|July|August|September|"
          "October|November|December")
DATE_RE = re.compile(
    r"[\s_-]*(?:Updated|Revised|Rev\.?)?[\s_-]*("
    r"\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}"
    rf"|(?:{MONTHS})\s*\d{{4}}"
    r"|\d{1,2}[.\-]\d{4}"
    r"|(?:19|20)\d{2}"
    r")\s*$", re.I)


def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.lower().replace("\u2019", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def tidy(stem):
    """Filenames are inconsistent. Normalise before splitting off the date."""
    s = stem.replace("_", " ")
    s = re.sub(r"^\d+\s*-\s*", "", s)              # "2 - Link to TED Talk"
    # Split run-together words: "ManagementPolicy" -> "Management Policy".
    # Requires two lowercase letters first so "(ePHI)" survives intact.
    s = re.sub(r"(?<=[a-z]{2})(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Za-z])(?=(?:19|20)\d{2}\b)", " ", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def parse_name(stem):
    """Split a filename into a display title and a revision date, if present."""
    s = tidy(stem)
    m = DATE_RE.search(s)
    if m:
        return s[: m.start()].strip(" -_"), m.group(1)
    return s.strip(" -_"), None


def is_printable_duplicate(name):
    low = name.lower()
    return low.startswith("easy print") or "packet" in low


def apply_corrections(stem, html, warnings):
    for old, new, why in CORRECTIONS.get(stem, []):
        n = html.count(old)
        if n != 1:
            warnings.append(
                f"correction in '{stem}' matched {n} times, expected 1 - "
                f"source may have changed: {old!r}")
            continue
        html = html.replace(old, new)
        warnings.append(f"corrected '{stem}': {old!r} -> {new!r} ({why})")
    return html


HEADING_CAPS_RE = re.compile(r"^[A-Z0-9][A-Z0-9 ,&/'’()\-]{2,78}:?$")
# "SCOPE OF POLICY: This policy applies to..." - a run-in label on the same line
RUNIN_RE = re.compile(r"^([A-Z][A-Z&/,'’ \-]{2,48}):\s+(\S.*)$")
# "I.  Incident Reporting/Investigations" - a numbered section title
ROMAN_RE = re.compile(r"^[IVX]{1,5}\.\s+[A-Z].{2,78}$")
LONE_NUMERAL_RE = re.compile(r"^(?:[IVX]{1,5}|\d{1,2}|[A-Z])\.$")
PAGE_NO_RE = re.compile(r"^(?:page\s+)?\d{1,3}(?:\s*(?:of|/)\s*\d{1,3})?$", re.I)
BULLET_RE = re.compile(r"^(?:[•●▪■◦]|[–\-o]\s)\s*")


def page_furniture(pages):
    """Header and footer lines repeat on most pages. Find them by their text
    with digits stripped, so '3 Revised 04/07/20' matches '4 Revised 04/07/20'."""
    if len(pages) < 3:
        return set()
    seen = {}
    for lines in pages:
        for key in {re.sub(r"[\d\s]+", " ", l["t"]).strip().lower() for l in lines}:
            if len(key) >= 6:
                seen[key] = seen.get(key, 0) + 1
    return {k for k, n in seen.items() if n >= 3 and n >= 0.4 * len(pages)}


def extract_html(path):
    """Text with layout-derived structure. Returns (html, page_count, chars).

    Works block by block in the PDF's own content order rather than sorting
    every line on the page by its y coordinate. That keeps two-column
    brochures (Workers Comp) from interleaving their columns line by line,
    and gives long policies (Incident Management, 42 pages) a paragraph per
    text block instead of one paragraph per document.
    """
    doc = pymupdf.open(path)
    pages = []            # per page: list of blocks, each a list of lines
    for page in doc:
        blocks = []
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            lines = []
            for ln in b["lines"]:
                dx, dy = ln.get("dir", (1, 0))
                if abs(dy) > 0.1:          # rotated furniture, not content
                    continue
                spans = [sp for sp in ln["spans"] if sp["text"].strip()]
                txt = "".join(sp["text"] for sp in ln["spans"]).strip()
                if not txt:
                    continue
                isbold = lambda sp: "Bold" in sp["font"] or sp.get("flags", 0) & 16
                lines.append({
                    "t": txt,
                    "size": round(max(sp["size"] for sp in ln["spans"]), 1),
                    "bold": any(isbold(sp) for sp in spans),
                    "allbold": bool(spans) and all(isbold(sp) for sp in spans),
                })
            if lines:
                blocks.append(lines)
        if blocks:
            pages.append(blocks)

    furniture = page_furniture([[l for b in p for l in b] for p in pages])
    out = []
    total = 0
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def emit_para(lines):
        if lines:
            close_list()
            out.append("<p>" + " ".join(lines) + "</p>")

    last_h_block = [None]

    def heading(level, text, block=None):
        close_list()
        t = _html.escape(text)
        # "I." on one line and "Background" on the next -> "I. Background"
        if out and out[-1].startswith(f"<h{level}>"):
            prev = out[-1][4:-5]
            if block is not None and block is last_h_block[0] and \
                    not prev.rstrip().endswith((":", ".", "?")) and \
                    (level == 2 or (prev.isupper() and text.isupper())):
                out[-1] = f"<h{level}>{prev} {t}</h{level}>"   # a title wrapped over lines
                return
            if LONE_NUMERAL_RE.match(prev):
                out[-1] = f"<h{level}>{prev} {t}</h{level}>"
                return
            if text[:1].islower():          # a heading wrapped mid-word
                joiner = "" if prev[-1:].islower() else " "
                out[-1] = f"<h{level}>{prev}{joiner}{t}</h{level}>"
                return
        out.append(f"<h{level}>{t}</h{level}>")

    for blocks in pages:
        flat = [l for b in blocks for l in b]
        body = sorted(l["size"] for l in flat)[len(flat) // 2]

        for lines in blocks:
            para, item = [], None      # item: an open bullet's text pieces
            for ln in lines:
                raw = ln["t"]
                if PAGE_NO_RE.match(raw) or \
                        re.sub(r"[\d\s]+", " ", raw).strip().lower() in furniture:
                    continue
                total += len(raw)
                t = _html.escape(raw)
                bullet = BULLET_RE.match(raw)
                runin = RUNIN_RE.match(raw)
                looks_heading = not raw.rstrip().endswith(".") and not raw[:1].islower()
                if ln["size"] >= body * 1.55:
                    if item: out.append("<li>" + " ".join(item) + "</li>"); item = None
                    emit_para(para); para = []
                    heading(2, raw, block=lines)
                    last_h_block[0] = lines
                elif (ln["bold"] and len(raw) < 95 and looks_heading and
                      (raw.rstrip().endswith(":") or ln["size"] > body * 1.05)) or \
                     (ln["allbold"] and len(raw) < 80 and looks_heading and
                      len(lines) == 1) or \
                     (len(lines) == 1 and HEADING_CAPS_RE.match(raw) and
                      any(c.isalpha() for c in raw)) or \
                     (ROMAN_RE.match(raw) and looks_heading) or \
                     (LONE_NUMERAL_RE.match(raw) and ln["bold"]):
                    if item: out.append("<li>" + " ".join(item) + "</li>"); item = None
                    emit_para(para); para = []
                    heading(3, raw, block=lines)
                    last_h_block[0] = lines
                elif runin and not bullet:
                    if item: out.append("<li>" + " ".join(item) + "</li>"); item = None
                    emit_para(para); para = []
                    rest = runin.group(2)
                    if len(rest) <= 60 and not rest.rstrip().endswith("."):
                        heading(3, raw)                 # "POLICY: Incident Management"
                    else:
                        heading(3, runin.group(1) + ":")
                        para.append(_html.escape(rest))
                elif bullet:
                    text = _html.escape(raw[bullet.end():].strip())
                    if item: out.append("<li>" + " ".join(item) + "</li>")
                    emit_para(para); para = []
                    if not in_list:
                        out.append("<ul>"); in_list = True
                    item = [text] if text else []
                elif item is not None:
                    item.append(t)          # wrapped continuation of the bullet
                else:
                    para.append(t)
            if item is not None:
                if item: out.append("<li>" + " ".join(item) + "</li>")
                item = None
            emit_para(para)
        close_list()
    close_list()
    return "\n".join(out), doc.page_count, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="the 'Annual Training - Paper Binder' folder")
    ap.add_argument("--out", default="content")
    args = ap.parse_args()

    root = Path(args.root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sections, warnings = [], []

    for folder, title in SECTION_TITLES.items():
        base = root / folder
        if not base.is_dir():
            warnings.append(f"missing section folder: {folder}")
            continue
        slug = slugify(title)
        docs, printables, attachments = [], [], []
        excluded_dirs = set()

        for f in sorted(base.rglob("*")):
            if not f.is_file() or f.name.startswith("."):
                continue
            rel = str(f.relative_to(root))
            if f.suffix.lower() != ".pdf":
                attachments.append({"name": f.name, "path": rel})
                continue
            display, revised = parse_name(f.stem)
            if f.stem in EXCLUDE:
                excluded_dirs.add(f.parent)
                warnings.append(f"{title}: excluded '{display}' - {EXCLUDE[f.stem]}")
                continue
            if is_printable_duplicate(f.stem):
                printables.append({"title": display, "path": rel,
                                   "dir": str(f.parent.relative_to(root))})
                continue
            html, pages, chars = extract_html(f)
            html = apply_corrections(f.stem, html, warnings)
            docs.append({
                "slug": slugify(display),
                "title": display,
                "revised": revised,
                "pages": pages,
                "path": rel,
                "image_only": chars < 200 and "http" not in html,
                "html": html,
            })

        # A print packet sitting beside an excluded file almost certainly still
        # contains it - the packets are just their folder concatenated.
        for pr in printables:
            pr["review"] = any(
                str(d.relative_to(root)).startswith(pr["dir"]) or
                pr["dir"].startswith(str(d.relative_to(root)))
                for d in excluded_dirs)
            if pr["review"]:
                warnings.append(
                    f"{title}: printable '{pr['title']}' likely still contains "
                    f"excluded pages - regenerate before linking it")

        if not docs:
            warnings.append(f"{title}: no readable documents")
        elif all(d["image_only"] for d in docs):
            warnings.append(f"{title}: every document is image-only")

        sections.append({
            "slug": slug, "title": title,
            "color": SECTION_COLORS.get(slug, "#6B6B76"),
            "documents": docs, "printables": printables,
            "links": LINKS.get(slug, []), "attachments": attachments,
        })

    extras = []
    for f in sorted(root.glob("*.pdf")):
        display, _ = parse_name(f.stem)
        html, pages, chars = extract_html(f)
        extras.append({"slug": slugify(display), "title": display,
                       "pages": pages, "path": f.name,
                       "image_only": chars < 200 and "http" not in html, "html": html})

    data = {"sections": sections, "extras": extras, "warnings": warnings}
    (out / "content.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"{len(sections)} sections -> {out/'content.json'}")
    for s in sections:
        img = sum(d["image_only"] for d in s["documents"])
        link = f", {len(s['links'])} link" if s["links"] else ""
        print(f"  {s['title']:<30} {len(s['documents']):2d} docs "
              f"({img} image-only), {len(s['printables'])} printable{link}")
    for w in warnings:
        print("  warning:", w)


if __name__ == "__main__":
    main()
