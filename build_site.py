#!/usr/bin/env python3
"""
build_site.py — render content/content.json into a static, multi-page site.

    python build_site.py                       # content/content.json -> site/
    python build_site.py --source "source/Annual Training - Paper Binder"
    python build_site.py --base /Annual-Training/   # hosted under a sub-path

Every section and document is its own HTML page, so URLs are shareable, the
browser's own find-in-page works, and nothing needs JavaScript to read. JS adds
the phone navigation sheet, search, and the signature-sheet behaviour.

With --source pointing at the paper binder folder, the build also copies the
print packets, offers each document's original PDF for download, and renders
image-only documents as page images. Without it (a fresh clone, where the
binder is gitignored) those become placeholders and the build says so.
"""

import argparse
import datetime as dt
import hashlib
import html as _html
import json
import re
import shutil
import unicodedata
from pathlib import Path

from training_config import (AS_PAGES, ATTESTATION, CERT_TOPICS, DELIVERY, FACPR,
                             FACPR_OBJECTIVES, FIRE_TOPICS, FOOTER_ADDRESS, LICENSED,
                             SCHEDULE, SIGN_TO, TITLE_FIXES, TRAINER, TRAINER_DEPT)

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--content", default="content/content.json")
ap.add_argument("--out", default="site")
ap.add_argument("--source", default=None,
                help="the 'Annual Training - Paper Binder' folder, for PDFs and page images")
ap.add_argument("--base", default="/", help="URL prefix the site is served from")
ap.add_argument("--submit-url", default="",
                help="endpoint the signature form POSTs to; without one the form emails "
                     "the sheets to --sign-to from the staff member's own mail app")
ap.add_argument("--sign-to", default=SIGN_TO,
                help=f"address signed sheets are emailed to (default {SIGN_TO})")
ap.add_argument("--image-zoom", type=float, default=1.6,
                help="render scale for image-only pages (1.0 = 72 dpi)")
ap.add_argument("--logo", default="static/logo.png",
                help="white-on-transparent logo for the maroon header; skipped if missing")
ap.add_argument("--serve-licensed", action="store_true",
                help="include page images of licensed material (only for a site behind sign-in)")
ARGS = ap.parse_args()

BASE = "/" + ARGS.base.strip("/") + "/" if ARGS.base.strip("/") else "/"
OUT = Path(ARGS.out)
SRC = json.load(open(ARGS.content, encoding="utf-8"))
SOURCE = Path(ARGS.source) if ARGS.source else None
CONTENT_VERSION = hashlib.sha256(
    Path(ARGS.content).read_bytes()).hexdigest()[:12]
BUILT = dt.date.today().isoformat()
WARN = list(SRC.get("warnings", []))
LOGO = Path(ARGS.logo) if Path(ARGS.logo).is_file() else None

# Paragraphs longer than this are split at sentence boundaries for display.
# Purely a readability measure for text blocks the PDF never broke up;
# wording is untouched.
LONG_PARA = 1400
PARA_TARGET = 700
JUMP_MIN_HEADINGS = 4


def esc(t):
    return _html.escape(str(t), quote=True)


def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def url(*parts):
    return BASE + "/".join(p.strip("/") for p in parts if p) + ("/" if parts else "")


def write(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def display_title(title):
    fixed = TITLE_FIXES.get(title)
    if fixed:
        WARN.append(f"title shown as '{fixed}' (file is named '{title}')")
        return fixed
    return title


# ---------------------------------------------------------------- content prep

def wrap_orphan_lists(html):
    """Older extractor output emits bare <li> runs. Group them into <ul>."""
    if "<ul>" in html:
        return html
    lines, out, open_ = html.split("\n"), [], False
    for ln in lines:
        is_li = ln.startswith("<li>")
        if is_li and not open_:
            out.append("<ul>"); open_ = True
        elif not is_li and open_:
            out.append("</ul>"); open_ = False
        out.append(ln)
    if open_:
        out.append("</ul>")
    return "\n".join(out)


SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"(])")


def split_long_paragraphs(html, stats):
    def split(m):
        text = m.group(1)
        if len(text) <= LONG_PARA:
            return m.group(0)
        chunks, cur = [], ""
        for sent in SENT_RE.split(text):
            if cur and len(cur) + len(sent) > PARA_TARGET:
                chunks.append(cur); cur = sent
            else:
                cur = (cur + " " + sent).strip()
        if cur:
            chunks.append(cur)
        stats["split"] += 1
        return "\n".join(f"<p>{c}</p>" for c in chunks)
    return re.sub(r"<p>(.*?)</p>", split, html, flags=re.S)


URL_RE = re.compile(r"(?<![\"'>])(https?://[^\s<]+?)(?=[.,;:)\]]*(?:\s|$|<))")


def linkify(html):
    """Bare URLs in the text become links (the TED talk page is only a URL)."""
    return URL_RE.sub(lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', html)


def add_heading_ids(html):
    """Give h2/h3 stable ids and return (html, [(level, id, text)])."""
    seen, heads = {}, []

    def repl(m):
        level, inner = m.group(1), m.group(2)
        text = re.sub(r"<[^>]+>", "", inner)
        base = slugify(_html.unescape(text))[:60] or "section"
        n = seen.get(base, 0) + 1
        seen[base] = n
        hid = base if n == 1 else f"{base}-{n}"
        heads.append((int(level), hid, text))
        return f'<h{level} id="{hid}">{inner}</h{level}>'
    return re.sub(r"<h([23])>(.*?)</h\1>", repl, html, flags=re.S), heads


def plain_text(html):
    t = re.sub(r"</(p|li|h2|h3)>", " ", html)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


def close_truncated(html):
    """A document cut mid-stream can end inside a tag or an open <p>."""
    html = re.sub(r"<[^>]*$", "", html)                 # half a tag
    html = html.rsplit(". ", 1)[0] + "." if ". " in html[-400:] else html
    for tag in ("li", "ul", "p"):
        if html.count(f"<{tag}>") > html.count(f"</{tag}>"):
            html += f"</{tag}>"
    return html


def drop_repeated_titles(html):
    """Slide decks repeat a title on every continuation slide ("Weight
    Management" five times). Keep the first of each top-level title."""
    seen = set()

    def repl(m):
        key = re.sub(r"\s+", " ", m.group(1)).strip().lower()
        if key in seen:
            return ""
        seen.add(key)
        return m.group(0)
    return re.sub(r"<h2>(.*?)</h2>\n?", repl, html, flags=re.S)


def join_broken_lines(html):
    """Slides and forms put every line in its own block. A paragraph with no
    end punctuation followed by one starting in lowercase is one sentence."""
    lines = html.split("\n")
    out = []
    for ln in lines:
        if (out and ln.startswith("<p>") and out[-1].startswith("<p>")
                and not re.search(r"[.:;!?\u2026]\s*</p>$", out[-1])
                and re.match(r"<p>[a-z(&]", ln)):
            out[-1] = out[-1][:-4] + " " + ln[3:]
        else:
            out.append(ln)
    return "\n".join(out)


def prepare(doc, stats):
    html = doc["html"]
    if doc.get("truncated"):
        html = close_truncated(html)
    html = wrap_orphan_lists(html)
    html = drop_repeated_titles(html)
    html = join_broken_lines(html)
    html = split_long_paragraphs(html, stats)
    html = linkify(html)
    html, heads = add_heading_ids(html)
    return html, heads


# ---------------------------------------------------------------- source files

def source_path(rel):
    if not SOURCE or not rel:
        return None
    p = SOURCE / rel
    return p if p.is_file() else None


def copy_pdf(rel, dest_rel):
    src = source_path(rel)
    if not src:
        return None
    dest = OUT / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return url(dest_rel).rstrip("/")


def render_pages(rel, dest_dir):
    """Rasterise an image-only PDF. Returns a list of (url, width, height)."""
    src = source_path(rel)
    if not src:
        return []
    import pymupdf
    (OUT / dest_dir).mkdir(parents=True, exist_ok=True)
    pages = []
    doc = pymupdf.open(src)
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(ARGS.image_zoom, ARGS.image_zoom))
        name = f"p{i:02d}.jpg"
        pix.save(str(OUT / dest_dir / name), jpg_quality=80)
        pages.append((url(dest_dir, name).rstrip("/"), pix.width, pix.height))
    return pages


# ---------------------------------------------------------------- layout

CSS = r"""
:root{
  --ink:#1B1B2F; --maroon:#7A1521; --gold:#C8A951;
  --page:#FCFBF8; --rule:#E3DDD0; --muted:#6E6A63; --accent:var(--maroon);
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif;
  --sans:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;
}
*{box-sizing:border-box}
html{scroll-padding-top:16px}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--serif);
  font-size:17px;line-height:1.62;
  background-image:radial-gradient(rgba(27,27,47,.055) 1px,transparent 1px);background-size:22px 22px}
a{color:var(--ink)}
button{font:inherit;cursor:pointer}
:focus-visible{outline:2.5px solid var(--maroon);outline-offset:2px}
.skip{position:absolute;left:-999px;top:8px;background:#fff;padding:8px 12px;z-index:50}
.skip:focus{left:8px}
.shell{display:grid;grid-template-columns:274px 1fr;min-height:100vh}

.rail{border-right:1px solid var(--rule);background:rgba(255,255,255,.75);
  position:sticky;top:0;height:100vh;overflow-y:auto;padding:22px 0 40px}
.brand{display:block;padding:0 20px 18px;border-bottom:1px solid var(--rule);margin-bottom:6px;text-decoration:none}
.brand b{font-family:var(--sans);font-weight:600;letter-spacing:.06em;font-size:12px;color:var(--maroon);display:block}
.brand span{font-size:26px;line-height:1.15;display:block;margin-top:4px}
.brand.logo{background:var(--maroon);padding:16px 20px 14px;margin:-22px 0 6px;border-bottom:3px solid var(--gold)}
.brand.logo img{display:block;width:150px;max-width:100%;height:auto}
.brand.logo span{color:#F6F1E6;font-size:22px;margin-top:8px}
.search{padding:12px 20px 4px}
.search input{width:100%;padding:8px 10px;border:1px solid var(--rule);background:#fff;
  font-family:var(--sans);font-size:14px;color:var(--ink)}
.grp{padding:13px 0 3px}
.grplab{font-family:var(--sans);font-size:11.5px;color:var(--muted);
  padding:0 20px 6px;display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.grplab b{color:var(--ink);font-weight:600}
.grplab em{font-style:normal;font-size:10.5px;opacity:.8;text-align:right}
.tab{display:flex;align-items:center;gap:11px;width:100%;background:none;border:0;
  border-left:5px solid transparent;padding:9px 18px 9px 15px;text-align:left;text-decoration:none;
  color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.35}
.tab:hover{background:rgba(27,27,47,.045)}
.tab[aria-current="true"]{border-left-color:var(--accent);background:rgba(27,27,47,.06);font-weight:600}
.dot{flex:none;width:12px;height:12px;border-radius:50%;background:var(--accent)}
.tab.off{color:var(--muted);cursor:default}
.tab.off:hover{background:none}
.tab.off .dot{border-radius:2px;background:none;border:2px dashed var(--rule)}
.tab-t{flex:1}
.tab .ct{font-size:11.5px;color:var(--muted)}
.certlink{margin-top:14px;border-top:1px solid var(--rule);padding-top:12px}

main{padding:0 0 90px;min-width:0}
.wrap{max-width:72ch;margin:0 auto;padding:0 28px}
.hero{background:linear-gradient(180deg,#6A1019,#7A1521 55%,#8C1D2B);border-bottom:4px solid var(--gold);
  color:#F6F1E6;padding:48px 28px 44px;margin-bottom:30px}
.hero .logo{display:block;width:220px;max-width:70%;height:auto;margin-bottom:22px}
.hero .wrap{padding:0}
.hero .org{display:block;font-family:var(--sans);font-weight:600;letter-spacing:.2em;
  font-size:12.5px;color:var(--gold);margin-bottom:10px}
.hero h1{font-size:clamp(40px,8vw,68px);line-height:.95;margin:0 0 14px;font-weight:600;letter-spacing:-.02em}
.hero .band{display:inline-block;background:var(--gold);color:#241E12;font-family:var(--sans);
  font-weight:600;letter-spacing:.16em;font-size:11px;padding:6px 14px}
.hero form{margin-top:26px;display:flex;gap:8px;max-width:440px}
.hero input{flex:1;padding:11px 12px;border:0;font-family:var(--sans);font-size:15px}
.hero button{background:var(--gold);color:#241E12;border:0;padding:0 18px;font-family:var(--sans);font-weight:600}

.sched{margin-bottom:34px}
.sched h2{font-size:15px;font-family:var(--sans);font-weight:600;margin:0 0 12px;color:var(--muted)}
.step{border-left:3px solid var(--rule);padding:0 0 18px 18px;position:relative}
.step:last-child{padding-bottom:0}
.step .hd{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.step h3{margin:0;font-size:20px;font-weight:600}
.step .how{font-family:var(--sans);font-size:12px;color:#fff;background:var(--ink);padding:2px 8px}
.step .how.self{background:none;color:var(--muted);border:1px solid var(--rule)}
.step p{margin:5px 0 10px;font-size:15.5px;color:var(--muted);max-width:58ch}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:#fff;border:1px solid var(--rule);border-left:4px solid var(--accent);
  padding:8px 13px;font-family:var(--sans);font-size:13.5px;text-align:left;text-decoration:none;color:var(--ink)}
.chip:hover{border-color:var(--ink)}
.chip.static{border-left-color:var(--rule);color:var(--muted);cursor:default}
.also{margin:30px 0 0}
.also h2{font-size:15px;font-family:var(--sans);font-weight:600;margin:0 0 10px;color:var(--muted)}

.sec-head{border-bottom:2px solid var(--accent);padding-bottom:14px;margin:34px 0 20px}
.sec-head .n{font-family:var(--sans);font-size:12px;color:var(--muted)}
.sec-head .n a{color:var(--muted)}
.sec-head h1{margin:5px 0 0;font-size:34px;font-weight:600;letter-spacing:-.01em;line-height:1.15}
.doclist{display:grid;gap:1px;background:var(--rule);border:1px solid var(--rule)}
.doc{background:var(--page);border:0;padding:15px 18px;text-align:left;width:100%;text-decoration:none;color:var(--ink);
  display:flex;justify-content:space-between;gap:14px;align-items:baseline}
.doc:hover{background:#fff}
.doc b{font-weight:600;font-size:17.5px}
.doc .meta{font-family:var(--sans);font-size:12px;color:var(--muted);white-space:nowrap;flex:none}
.printrow{margin-top:18px;font-family:var(--sans);font-size:13.5px;color:var(--muted);line-height:1.7}
.printrow a{color:var(--ink);font-weight:600;white-space:nowrap}
.printrow a::before{content:"\1F5A8\FE0F  "}
.flag{background:#F4E4C3;color:#6B4E12;font-size:11.5px;padding:1px 7px;white-space:nowrap}
.links{margin-bottom:18px;display:grid;gap:10px}
.link{display:block;background:#fff;border:1px solid var(--rule);border-left:4px solid var(--accent);
  padding:13px 16px;text-decoration:none;color:var(--ink)}
.link:hover{border-color:var(--ink)}
.link b{display:block;font-size:17px;font-weight:600}
.link span{display:block;font-family:var(--sans);font-size:13.5px;color:var(--muted);margin-top:2px}
.link .host{font-size:12px;margin-top:5px}

article h2{font-size:24px;margin:30px 0 8px;font-weight:600;line-height:1.2}
article h3{font-size:16.5px;margin:22px 0 4px;font-weight:700;font-family:var(--sans);line-height:1.3}
article p{margin:0 0 12px;overflow-wrap:anywhere}
article ul{margin:0 0 14px;padding:0}
article li{margin:0 0 6px 22px}
article table{border-collapse:collapse;width:100%;font-size:15px}
article td,article th{border:1px solid var(--rule);padding:6px 8px;vertical-align:top}
.docmeta{font-family:var(--sans);font-size:12.5px;color:var(--muted);margin:0 0 20px}
.docmeta a{color:var(--ink)}
.jump{background:#fff;border:1px solid var(--rule);padding:0 18px;margin:0 0 26px;font-family:var(--sans);font-size:14px}
.jump summary{cursor:pointer;padding:12px 0;font-weight:600;font-size:13px;letter-spacing:.02em;list-style:none;display:flex;justify-content:space-between}
.jump summary::-webkit-details-marker{display:none}
.jump summary::after{content:"+";color:var(--muted)}
.jump[open] summary::after{content:"\2212"}
.jump .ct{font-weight:400;color:var(--muted);margin-left:8px;flex:1}
.jump ol{margin:0;padding:4px 0 14px;list-style:none;border-top:1px solid var(--rule)}
.jump li{margin:3px 0}
.jump li.l3{margin-left:16px;font-size:13px}
.jump a{text-decoration:none}
.jump a:hover{text-decoration:underline}
.notice{border:1px solid var(--rule);border-left:4px solid var(--gold);background:#fff;padding:14px 18px;
  color:var(--muted);font-family:var(--sans);font-size:14px;margin:0 0 22px}
.placeholder{border:1px dashed var(--rule);background:rgba(27,27,47,.02);padding:24px;
  color:var(--muted);font-family:var(--sans);font-size:14px}
.pageimg{display:block;width:100%;height:auto;border:1px solid var(--rule);background:#fff;margin:0 0 14px}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:36px;padding-top:20px;border-top:1px solid var(--rule)}
.pager a{background:none;border:1px solid var(--rule);padding:11px 16px;font-family:var(--sans);font-size:14px;max-width:48%;text-decoration:none}
.pager a:hover{border-color:var(--ink)}
.pager span{flex:1}
.totop{display:block;margin-top:24px;font-family:var(--sans);font-size:13px;color:var(--muted)}

.results{list-style:none;margin:20px 0;padding:0}
.results li{border-bottom:1px solid var(--rule);padding:14px 0}
.results .sec{font-family:var(--sans);font-size:12px;color:var(--muted)}
.results a{font-weight:600;font-size:18px;text-decoration:none}
.results a:hover{text-decoration:underline}
.results p{margin:4px 0 0;font-size:15px;color:var(--muted)}
mark{background:#F4E4C3;color:inherit}

.sheet{background:#fff;border:1px solid var(--rule);padding:0 32px 22px;margin-bottom:26px;font-family:var(--sans);font-size:14px}
.sheet .sh{background:var(--maroon);border-bottom:4px solid var(--gold);margin:0 -32px 18px;padding:14px 32px}
.sheet .sh img{display:block;width:150px;height:auto}
.sheet .sh b{color:#F6F1E6;font-family:var(--sans);font-size:14px;letter-spacing:.08em}
.sheet h2{text-align:center;font-size:24px;margin:4px 0 2px;font-weight:700;font-family:var(--sans)}
.sheet .sub{text-align:center;color:var(--ink);margin:0 0 18px}
.sheet h3{color:var(--maroon);font-size:14px;font-weight:700;margin:16px 0 4px;letter-spacing:.02em}
.sheet h3.plain{color:var(--ink)}
.sheet .idbox{border:1.5px solid var(--maroon);border-radius:6px;background:#F7F5F0;padding:10px 14px;margin:0 0 6px}
.sheet .idbox .row{gap:12px 20px}
.sheet ul{margin:0 0 6px;padding:0 0 0 14px;list-style:none}
.sheet li{margin:0 0 2px;padding-left:12px;text-indent:-12px}
.sheet li::before{content:"*  ";color:var(--muted)}
.sheet ul.two{columns:2;column-gap:30px}
.sheet ul.two li{break-inside:avoid}
.sheet .datelist{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;align-items:center;max-width:360px;margin:0 0 4px 14px}
.sheet .datelist input{margin:0;padding:6px 2px}
.attest{background:#fff;border:1px solid var(--rule);border-radius:4px;padding:12px 14px;font-size:13.5px;margin:4px 0 14px;font-family:var(--serif);font-size:15px}
.sheet .trainer{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:baseline;margin-top:10px}
.sheet .trainer .line{border-bottom:1px solid var(--ink);min-width:200px;flex:1}
.sheet .sig-line{font-family:"Segoe Script","Brush Script MT",cursive;font-size:20px;color:var(--muted)}
.sheet .foot{text-align:center;color:var(--muted);font-size:11px;margin-top:22px}
.sheet .certify{text-align:center;margin:0 0 14px;font-size:15px}
.sheet .type{color:var(--gold);font-weight:700}
.sheet em{font-style:italic}
.sheet .field{margin-bottom:10px}
@media(max-width:640px){.sheet ul.two{columns:1}}
.field{display:block;margin-bottom:15px;font-family:var(--sans);font-size:13px;color:var(--muted)}
.field input{display:block;width:100%;margin-top:4px;padding:9px 2px;border:0;
  border-bottom:1px solid var(--ink);background:transparent;font-family:var(--serif);font-size:16px;color:var(--ink)}
.field input.sig{font-family:"Segoe Script","Brush Script MT",cursive;font-size:23px}
.field input:disabled{border-bottom-color:var(--rule)}
.row{display:grid;gap:20px}
@media(min-width:640px){.row{grid-template-columns:1fr 1fr}}
.track{display:flex;gap:10px;margin:8px 0 18px;flex-wrap:wrap}
.track button{flex:1;min-width:200px;background:#fff;border:2px solid var(--ink);border-radius:6px;padding:12px 14px;
  font-family:var(--sans);font-size:14px;font-weight:600;color:var(--ink);text-align:left;display:flex;gap:10px;align-items:center;
  box-shadow:0 1px 2px rgba(0,0,0,.08)}
.track button::before{content:"";width:16px;height:16px;border:2px solid var(--ink);border-radius:50%;flex:none;box-sizing:border-box}
.track button:hover{background:#F7F5F0}
.track button[aria-pressed="true"]{background:var(--maroon);border-color:var(--maroon);color:#fff}
.track button[aria-pressed="true"]::before{border-color:#fff;background:#fff;box-shadow:inset 0 0 0 3px var(--maroon)}
.acts{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
.submit{background:var(--maroon);color:#fff;border:0;padding:13px 22px;font-family:var(--sans);font-weight:600;font-size:15px}
.submit:disabled{background:#B9B3A9;cursor:not-allowed}
.ghost{background:none;border:1px solid var(--rule);padding:13px 20px;font-family:var(--sans);font-size:15px}
.note{font-family:var(--sans);font-size:13px;color:var(--muted);margin-top:14px}

footer{font-family:var(--sans);font-size:12px;color:var(--muted);border-top:1px solid var(--rule);
  margin:50px 0 0;padding:16px 0 0}
.railtoggle{display:none}
.scrim{display:none}
@media(max-width:860px){
  .shell{grid-template-columns:1fr}
  .rail{position:fixed;inset:auto 0 0 0;height:auto;max-height:74vh;width:100%;
    border-right:0;border-top:1px solid var(--rule);z-index:30;background:#fff;
    transform:translateY(100%);transition:transform .28s;padding-bottom:70px}
  .rail.open{transform:translateY(0)}
  .scrim.open{display:block;position:fixed;inset:0;background:rgba(27,27,47,.35);z-index:29}
  .railtoggle{display:block;position:fixed;left:0;right:0;bottom:0;z-index:31;
    background:var(--ink);color:#F6F1E6;border:0;padding:15px;font-family:var(--sans);font-weight:600;font-size:15px}
  main{padding-bottom:80px}
  .doc{flex-direction:column;gap:3px}
  .sheet{padding:0 18px 22px}
  .sheet .sh{margin:0 -18px 18px;padding:12px 18px}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
@media print{
  body{background:#fff;font-size:11pt;background-image:none}
  .rail,.railtoggle,.scrim,.acts,.track,.note,.pager,.hero,.sched,.jump,.totop,footer,.skip,.signintro{display:none!important}
  .sheet .sh{background:var(--maroon)!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .shell{display:block}
  .wrap{max-width:none;padding:0}
  .sheet{border:0;padding:0;margin:0 0 20px;break-after:page}
  .sheet .sh{margin:0 0 14px;padding:10px 16px}
  .field input{border-bottom:1px solid #000}
  a{text-decoration:none;color:#000}
}
"""

JS = r"""
(function(){
  var rail=document.getElementById('rail'), tog=document.getElementById('railtoggle'),
      scrim=document.getElementById('scrim');
  function setOpen(o){rail.classList.toggle('open',o);scrim.classList.toggle('open',o);
    tog.setAttribute('aria-expanded',o);tog.textContent=o?'Close':'Sections';}
  if(tog){tog.addEventListener('click',function(){setOpen(!rail.classList.contains('open'));});
    scrim.addEventListener('click',function(){setOpen(false);});}

  // ---- search
  var box=document.getElementById('results');
  if(box){
    var q=new URLSearchParams(location.search).get('q')||'';
    var input=document.getElementById('q'); if(input) input.value=q;
    var esc=function(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');};
    var status=document.getElementById('status');
    if(!q.trim()){status.textContent='Type a word or phrase above to search every document.';return;}
    status.textContent='Searching…';
    fetch(box.dataset.index).then(function(r){return r.json();}).then(function(idx){
      var terms=q.toLowerCase().split(/\s+/).filter(Boolean);
      var hits=[];
      idx.forEach(function(d){
        var t=d.t.toLowerCase(), h=d.h.toLowerCase(), b=d.b.toLowerCase(), score=0, first=-1;
        terms.forEach(function(w){
          if(t.indexOf(w)>-1) score+=12;
          if(h.indexOf(w)>-1) score+=5;
          var n=0,i=b.indexOf(w); if(i>-1&&(first<0||i<first)) first=i;
          while(i>-1&&n<50){n++;i=b.indexOf(w,i+1);} score+=n;
        });
        if(score>0) hits.push({d:d,s:score,i:first});
      });
      hits.sort(function(a,b){return b.s-a.s;});
      status.textContent=hits.length?hits.length+(hits.length===1?' document matches':' documents match')+' “'+q+'”':'Nothing matches “'+q+'”.';
      var re=new RegExp('('+terms.map(function(w){return w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}).join('|')+')','ig');
      box.innerHTML=hits.slice(0,60).map(function(h){
        var d=h.d, snip='';
        if(h.i>-1){var a=Math.max(0,h.i-90), z=Math.min(d.b.length,h.i+160);
          snip=(a>0?'…':'')+esc(d.b.slice(a,z))+(z<d.b.length?'…':'');}
        else snip=esc(d.b.slice(0,200))+'…';
        return '<li><div class="sec">'+esc(d.s)+'</div><a href="'+d.u+'">'+esc(d.t).replace(re,'<mark>$1</mark>')+
          '</a><p>'+snip.replace(re,'<mark>$1</mark>')+'</p></li>';
      }).join('');
    }).catch(function(){status.textContent='Search is unavailable right now.';});
  }

  // ---- signature sheets
  var form=document.getElementById('signform');
  if(form){
    var track=null, note=document.getElementById('signnote'), submit=form.querySelector('.submit');
    var facpr=form.querySelectorAll('[data-facpr]'), api=form.dataset.submit, to=form.dataset.mailto;
    var FAC=__FACPR__;
    var LABELS={employee_name:'Employee name',job_title:'Job title',training_date_range:'Training dates',day1_date:'Day 1',day2_date:'Day 2',
      day3_date:'Day 3',staff_signature:'Staff signature',fire_employee_name:'Employee name',
      fire_training_date:'Training date',fire_employee_signature:'Employee signature',
      facpr_employee_name:'Employee name',facpr_date_top:'Date',facpr_employee_signature:'Employee signature'};
    var $n=function(n){return form.querySelector('[name='+n+']');};
    function fmt(iso){if(!iso) return ''; var p=iso.split('-'); return p.length===3?(p[1]+'/'+p[2]+'/'+p[0]):iso;}
    // Fire safety follows Day 1, First Aid follows Day 3, until someone edits them.
    form.querySelectorAll('[data-follow]').forEach(function(el){
      var src=$n(el.dataset.follow);
      src.addEventListener('input',function(){if(!el.dataset.touched) el.value=src.value;});
      el.addEventListener('input',function(){el.dataset.touched=el.value?'1':'';});
    });
    function range(){var a=$n('day1_date').value, z=$n('day3_date').value;
      $n('training_date_range').value=(a||z)?(fmt(a)+(z?' - '+fmt(z):'')):'';}
    $n('day1_date').addEventListener('input',range); $n('day3_date').addEventListener('input',range);
    function setTrack(t){track=t;
      form.querySelectorAll('[data-track]').forEach(function(b){b.setAttribute('aria-pressed',b.dataset.track===t);});
      facpr.forEach(function(el){el.disabled=!t;});
      $n('track').value=t||'';
      var f=FAC[t||'recert'];
      document.getElementById('facpr-hours').textContent=f.hours;
      document.getElementById('facpr-title').textContent=f.title;
      document.getElementById('facpr-desc').textContent=f.description;
      document.getElementById('facpr-type').textContent=f.type;
      submit.disabled=!(t&&(api||to));
      submit.textContent=api?'Submit signed sheets':'Email your signed sheets';
      note.textContent=!(api||to)?'Submission is not switched on for this build. Print the sheets and hand them in.'
        :!t?'Choose Recertification or Review only (your trainer tells you which) to enable signing.'
        :api?'':'This opens your email app with the sheets filled in, addressed to the training department ('+to+'). Send it from your own work email so they know it came from you.';
    }
    function values(){var d={}; new FormData(form).forEach(function(v,k){d[k]=v;}); return d;}
    function mailBody(d){
      var f=FAC[d.track||'recert'];
      var L=['SHARED SUPPORT ANNUAL TRAINING - SIGNED SHEETS','','1. Annual Training certificate (22.5 hours)'];
      ['employee_name','job_title','training_date_range','day1_date','day2_date','day3_date','staff_signature'].forEach(function(k){L.push('  '+LABELS[k]+': '+(k.indexOf('date')>-1&&k!=='training_date_range'?fmt(d[k]):(d[k]||'')));});
      L.push('  Attestation: agreed as printed on the sign page','','2. Fire Safety Training');
      ['fire_employee_name','fire_training_date','fire_employee_signature'].forEach(function(k){L.push('  '+LABELS[k]+': '+(k.indexOf('date')>-1?fmt(d[k]):(d[k]||'')));});
      L.push('','3. '+f.title+' ('+f.type+')');
      ['facpr_employee_name','facpr_date_top','facpr_employee_signature'].forEach(function(k){L.push('  '+LABELS[k]+': '+(k.indexOf('date')>-1?fmt(d[k]):(d[k]||'')));});
      L.push('','Sent from the digital binder, content version '+d.content_version+', '+new Date().toISOString());
      return L.join('\n');
    }
    form.querySelectorAll('[data-track]').forEach(function(b){b.addEventListener('click',function(){setTrack(b.dataset.track);});});
    document.getElementById('print').addEventListener('click',function(){window.print();});
    form.addEventListener('submit',function(e){
      e.preventDefault();
      if(!track){note.textContent='Choose Recertification or Review only first.'; return;}
      if(!form.checkValidity()){form.reportValidity(); note.textContent='Every field is required. Fill in the highlighted ones.'; return;}
      var data=values(); data.submitted_at=new Date().toISOString();
      if(!api){
        if(!to) return;
        var href='mailto:'+to+'?subject='+encodeURIComponent('Annual Training signed sheets - '+(data.employee_name||''))+
          '&body='+encodeURIComponent(mailBody(data));
        var a=document.getElementById('mailto-link'); a.href=href; a.click();
        note.textContent='Your email app should have opened with the sheets filled in. Check it arrived in your sent items, or print the sheets instead.';
        return;
      }
      submit.disabled=true; note.textContent='Sending…';
      fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
        .then(function(r){if(!r.ok) throw new Error(r.status); note.textContent='Sent. The training department has your signed sheets.';})
        .catch(function(){submit.disabled=false; note.textContent='That didn’t go through. Try again, or print the sheets instead.';});
    });
    setTrack(null);
  }
})();
"""


def schedule_for(key):
    return next(s for s in SCHEDULE if s["key"] == key)


def rail(active_slug=None, active="sec"):
    brand = (f'<a class="brand logo" href="{url()}"><img src="{url("assets", "logo.png").rstrip("/")}" alt="Shared Support">'
             f'<span>Annual Training</span></a>' if LOGO else
             f'<a class="brand" href="{url()}"><b>Shared Support</b><span>Annual Training</span></a>')
    parts = [brand,
             f'<form class="search" role="search" action="{url("search")}"><label class="visually-hidden" for="rs" '
             'style="position:absolute;left:-999px">Search a policy</label>'
             '<input id="rs" type="search" name="q" placeholder="Search a policy"></form>']
    for st in SCHEDULE:
        secs = [s for s in SECTIONS if s["delivery"] == st["key"]]
        parts.append(f'<div class="grp"><div class="grplab"><b>{esc(st["label"])}</b><em>{esc(st["how"])}</em></div>')
        if secs:
            for s in secs:
                cur = "true" if s["slug"] == active_slug else "false"
                parts.append(f'<a class="tab" style="--accent:{s["color"]}" href="{s["url"]}" aria-current="{cur}">'
                             f'<span class="dot"></span><span class="tab-t">{esc(s["title"])}</span>'
                             f'<span class="ct">{len(s["documents"])}</span></a>')
        else:
            parts.append('<span class="tab off"><span class="dot"></span><span class="tab-t">With your trainer</span></span>')
        parts.append("</div>")
    cur = "true" if active == "sign" else "false"
    parts.append(f'<div class="certlink"><a class="tab" href="{url("sign")}" aria-current="{cur}">'
                 '<span class="dot" style="--accent:var(--maroon)"></span>'
                 '<span class="tab-t">Sign your training sheets</span></a></div>')
    return "".join(parts)


def layout(title, body, active_slug=None, active="sec", accent=None):
    style = f' style="--accent:{accent}"' if accent else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - Shared Support Annual Training</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{url("assets", "site.css").rstrip("/")}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="shell">
  <nav class="rail" id="rail" aria-label="Training sections">{rail(active_slug, active)}</nav>
  <main id="main"{style}>{body}
  <div class="wrap"><footer>Shared Support, Inc. &middot; Annual Training digital binder &middot;
  content version {CONTENT_VERSION} &middot; built {BUILT}</footer></div>
  </main>
</div>
<div class="scrim" id="scrim"></div>
<button class="railtoggle" id="railtoggle" aria-expanded="false" aria-controls="rail">Sections</button>
<script src="{url("assets", "site.js").rstrip("/")}" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- pages

def pages_word(n):
    return f"{n} page" if n == 1 else f"{n} pages"


def render_home():
    steps = []
    for st in SCHEDULE:
        secs = [s for s in SECTIONS if s["delivery"] == st["key"]]
        self_ = st["key"] in ("independent", "day3")
        chips = "".join(
            f'<a class="chip" style="--accent:{s["color"]}" href="{s["url"]}">{esc(s["title"])}</a>' for s in secs
        ) or "".join(f'<span class="chip static">{esc(i)}</span>' for i in st.get("items", []))
        steps.append(f'<div class="step"><div class="hd"><h3>{esc(st["label"])}</h3>'
                     f'<span class="how{" self" if self_ else ""}">{esc(st["how"])}</span></div>'
                     f'<p>{esc(st["blurb"])}</p><div class="chips">{chips}</div></div>')
    also = ""
    if EXTRAS:
        also = ('<div class="also"><h2>Also in the binder</h2><div class="chips">' +
                "".join(f'<a class="chip" href="{e["url"]}">{esc(e["title"])}</a>' for e in EXTRAS) +
                '</div></div>')
    org = (f'<img class="logo" src="{url("assets", "logo.png").rstrip("/")}" alt="Shared Support">' if LOGO
           else '<span class="org">Shared Support</span>')
    body = (f'<header class="hero"><div class="wrap">{org}'
            f'<h1>Annual Training</h1><span class="band">Digital Binder</span>'
            f'<form role="search" action="{url("search")}"><input type="search" name="q" '
            f'placeholder="Search a policy" aria-label="Search a policy"><button>Search</button></form>'
            f'</div></header><div class="wrap"><div class="sched"><h2>How your training runs</h2>'
            + "".join(steps) + '</div>'
            '<div class="printrow">Need paper? Every section lists its print-ready packet on its page.</div>'
            + also + '</div>')
    write("index.html", layout("Digital Binder", body, active="home"))


def render_section(s):
    st = schedule_for(s["delivery"])
    links = ""
    if s["links"]:
        links = '<div class="links">' + "".join(
            f'<a class="link" href="{esc(l["url"])}" target="_blank" rel="noopener"><b>{esc(l["title"])}</b>'
            f'<span>{esc(l["blurb"])}</span><span class="host">{esc(re.sub(r"^https?://", "", l["url"]).split("/")[0])}</span></a>'
            for l in s["links"]) + "</div>"
    docs = "".join(
        f'<a class="doc" href="{d["url"]}"><b>{esc(d["title"])}</b><span class="meta">'
        + (f'rev {esc(d["revised"])} &middot; ' if d["revised"] else "")
        + (f'{pages_word(d["pages"])}' + (" &middot; scanned" if d["image_only"] else ""))
        + "</span></a>" for d in s["documents"])
    prints = print_row(s)
    body = (f'<div class="wrap"><div class="sec-head"><span class="n">'
            f'{esc(st["label"])} &middot; {esc(st["how"])}</span><h1>{esc(s["title"])}</h1></div>'
            + links + f'<div class="doclist">{docs}</div>' + prints + "</div>")
    write(s["rel"] + "/index.html", layout(s["title"], body, s["slug"], accent=s["color"]))


def print_row(s):
    """One line: the section's print packet. "Easy Print" files are preferred
    over the "… Packet" duplicates; a packet flagged for review (it still
    contains retired pages) is never linked."""
    if not s["printables"]:
        return ""
    ok = [p for p in s["printables"] if not p.get("review")]
    ok.sort(key=lambda p: 0 if p["title"].lower().startswith("easy print") else 1)
    if ok and ok[0].get("href"):
        p = ok[0]
        size = f", {p['size_mb']:.0f} MB" if p.get("size_mb") else ""
        return f'<div class="printrow"><a href="{p["href"]}">Print this section (PDF{size})</a></div>'
    if ok:
        return '<div class="printrow">Print packet: not included in this build.</div>'
    return ('<div class="printrow">Print packet <span class="flag">being regenerated</span> '
            'it still contains the retired DCI pages, so it isn\u2019t linked until the training '
            'department reissues it.</div>')


def jump_list(heads):
    """A collapsed "on this page" list: the top-level headings, plus any
    subheadings that come before the first one (a policy whose only large
    headings are in an attached form still gets its own sections listed).
    Sentence-case lead-ins ending in a colon and very long lines are left out."""
    first_h2 = next((i for i, h in enumerate(heads) if h[0] == 2), len(heads))
    picked = [h for i, h in enumerate(heads) if h[0] == 2 or i < first_h2]
    picked = [h for h in picked
              if len(h[2]) <= 90 and not (h[2].rstrip().endswith(":") and not h[2].isupper())]
    if len(picked) < JUMP_MIN_HEADINGS:
        return ""
    picked = picked[:40]
    items = "".join(f'<li class="l{lvl}"><a href="#{hid}">{text}</a></li>' for lvl, hid, text in picked)
    return (f'<details class="jump"><summary>On this page <span class="ct">{len(picked)}</span></summary>'
            f'<ol>{items}</ol></details>')


def render_doc(s, d, i, stats):
    docs = s["documents"]
    crumbs = f'<a href="{s["url"]}">{esc(s["title"])}</a>' if s else ""
    meta = []
    if d.get("revised"):
        meta.append(f"Last revised {esc(d['revised'])}")
    meta.append(pages_word(d["pages"]))
    if d.get("pdf"):
        meta.append(f'<a href="{d["pdf"]}">Download the PDF</a>')
    notices = []
    if d["slug"] in LICENSED:
        notices.append(LICENSED[d["slug"]] + ("" if d.get("pages_img") else
                       " It isn't reproduced on this public site; use the card in your printed "
                       "binder or ask your trainer for one."))
    if d.get("truncated"):
        notices.append("Only the first part of this document is in this build. The full text "
                       "appears once the binder is re-extracted.")
    if d["image_only"] or d["slug"] in AS_PAGES:
        jump = ""
        if d.get("pages_img"):
            article = "".join(
                f'<img class="pageimg" src="{u}" width="{w}" height="{h}" loading="lazy" '
                f'alt="{esc(d["title"])}, page {n}">'
                for n, (u, w, h) in enumerate(d["pages_img"], 1))
        elif d["slug"] in LICENSED:
            article = ""
        elif d["slug"] in AS_PAGES:
            html, _ = prepare(d, stats)
            article = html
        else:
            article = (f'<div class="placeholder">Scanned handout, {pages_word(d["pages"])}. '
                       'Page images are added when the site is built from the binder folder.</div>')
    else:
        html, heads = prepare(d, stats)
        jump = jump_list(heads)
        article = html
    prev = (f'<a href="{docs[i-1]["url"]}" rel="prev">&larr; {esc(docs[i-1]["title"])}</a>' if i > 0
            else f'<a href="{s["url"]}">&larr; {esc(s["title"])}</a>' if s else "<span></span>")
    nxt = (f'<a href="{docs[i+1]["url"]}" rel="next">{esc(docs[i+1]["title"])} &rarr;</a>'
           if i < len(docs) - 1 else "<span></span>")
    body = (f'<div class="wrap"><div class="sec-head"><span class="n">{crumbs}</span>'
            f'<h1>{esc(d["title"])}</h1></div><p class="docmeta">{" &middot; ".join(meta)}</p>'
            + "".join(f'<div class="notice">{esc(n)}</div>' for n in notices)
            + jump + f'<article>{article}</article>'
            + f'<div class="pager">{prev}{nxt}</div>'
            + f'<a class="totop" href="#main">Back to top</a></div>')
    write(d["rel"] + "/index.html",
          layout(d["title"], body, s["slug"] if s else None, accent=s["color"] if s else None))


def render_search():
    body = (f'<div class="wrap"><div class="sec-head"><span class="n">Search</span><h1>Search the binder</h1></div>'
            f'<form role="search" action="{url("search")}" class="hero" style="background:none;padding:0;margin:0 0 10px">'
            f'<input id="q" type="search" name="q" aria-label="Search" style="border:1px solid var(--rule)">'
            f'<button style="background:var(--ink);color:#fff">Search</button></form>'
            f'<p class="docmeta" id="status">Loading…</p>'
            f'<ul class="results" id="results" data-index="{url("search-index.json").rstrip("/")}"></ul>'
            f'<noscript><p class="notice">Search needs JavaScript. Every document is also listed on its section page.</p></noscript>'
            '</div>')
    write("search/index.html", layout("Search", body, active="search"))


def render_sign():
    def field(label, name, kind="text", ph="", cls="", extra=""):
        return (f'<label class="field">{label}<input type="{kind}" name="{name}" required'
                f'{" class=" + chr(34) + cls + chr(34) if cls else ""}'
                f'{" placeholder=" + chr(34) + ph + chr(34) if ph else ""}{extra}></label>')

    def ul(items, two=False):
        return f'<ul class="{"two" if two else ""}">' + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"

    band = (f'<div class="sh"><img src="{url("assets", "logo.png").rstrip("/")}" alt="Shared Support"></div>'
            if LOGO else '<div class="sh"><b>SHARED SUPPORT, INC.</b></div>')
    foot = f'<div class="foot">{esc(FOOTER_ADDRESS)}</div>'
    trainer = (f'<div class="trainer"><b>Trainer:</b><span class="sig-line">{esc(TRAINER)}</span>'
               f'<span>{esc(TRAINER)}, {esc(TRAINER_DEPT)}</span></div>')
    submit_attr = (f' data-submit="{esc(ARGS.submit_url)}"' if ARGS.submit_url
                   else f' data-mailto="{esc(ARGS.sign_to)}"' if ARGS.sign_to else "")
    how = ("Submitting sends them to the training department"
           if ARGS.submit_url else
           f"Sending emails them to the training department at {esc(ARGS.sign_to)} from your own mail app"
           if ARGS.sign_to else "Print them and hand them in")
    objectives = "".join(f'<h3 class="plain">{esc(h)}</h3>{ul(items)}' for h, items in FACPR_OBJECTIVES)
    rec = FACPR["recert"]
    body = f"""<div class="wrap" style="padding-top:34px">
<div class="signintro"><h1 style="font-size:32px;margin:0 0 6px;font-weight:600">Sign your training sheets</h1>
<p style="color:var(--muted);margin:0 0 24px;max-width:58ch">Fill these in once you\u2019ve finished all three days. Every field is required.
{how}; printing gives you the same three sheets on paper.</p></div>
<form id="signform"{submit_attr} novalidate>
<input type="hidden" name="content_version" value="{CONTENT_VERSION}">
<input type="hidden" name="track" value="">

<div class="sheet">{band}
<h2>Annual Training</h2><p class="sub">Certificate of Training &nbsp;\u00b7&nbsp; Total Hours: 22.5</p>
<div class="idbox"><div class="row">{field("Employee Name:", "employee_name", extra=" autocomplete='name'")}{field("Job Title:", "job_title")}</div>
<label class="field">Training Dates:<input type="text" name="training_date_range" readonly placeholder="filled in from the dates below"></label></div>
<h3>TRAINING DATES</h3>
<div class="datelist"><span>Day 1:</span><input type="date" name="day1_date" required aria-label="Day 1 date">
<span>Day 2:</span><input type="date" name="day2_date" required aria-label="Day 2 date">
<span>Day 3:</span><input type="date" name="day3_date" required aria-label="Day 3 date"></div>
<h3>DAY 1 - Annual Training</h3>{ul(CERT_TOPICS["day1"], two=True)}
<h3>INDEPENDENT TRAININGS (complete before Day 2)</h3>{ul(CERT_TOPICS["independent"])}
<h3>DAY 2 - Annual Training</h3>{ul(CERT_TOPICS["day2"])}
<h3>DAY 3 - In-Person Training</h3>{ul(CERT_TOPICS["day3"])}
<h3>ATTESTATION</h3><div class="attest">{esc(ATTESTATION)}</div>
{field("Staff Signature:", "staff_signature", ph="Type your full name", cls="sig")}
{trainer}
{foot}</div>

<div class="sheet">{band}
<h2>Emergency Training: Fire Safety Training</h2><p class="sub"><b>By Expert</b></p>
<p class="certify">This is to certify that Shared Support, Inc. has conducted and completed<br>Fire Safety Training as specified below for:</p>
<div class="row">{field("Employee Name", "fire_employee_name")}{field("Employee Signature", "fire_employee_signature", ph="Type your full name", cls="sig")}</div>
<h3>Training Date:</h3><div class="datelist"><span></span><input type="date" name="fire_training_date" required data-follow="day1_date" aria-label="Fire safety training date"></div>
<h3>Training Topics:</h3>{ul(FIRE_TOPICS)}
<div class="trainer"><span><b>{esc(TRAINER)}</b><br><small>Trainer\u2019s Name</small></span>
<span class="sig-line">{esc(TRAINER)}</span></div>
{foot}</div>

<div class="sheet">{band}
<h2>Training Cover</h2>
<div class="row"><div class="datelist" style="margin-left:0"><b>Date:</b><input type="date" name="facpr_date_top" required data-follow="day3_date" aria-label="First aid training date"></div>
<div style="text-align:right"><b>Total Hours: <span id="facpr-hours">{esc(rec["hours"])}</span></b></div></div>
<p style="margin:14px 0 6px;font-family:var(--sans);font-size:13px;color:var(--muted)">Your trainer tells you which of these applies to you:</p>
<div class="track"><button type="button" data-track="recert" aria-pressed="false">{esc(rec["button"])}</button>
<button type="button" data-track="review" aria-pressed="false">{esc(FACPR["review"]["button"])}</button></div>
<h2 id="facpr-title" style="text-align:left;font-size:20px;color:var(--maroon)">{esc(rec["title"])}</h2>
<h3><em>TRAINING DESCRIPTION:</em></h3><p id="facpr-desc"><em>{esc(rec["description"])}</em></p>
<h3>TRAINING OBJECTIVE:</h3><p style="margin:0 0 4px 14px">Demonstrate the skills for the following:</p>{objectives}
<div class="idbox">{field("Employee Name:", "facpr_employee_name", extra=" data-facpr disabled")}
<div><b>Type:</b> &nbsp;<span class="type" id="facpr-type">{esc(rec["type"])}</span></div></div>
{field("Employee Signature:", "facpr_employee_signature", ph="Type your full name", cls="sig", extra=" data-facpr disabled")}
<div class="trainer"><b>Trainer\u2019s Signature:</b><span class="sig-line">{esc(TRAINER)}</span><span>{esc(TRAINER)}</span></div>
{foot}</div>

<div class="acts"><button class="submit" type="submit" disabled>Submit signed sheets</button>
<button class="ghost" type="button" id="print">Print these sheets</button></div>
<p class="note" id="signnote"></p>
<a id="mailto-link" hidden aria-hidden="true">email</a>
</form></div>"""
    write("sign/index.html", layout("Sign your training sheets", body, active="sign"))


def render_404():
    body = (f'<div class="wrap" style="padding-top:34px"><h1>That page isn’t in the binder</h1>'
            f'<p>Try the <a href="{url()}">contents</a> or <a href="{url("search")}">search</a>.</p></div>')
    write("404.html", layout("Not found", body))


# ---------------------------------------------------------------- assemble

SECTIONS, EXTRAS, INDEX = [], [], []
STATS = {"split": 0, "images": 0, "pdfs": 0}

missing = set(DELIVERY) - {s["slug"] for s in SRC["sections"]}
unmapped = {s["slug"] for s in SRC["sections"]} - set(DELIVERY)
if missing or unmapped:
    raise SystemExit(f"delivery map mismatch: unknown {sorted(missing)}, unmapped {sorted(unmapped)}")

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

for s in SRC["sections"]:
    s = dict(s)
    s["delivery"] = DELIVERY[s["slug"]]
    s["rel"] = f"sections/{s['slug']}"
    s["url"] = url(s["rel"])
    docs = []
    for d in s["documents"]:
        d = dict(d)
        d["title"] = display_title(d["title"])
        d["rel"] = f"{s['rel']}/{d['slug']}"
        d["url"] = url(d["rel"])
        if d.get("path"):
            fname = Path(d["path"]).name
            if (d["image_only"] or d["slug"] in AS_PAGES) and (d["slug"] not in LICENSED or ARGS.serve_licensed):
                d["pages_img"] = render_pages(d["path"], f"pages/{s['slug']}/{d['slug']}")
                STATS["images"] += len(d["pages_img"])
            if d["slug"] not in LICENSED:      # licensed material is never served as a file
                href = copy_pdf(d["path"], f"files/{s['slug']}/{fname}")
                if href:
                    d["pdf"] = href
                    STATS["pdfs"] += 1
        docs.append(d)
    s["documents"] = docs
    for p in s["printables"]:
        if not p.get("review"):
            p["href"] = copy_pdf(p["path"], f"print/{s['slug']}/{Path(p['path']).name}")
            if p["href"]:
                STATS["pdfs"] += 1
                p["size_mb"] = source_path(p["path"]).stat().st_size / 1048576
    SECTIONS.append(s)

for e in SRC.get("extras", []):
    e = dict(e)
    e["title"] = display_title(e["title"])
    e["rel"] = f"extras/{e['slug']}"
    e["url"] = url(e["rel"])
    e.setdefault("revised", None)
    if e.get("path"):
        e["pdf"] = copy_pdf(e["path"], f"files/extras/{Path(e['path']).name}")
    EXTRAS.append(e)

write("assets/site.css", CSS.strip() + "\n")
if LOGO:
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LOGO, OUT / "assets" / "logo.png")
else:
    WARN.append(f"no logo at {ARGS.logo}; header shows the name in text")
write("assets/site.js", JS.strip().replace("__FACPR__", json.dumps(FACPR)) + "\n")
render_home()
render_search()
render_sign()
render_404()

for s in SECTIONS:
    render_section(s)
    for i, d in enumerate(s["documents"]):
        render_doc(s, d, i, STATS)
        if not d["image_only"]:
            html, heads = prepare(d, {"split": 0})
            INDEX.append({"t": d["title"], "s": s["title"], "u": d["url"],
                          "h": " | ".join(h[2] for h in heads), "b": plain_text(html)})
        else:
            INDEX.append({"t": d["title"], "s": s["title"], "u": d["url"], "h": "",
                          "b": f"Scanned handout, {pages_word(d['pages'])}."})

extra_sec = {"slug": None, "title": "Also in the binder", "url": url(), "color": None,
             "documents": EXTRAS}
for i, e in enumerate(EXTRAS):
    render_doc(extra_sec, e, i, STATS)
    html, heads = prepare(e, {"split": 0})
    INDEX.append({"t": e["title"], "s": "Also in the binder", "u": e["url"],
                  "h": " | ".join(h[2] for h in heads), "b": plain_text(html)})

write("search-index.json", json.dumps(INDEX, ensure_ascii=False))
write("staticwebapp.config.json", json.dumps({
    "trailingSlash": "always",
    "responseOverrides": {"404": {"rewrite": "/404.html"}},
    "globalHeaders": {"X-Content-Type-Options": "nosniff",
                      "Referrer-Policy": "strict-origin-when-cross-origin"},
    "routes": [{"route": "/assets/*", "headers": {"Cache-Control": "public, max-age=86400"}},
               {"route": "/pages/*", "headers": {"Cache-Control": "public, max-age=604800"}}],
}, indent=2))
write(".nojekyll", "")

if STATS["split"]:
    WARN.append(f"{STATS['split']} very long paragraphs split at sentence boundaries for display")

n_docs = sum(len(s["documents"]) for s in SECTIONS)
n_pages = sum(1 for _ in OUT.rglob("index.html")) + 1
print(f"wrote {OUT}/ : {n_pages} pages, {n_docs} documents in {len(SECTIONS)} sections, "
      f"{len(EXTRAS)} extra, {STATS['pdfs']} PDFs, {STATS['images']} page images, "
      f"content version {CONTENT_VERSION}")
if not SOURCE:
    print("  note: no --source given, so print packets, PDF downloads, and page images are placeholders")
for w in WARN:
    print("  warning:", w)
