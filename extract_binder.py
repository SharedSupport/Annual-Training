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


def extract_html(path):
    """Text with layout-derived structure. Returns (html, page_count, chars).

    Works block by block in the PDF's own content order rather than sorting
    every line on the page by its y coordinate. That keeps two-column
    brochures (Workers Comp) from interleaving their columns line by line,
    and gives long policies (Incident Management, 42 pages) a paragraph per
    text block instead of one paragraph per document.
    """
    doc = pymupdf.open(path)
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
                txt = "".join(s["text"] for s in ln["spans"]).strip()
                if not txt:
                    continue
                lines.append({
                    "t": txt,
                    "size": round(max(s["size"] for s in ln["spans"]), 1),
                    "bold": any("Bold" in s["font"] for s in ln["spans"]),
                })
            if lines:
                blocks.append(lines)
        if not blocks:
            continue
        flat = [l for b in blocks for l in b]
        total += sum(len(l["t"]) for l in flat)
        body = sorted(l["size"] for l in flat)[len(flat) // 2]

        for lines in blocks:
            para, item = [], None      # item: an open bullet's text pieces
            for ln in lines:
                t = _html.escape(ln["t"])
                bullet = re.match(r"^[•●▪–\-]\s+", ln["t"]) or \
                    re.match(r"^[•●▪]", ln["t"])
                if ln["size"] >= body * 1.55:
                    if item: out.append("<li>" + " ".join(item) + "</li>"); item = None
                    emit_para(para); para = []
                    close_list(); out.append(f"<h2>{t}</h2>")
                elif (ln["bold"] and len(t) < 95 and
                      (t.rstrip().endswith(":") or ln["size"] > body * 1.05)) or \
                     (len(lines) == 1 and HEADING_CAPS_RE.match(ln["t"]) and
                      any(c.isalpha() for c in ln["t"])):
                    if item: out.append("<li>" + " ".join(item) + "</li>"); item = None
                    emit_para(para); para = []
                    close_list(); out.append(f"<h3>{t}</h3>")
                elif bullet:
                    text = t[bullet.end():].strip() if bullet.end() <= len(t) else ""
                    text = text.lstrip("•●▪ ").strip()
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
                "image_only": chars < 200,
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
                       "image_only": chars < 200, "html": html})

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
