#!/usr/bin/env python3
"""Build a self-contained prototype of the training site from content.json.

Superseded by build_site.py, which renders the real multi-page site. Kept so the
single-file prototype can still be regenerated for sharing."""

import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--content", default="content/content.json",
                help="extractor output (default: content/content.json)")
ap.add_argument("--out", default="training-site-prototype.html")
ARGS = ap.parse_args()

SRC = json.load(open(ARGS.content, encoding="utf-8"))

from training_config import ATTESTATION, DELIVERY, FIRE_TOPICS, SCHEDULE

MAX_DOC_CHARS = 45000


def payload():
    secs = []
    for s in SRC["sections"]:
        docs = []
        for d in s["documents"]:
            html = d["html"]
            trimmed = len(html) > MAX_DOC_CHARS
            docs.append({
                "slug": d["slug"], "title": d["title"], "revised": d["revised"],
                "pages": d["pages"], "imageOnly": d["image_only"],
                "trimmed": trimmed,
                "html": "" if d["image_only"] else html[:MAX_DOC_CHARS],
            })
        secs.append({
            "slug": s["slug"], "title": s["title"], "color": s["color"],
            "delivery": DELIVERY[s["slug"]], "documents": docs,
            "printables": s["printables"], "links": s.get("links", []),
        })
    return {"sections": secs, "schedule": SCHEDULE, "extras": SRC["extras"],
            "warnings": SRC.get("warnings", []),
            "fireTopics": FIRE_TOPICS, "attestation": ATTESTATION}


missing = set(DELIVERY) - {s["slug"] for s in SRC["sections"]}
unmapped = {s["slug"] for s in SRC["sections"]} - set(DELIVERY)
if missing or unmapped:
    raise SystemExit(f"delivery map mismatch — unknown: {sorted(missing)}, "
                     f"unmapped sections: {sorted(unmapped)}")

PAYLOAD = json.dumps(payload()).replace("</", "<\\/")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shared Support Annual Training - Digital Binder</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#1B1B2F; --maroon:#7A1521; --gold:#C8A951;
  --page:#FCFBF8; --rule:#E3DDD0; --muted:#6E6A63;
  --serif:"Source Serif 4",Georgia,serif; --sans:"Inter",system-ui,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--serif);
  font-size:17px;line-height:1.62;
  background-image:radial-gradient(rgba(27,27,47,.055) 1px,transparent 1px);
  background-size:22px 22px}
button{font:inherit;cursor:pointer}
:focus-visible{outline:2.5px solid var(--maroon);outline-offset:2px}
.shell{display:grid;grid-template-columns:274px 1fr;min-height:100vh}

.rail{border-right:1px solid var(--rule);background:rgba(255,255,255,.75);
  position:sticky;top:0;height:100vh;overflow-y:auto;padding:22px 0 40px}
.brand{padding:0 20px 18px;border-bottom:1px solid var(--rule);margin-bottom:6px;cursor:pointer}
.brand b{font-family:var(--sans);font-weight:600;letter-spacing:.06em;font-size:12px;color:var(--maroon);display:block}
.brand span{font-size:26px;line-height:1.15;display:block;margin-top:4px}
.grp{padding:13px 0 3px}
.grplab{font-family:var(--sans);font-size:11.5px;color:var(--muted);
  padding:0 20px 6px;display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.grplab b{color:var(--ink);font-weight:600}
.grplab em{font-style:normal;font-size:10.5px;opacity:.8;text-align:right}
.tab{display:flex;align-items:center;gap:11px;width:100%;background:none;border:0;
  border-left:5px solid transparent;padding:9px 18px 9px 15px;text-align:left;
  color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.35}
.tab:hover:not(:disabled){background:rgba(27,27,47,.045)}
.tab[aria-current="true"]{border-left-color:var(--accent);background:rgba(27,27,47,.06);font-weight:600}
.dot{flex:none;width:12px;height:12px;border-radius:50%;background:var(--accent)}
.tab:disabled{color:var(--muted);cursor:default}
.tab:disabled .dot{border-radius:2px;background:none;border:2px dashed var(--rule)}
.tab-t{flex:1}
.tab .ct{font-size:11.5px;color:var(--muted)}
.certlink{margin-top:14px;border-top:1px solid var(--rule);padding-top:12px}

main{padding:0 0 90px;min-width:0}
.wrap{max-width:72ch;margin:0 auto;padding:0 28px}
.hero{background:linear-gradient(180deg,#1B1B2F,#2A2543 60%,#3A2E4A);
  color:#F6F1E6;padding:56px 28px 44px;margin-bottom:30px}
.hero .wrap{padding:0}
.hero .org{display:block;font-family:var(--sans);font-weight:600;letter-spacing:.2em;
  font-size:12.5px;color:var(--gold);margin-bottom:10px}
.hero h1{font-size:clamp(40px,8vw,68px);line-height:.95;margin:0 0 14px;font-weight:600;letter-spacing:-.02em}
.hero .band{display:inline-block;background:var(--gold);color:#241E12;font-family:var(--sans);
  font-weight:600;letter-spacing:.16em;font-size:11px;padding:6px 14px}

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
  padding:8px 13px;font-family:var(--sans);font-size:13.5px;text-align:left}
.chip:hover{border-color:var(--ink)}
.chip.static{border-left-color:var(--rule);color:var(--muted);cursor:default}

.sec-head{border-bottom:2px solid var(--accent);padding-bottom:14px;margin:34px 0 20px}
.sec-head .n{font-family:var(--sans);font-size:12px;color:var(--muted)}
.sec-head h2{margin:5px 0 0;font-size:34px;font-weight:600;letter-spacing:-.01em}
.doclist{display:grid;gap:1px;background:var(--rule);border:1px solid var(--rule)}
.doc{background:var(--page);border:0;padding:15px 18px;text-align:left;width:100%;
  display:flex;justify-content:space-between;gap:14px;align-items:baseline}
.doc:hover{background:#fff}
.doc b{font-weight:600;font-size:17.5px}
.doc .meta{font-family:var(--sans);font-size:12px;color:var(--muted);white-space:nowrap;flex:none}
.printrow{margin-top:18px;font-family:var(--sans);font-size:13.5px;color:var(--muted)}
.printrow a{color:var(--ink)}
.flag{background:#F4E4C3;color:#6B4E12;font-size:11.5px;padding:1px 7px;white-space:nowrap}
.links{margin-bottom:18px;display:grid;gap:10px}
.link{display:block;background:#fff;border:1px solid var(--rule);border-left:4px solid var(--accent);
  padding:13px 16px;text-decoration:none;color:var(--ink)}
.link:hover{border-color:var(--ink)}
.link b{display:block;font-size:17px;font-weight:600}
.link span{display:block;font-family:var(--sans);font-size:13.5px;color:var(--muted);margin-top:2px}
.link .host{font-size:12px;margin-top:5px}

article h2{font-size:24px;margin:26px 0 8px;font-weight:600}
article h3{font-size:16.5px;margin:20px 0 4px;font-weight:700;font-family:var(--sans)}
article p{margin:0 0 12px}
article li{margin:0 0 6px 20px}
.docmeta{font-family:var(--sans);font-size:12.5px;color:var(--muted);margin:0 0 20px}
.placeholder{border:1px dashed var(--rule);background:rgba(27,27,47,.02);padding:24px;
  color:var(--muted);font-family:var(--sans);font-size:14px}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:36px;padding-top:20px;border-top:1px solid var(--rule)}
.pager button{background:none;border:1px solid var(--rule);padding:11px 16px;font-family:var(--sans);font-size:14px;max-width:48%}
.pager span{flex:1}

.sheet{background:#fff;border:1px solid var(--rule);padding:0 32px 28px;margin-bottom:22px}
.sheet .sh{border-top:6px solid var(--maroon);border-bottom:3px solid var(--gold);
  margin:0 -32px 20px;padding:16px 32px 12px}
.sheet .sh b{font-family:var(--sans);font-size:11px;letter-spacing:.08em;color:var(--maroon);display:block}
.sheet .sh h3{margin:5px 0 2px;font-size:24px;font-weight:600}
.sheet .sh em{font-style:normal;font-family:var(--sans);font-size:12.5px;color:var(--muted)}
.attest{background:var(--page);border:1px solid var(--rule);padding:15px 17px;font-size:15.5px;margin:16px 0}
.topics{columns:2;column-gap:26px;font-size:14px;font-family:var(--sans);color:var(--muted);margin:4px 0 20px}
.topics div{break-inside:avoid;margin-bottom:3px}
@media(max-width:640px){.topics{columns:1}}
.field{display:block;margin-bottom:15px;font-family:var(--sans);font-size:13px;color:var(--muted)}
.field input{display:block;width:100%;margin-top:4px;padding:9px 2px;border:0;
  border-bottom:1px solid var(--ink);background:transparent;font-family:var(--serif);font-size:16px;color:var(--ink)}
.field input.sig{font-family:"Segoe Script","Brush Script MT",cursive;font-size:23px}
.field input:disabled{border-bottom-color:var(--rule)}
.row{display:grid;gap:20px}
@media(min-width:640px){.row{grid-template-columns:1fr 1fr}}
.track{display:flex;border:1px solid var(--rule);margin:4px 0 20px}
.track button{flex:1;background:none;border:0;padding:12px 8px;font-family:var(--sans);font-size:13.5px;color:var(--muted)}
.track button[aria-pressed="true"]{background:var(--ink);color:#fff;font-weight:600}
.acts{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
.submit{background:var(--maroon);color:#fff;border:0;padding:13px 22px;font-family:var(--sans);font-weight:600;font-size:15px}
.submit:disabled{background:#B9B3A9;cursor:not-allowed}
.ghost{background:none;border:1px solid var(--rule);padding:13px 20px;font-family:var(--sans);font-size:15px}
.note{font-family:var(--sans);font-size:13px;color:var(--muted);margin-top:14px}

.railtoggle{display:none}
@media(max-width:860px){
  .shell{grid-template-columns:1fr}
  .rail{position:fixed;inset:auto 0 0 0;height:auto;max-height:74vh;width:100%;
    border-right:0;border-top:1px solid var(--rule);z-index:30;background:#fff;
    transform:translateY(100%);transition:transform .28s;padding-bottom:70px}
  .rail.open{transform:translateY(0)}
  .railtoggle{display:block;position:fixed;left:0;right:0;bottom:0;z-index:31;
    background:var(--ink);color:#F6F1E6;border:0;padding:15px;font-family:var(--sans);font-weight:600;font-size:15px}
  main{padding-bottom:80px}
  .doc{flex-direction:column;gap:3px}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
@media print{
  body{background:#fff;font-size:11pt;background-image:none}
  .rail,.railtoggle,.acts,.track,.note,.pager,.hero,.sched{display:none!important}
  .shell{display:block}
  .wrap{max-width:none;padding:0}
  .sheet{border:0;padding:0;margin:0 0 20px;break-after:page}
  .sheet .sh{margin:0 0 14px;padding:10px 0}
  .field input{border-bottom:1px solid #000}
}
</style>
</head>
<body>
<div class="shell">
  <nav class="rail" id="rail" aria-label="Training sections"></nav>
  <main id="main"></main>
</div>
<button class="railtoggle" id="railtoggle" aria-expanded="false">Sections</button>

<script>
const D = __PAYLOAD__;
const byId = {};
D.sections.forEach(s => byId[s.slug] = s);
let track = null;               // set by the trainer in the real build
let view = {mode:"home"};
const $ = q => document.querySelector(q);
const secsFor = k => D.sections.filter(s => s.delivery === k);
const esc = t => String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;");

function renderRail(){
  $("#rail").innerHTML =
    '<div class="brand" id="home"><b>Shared Support</b><span>Annual Training</span></div>' +
    D.schedule.map(st => {
      const secs = secsFor(st.key);
      return '<div class="grp"><div class="grplab"><b>' + st.label + '</b><em>' + st.how + '</em></div>' +
        (secs.length ? secs.map(s =>
          '<button class="tab" style="--accent:' + s.color + '" data-sec="' + s.slug + '"' +
          ' aria-current="' + (view.slug === s.slug) + '"><span class="dot"></span>' +
          '<span class="tab-t">' + esc(s.title) + '</span>' +
          '<span class="ct">' + s.documents.length + '</span></button>').join("")
        : '<button class="tab" disabled><span class="dot"></span>' +
          '<span class="tab-t">With your trainer</span></button>') + '</div>';
    }).join("") +
    '<div class="certlink"><button class="tab" data-cert="1" aria-current="' + (view.mode==="cert") + '">' +
      '<span class="dot" style="--accent:var(--maroon)"></span>' +
      '<span class="tab-t">Sign your training sheets</span></button></div>';
}

function renderHome(){
  $("#main").innerHTML =
  '<header class="hero"><div class="wrap">' +
    '<span class="org">Shared Support</span>' +
    '<h1>Annual Training</h1>' +
    '<span class="band">Digital Binder</span>' +
  '</div></header><div class="wrap"><div class="sched"><h2>How your training runs</h2>' +
  D.schedule.map(st => {
    const secs = secsFor(st.key);
    const self = st.key === "independent" || st.key === "day3";
    return '<div class="step"><div class="hd"><h3>' + st.label + '</h3>' +
      '<span class="how' + (self ? " self" : "") + '">' + st.how + '</span></div>' +
      '<p>' + st.blurb + '</p><div class="chips">' +
      (secs.length ? secs.map(s =>
        '<button class="chip" style="--accent:' + s.color + '" data-sec="' + s.slug + '">' +
        esc(s.title) + '</button>').join("")
        : (st.items || []).map(i => '<span class="chip static">' + esc(i) + '</span>').join("")) +
      '</div></div>';
  }).join("") + '</div>' +
  '<div class="printrow">Need paper? Every section has a print-ready packet on its page.</div>' +
  '</div>';
}

function renderSection(slug){
  const s = byId[slug];
  $("#main").innerHTML = '<div class="wrap" style="--accent:' + s.color + '">' +
    '<div class="sec-head"><span class="n">' +
      D.schedule.find(x => x.key === s.delivery).label + ' \u00b7 ' +
      D.schedule.find(x => x.key === s.delivery).how + '</span>' +
      '<h2>' + esc(s.title) + '</h2></div>' +
    (s.links.length ? '<div class="links">' + s.links.map(l =>
      '<a class="link" href="' + l.url + '" target="_blank" rel="noopener">' +
      '<b>' + esc(l.title) + '</b><span>' + esc(l.blurb) + '</span>' +
      '<span class="host">' + esc(new URL(l.url).host) + '</span></a>').join("") + '</div>' : "") +
    '<div class="doclist">' + s.documents.map(d =>
      '<button class="doc" data-doc="' + s.slug + '/' + d.slug + '">' +
      '<b>' + esc(d.title) + '</b><span class="meta">' +
      (d.revised ? "rev " + esc(d.revised) + " \u00b7 " : "") +
      d.pages + (d.pages === 1 ? " page" : " pages") + '</span></button>').join("") +
    '</div>' +
    (s.printables.length ? '<div class="printrow">Print-ready packet: ' +
      s.printables.map(p => '<a href="#">' + esc(p.title) + '</a>' +
        (p.review ? ' <span class="flag">needs regenerating</span>' : "")).join(", ") +
      '</div>' : "") +
    '</div>';
  window.scrollTo(0,0);
}

function renderDoc(key){
  const [ss, ds] = key.split("/");
  const s = byId[ss];
  const i = s.documents.findIndex(d => d.slug === ds);
  const d = s.documents[i];
  const body = d.imageOnly
    ? '<div class="placeholder">Scanned handout \u2014 shown as page images in the real build, ' +
      'with a download link. ' + d.pages + ' pages.</div>'
    : d.html + (d.trimmed ? '<div class="placeholder">Trimmed here to keep this ' +
      'prototype a single file. The full document loads from content.json in the real build.</div>' : "");
  $("#main").innerHTML = '<div class="wrap" style="--accent:' + s.color + '">' +
    '<div class="sec-head"><span class="n">' + esc(s.title) + '</span>' +
      '<h2>' + esc(d.title) + '</h2></div>' +
    '<p class="docmeta">' + (d.revised ? "Last revised " + esc(d.revised) + " \u00b7 " : "") +
      d.pages + (d.pages === 1 ? " page" : " pages") + '</p>' +
    '<article>' + body + '</article><div class="pager">' +
    (i > 0 ? '<button data-doc="' + ss + '/' + s.documents[i-1].slug + '">\u2190 ' +
      esc(s.documents[i-1].title) + '</button>' : '<button data-sec="' + ss + '">\u2190 ' + esc(s.title) + '</button>') +
    (i < s.documents.length - 1 ? '<button data-doc="' + ss + '/' + s.documents[i+1].slug + '">' +
      esc(s.documents[i+1].title) + ' \u2192</button>' : '<span></span>') +
    '</div></div>';
  window.scrollTo(0,0);
}

function renderCert(){
  $("#main").innerHTML = '<div class="wrap" style="padding-top:34px">' +
    '<h2 style="font-size:32px;margin:0 0 6px;font-weight:600">Sign your training sheets</h2>' +
    '<p style="color:var(--muted);margin:0 0 24px;max-width:58ch">Fill these in once you\u2019ve ' +
    'finished all three days. Submitting sends them to the training department.</p>' +

    '<div class="sheet"><div class="sh"><b>SHARED SUPPORT, INC.</b>' +
      '<h3>Annual Training</h3><em>Certificate of Training \u00b7 Total hours: 22.5</em></div>' +
      '<div class="row"><label class="field">Employee name<input type="text"></label>' +
      '<label class="field">Job title<input type="text"></label></div>' +
      '<div class="row"><label class="field">Day 1 date<input type="text" placeholder="mm/dd/yyyy"></label>' +
      '<label class="field">Day 2 date<input type="text" placeholder="mm/dd/yyyy"></label></div>' +
      '<div class="row"><label class="field">Day 3 date<input type="text" placeholder="mm/dd/yyyy"></label><span></span></div>' +
      '<div class="attest">' + D.attestation + '</div>' +
      '<label class="field">Staff signature<input class="sig" type="text" placeholder="Type your full name"></label></div>' +

    '<div class="sheet"><div class="sh"><b>EMERGENCY TRAINING</b>' +
      '<h3>Fire Safety Training</h3><em>Topics covered</em></div>' +
      '<div class="topics">' + D.fireTopics.map(t => '<div>' + esc(t) + '</div>').join("") + '</div>' +
      '<div class="row"><label class="field">Employee name<input type="text"></label>' +
      '<label class="field">Training date<input type="text" placeholder="mm/dd/yyyy"></label></div>' +
      '<label class="field">Employee signature<input class="sig" type="text" placeholder="Type your full name"></label></div>' +

    '<div class="sheet"><div class="sh"><b>TRAINING COVER</b>' +
      '<h3>First Aid / CPR / AED</h3><em>Your trainer tells you which of these applies to you</em></div>' +
      '<div class="track">' +
        '<button data-track="recert" aria-pressed="' + (track==="recert") + '">Recertification \u00b7 2.75 hours</button>' +
        '<button data-track="review" aria-pressed="' + (track==="review") + '">Review only \u00b7 2.0 hours</button></div>' +
      '<div class="row"><label class="field">Employee name<input type="text"' + (track?"":" disabled") + '></label>' +
      '<label class="field">Date<input type="text" placeholder="mm/dd/yyyy"' + (track?"":" disabled") + '></label></div>' +
      '<label class="field">Employee signature<input class="sig" type="text" placeholder="Type your full name"' +
        (track?"":" disabled") + '></label></div>' +

    '<div class="acts"><button class="submit"' + (track?"":" disabled") + '>Submit signed sheets</button>' +
    '<button class="ghost" id="print">Print these sheets</button></div>' +
    '<p class="note">Prototype \u2014 nothing is submitted or emailed yet.' +
      (track ? "" : " Pick a First Aid option to enable signing.") + '</p></div>';
  window.scrollTo(0,0);
}

function render(){
  renderRail();
  if(view.mode === "home") renderHome();
  else if(view.mode === "cert") renderCert();
  else if(view.mode === "doc") renderDoc(view.key);
  else renderSection(view.slug);
}

document.addEventListener("click", e => {
  const doc = e.target.closest("[data-doc]");
  if(doc){ const k=doc.dataset.doc; view={mode:"doc", key:k, slug:k.split("/")[0]};
    $("#rail").classList.remove("open"); render(); return; }
  const sec = e.target.closest("[data-sec]");
  if(sec && !sec.disabled){ view={mode:"sec", slug:sec.dataset.sec};
    $("#rail").classList.remove("open"); render(); return; }
  if(e.target.closest("[data-cert]")){ view={mode:"cert"};
    $("#rail").classList.remove("open"); render(); return; }
  if(e.target.closest("#home")){ view={mode:"home"}; render(); return; }
  if(e.target.closest("#print")){ window.print(); return; }
  const tr = e.target.closest("[data-track]");
  if(tr){ track = tr.dataset.track; render(); }
});
$("#railtoggle").addEventListener("click", () => {
  const open = $("#rail").classList.toggle("open");
  $("#railtoggle").setAttribute("aria-expanded", open);
});
render();
</script>
</body>
</html>
"""

out = Path(ARGS.out)
if out.parent != Path(""):
    out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(HTML.replace("__PAYLOAD__", PAYLOAD), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
