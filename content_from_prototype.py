#!/usr/bin/env python3
"""
Recover content/content.json from a committed training-site-prototype.html.

The source binder is gitignored (113 MB of policy PDFs), so a fresh clone can't
run extract_binder.py. The prototype embeds the extractor's output, and this
puts it back into the extractor's schema so build_site.py can run.

Caveats, printed as warnings:
  * the prototype trims documents to 45,000 characters (currently only the
    Incident Management policy), so those come back truncated;
  * image-only documents carry no page images and no PDF path, so the site
    shows a placeholder for them until the real binder is extracted.

Prefer the real thing whenever the binder is available:
    python extract_binder.py "source/Annual Training - Paper Binder" --out content
"""

import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--prototype", default="training-site-prototype.html")
ap.add_argument("--out", default="content")
args = ap.parse_args()

src = Path(args.prototype).read_text(encoding="utf-8")
line = next(l for l in src.splitlines() if l.startswith("const D = "))
payload = json.loads(line[len("const D = "):].rstrip(";").replace("<\\/", "</"))

warnings = list(payload.get("warnings", []))
sections = []
for s in payload["sections"]:
    docs = []
    for d in s["documents"]:
        if d["trimmed"]:
            warnings.append(f"{s['title']}: '{d['title']}' recovered from the prototype "
                            f"is truncated at {len(d['html']):,} characters - "
                            f"re-run extract_binder.py for the full text")
        docs.append({
            "slug": d["slug"], "title": d["title"], "revised": d["revised"],
            "pages": d["pages"], "path": None, "image_only": d["imageOnly"],
            "truncated": d["trimmed"], "html": d["html"],
        })
    sections.append({
        "slug": s["slug"], "title": s["title"], "color": s["color"],
        "documents": docs, "printables": s["printables"],
        "links": s.get("links", []), "attachments": [],
    })

warnings.append("content recovered from training-site-prototype.html, not the binder - "
                "no PDFs or page images are available in this build")

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
data = {"sections": sections, "extras": payload["extras"], "warnings": warnings,
        "recovered_from": args.prototype}
(out / "content.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"{len(sections)} sections -> {out/'content.json'}")
for w in warnings:
    print("  warning:", w)
