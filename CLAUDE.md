# Shared Support Annual Training — Digital Binder

Turning the Annual Training binder into an internal website for ~300 staff, replacing a
95 MB interactive PDF that staff currently have to download and open in a specific app.

## Why this exists

The digital binder PDF **contains zero link annotations**. The colored section tabs down
the right edge, the ‹ › arrows, the "?" button, and the "Go Back To Where You Left Off"
control are all flat artwork. Nothing is clickable in any reader. The only working
navigation is 12 PDF bookmarks — which is why staff are hunting for a bookmark pane. The
navigation they can see does nothing.

## Current state

Build-order step 1 is done: `build_site.py` renders `content/content.json` into
`site/`, a static multi-page site (section pages, document pages with jump lists,
search, print packets, scanned pages as images, signature sheets). The older
single-file prototype (`training-site-prototype.html`, `build_prototype.py`) is
kept for sharing but superseded.

    pip install -r requirements.txt
    python extract_binder.py "source/Annual Training - Paper Binder" --out content
    python build_site.py --source "source/Annual Training - Paper Binder"

No binder to hand? `python content_from_prototype.py` rebuilds `content.json`
from the committed prototype (no PDFs, no page images, Incident Management cut at
45k characters). `training_config.py` holds the section-to-day map, sheet wording,
display title fixes, and the licensed-material list shared by both builders.

## Source of truth: the paper binder folders

**Extract from the paper binder zip, not the digital binder PDF.**

The seven numbered folders match the printed table of contents exactly. The PDF bookmarks
never did — 9 entries, an invented standalone MANDT section, no Independent Trainings, and
Medication Administration pinned to a single page.

Each policy is its own file with a revision date in the filename, so the site shows staff
what they're reading and when it last changed.

**The paper files are newer than the digital binder.** The InDesign export was built
03/04/2026; Abuse Policy is 7.10.26, Fleet Safety 07.13.26, Community Participation
July2026. Anyone reading the digital binder is reading stale policy.

## How the training actually runs

Day 1 and Day 2 are **live virtual sessions on Teams**, not self-paced coursework. The
site is the material staff follow along with and refer back to. That's why there is no
progress tracking and no "mark complete" — the signature submission is the only
confirmation.

| Stage | Delivery | Sections |
|---|---|---|
| Day 1 | Virtual, Teams | DRC Policies, Incident Management & Abuse, Driver's Safety, Disaster Preparedness |
| Independent | On their own, before Day 2 | Independent Trainings |
| Day 2 | Virtual, Teams | Alternative Routes, Medication Administration |
| Day 3 | In person | Skills session, fit testing, Q&A — nothing to read |

The section→day mapping is inferred from certificate topic names and **still needs the
training department to confirm it**.

## No accounts

Staff open this on a personal device without signing in. Consequences:

- No progress persistence. Nothing to store per person, no cookies, no session.
- **The signature form is an unauthenticated POST.** Anyone can submit under any name.
  Manageable because the training department knows who attended both Teams sessions and
  Day 3 is in person, but the form is corroborating evidence, not the roster.

Mitigations, cheapest first: reconcile submissions against the roster; log UTC timestamp,
source IP, and user agent; email the completed packet to the staff member's **directory**
address, never one typed into the form; rate-limit and CAPTCHA the endpoint since it
generates PDFs and sends mail. A per-person link emailed at the start of training would
identify submitters without building logins.

## Signature packets — fill, don't rebuild

`Annual_Training_Packet_BLANK_RECERT.pdf` and `..._REVIEW.pdf` are **already fillable
AcroForms**, 3 pages and 14 named fields each. Never re-typeset the certificates — fill
the existing blank with pypdf (`update_page_form_field_values`), flatten, and the output
is byte-identical to what the training department already uses.

Field names are track-suffixed: `employee_name_recert` / `employee_name_review`, likewise
`job_title`, `training_date_range`, `day1_date`, `day2_date`, `day3_date`,
`staff_signature`, `trainer_date_p1`, `fire_employee_name`, `fire_employee_signature`,
`fire_training_date`, `facpr_date_top`, `facpr_employee_name`, `facpr_employee_signature`.

Pages 1 and 2 are identical across both packets. Only page 3 differs:

| | RECERT | REVIEW |
|---|---|---|
| Title | FA/CPR/AED - Recertification | FA/CPR Skill Session - For Review ONLY |
| Hours | 2.75 | 2.0 |

Submission order: **sign → fill → flatten → store → email.** Email is delivery, not the
record. Store the flattened PDF in Blob under a versioned container — that's the artifact
a licensing surveyor asks for.

## Extractor conventions

- `EXCLUDE` — files kept off the site, with the reason recorded so a re-run doesn't
  reinstate them. Currently: the DCI cheat sheet (DCI is retired; time and attendance is
  in iCM).
- `CORRECTIONS` — wording fixed on the site because the source document is out of date.
  Each entry must match **exactly once**; zero or multiple matches warn rather than
  silently no-op. Currently: HEAVY HITTER LIST, "DCI clock in and clock out" → "iCM".
  **Every entry here is a source edit someone still owes** — the site and the PDF
  currently disagree. If the list grows, fix the documents instead.
- `LINKS` — external resources per section. Currently the iCM Time & Attendance guide on
  Independent Trainings.
- Print packets ("Easy Print …", "… Packet") are excluded from extraction and kept as the
  section's printable download. Any packet sitting beside an excluded file is flagged
  for review, and the build **rebuilds it** from the section's current individual files
  (generated cover page, licensed docs left out, retired pages gone) rather than
  linking the binder's copy. The binder's copy still needs reissuing.
- `CORRECTIONS` are applied to the PDF download as well as the page text: the old
  phrase is redacted and the new one written on the same baseline, shrunk to the
  original width. Downloads and print packets open in a new tab so the reader keeps
  their place.
- `EMBEDS` (in `training_config.py`) puts a video above a document's text; the TED
  talk is embedded from YouTube.
- `NOT_CONTENT` — section cover pages, skipped without flagging the packets beside them
  (unlike `EXCLUDE`, which marks a packet as still containing retired pages).
- `AS_PAGES` (in `training_config.py`) — documents with a text layer that still render as
  page images because the text reads badly: the Auto Accident Form with its scene diagram.
  Their text still feeds search.
- `TITLE_FIXES` and `LICENSED` (in `training_config.py`) are display-level too. Title
  fixes cover filename typos ("Referance") and a person's name in a filename; the
  licensed entry keeps the Red Cross card as page images with a notice and no download.
- Lines that repeat on most pages (running headers, "3 Revised 04/07/20" footers, bare
  page numbers) are dropped as page furniture. Run-in labels ("SCOPE OF POLICY:"),
  Roman-numeral section titles, and bold single-line blocks become headings; a lone
  numeral merges with the title on the next line; a large title wrapped over several
  lines is one heading.
- Text is extracted **block by block in content order**, not by sorting every line on
  the page by y. The y-sort interleaved the two columns of the Workers Comp brochure
  line by line and produced one 45,000-character paragraph for the 42-page Incident
  Management policy. Bullets become real `<ul>` lists; wrapped bullet lines stay in
  their item. `build_site.py` also splits any surviving over-long paragraph at sentence
  boundaries for display, and warns how many it touched.

### Gotchas that already bit once

- **Slugs come from titles containing curly apostrophes.** "Driver's Safety" slugged to
  `driver-s-safety` and silently mismatched the delivery map. Apostrophes are now stripped
  before slugifying, and `build_prototype.py` hard-fails on any unknown slug. Keep that
  check — a `.get()` fallback is how it hid the first time.
- **Filenames are inconsistent**: underscores, leading index numbers ("2 - Link to TED
  Talk"), run-together words ("SexualHealthPersonalRelationsSexualityPolicy2019"). `tidy()`
  normalises them; the date regex whitelists real month names so "Policy2019" isn't parsed
  as a revision date.
- **Rotated text.** The digital binder's tab labels are rotated and baked onto every page.
  Extraction filters by line writing direction. Keep that if the PDF path is ever revived.
- **Bullet glyphs on empty lines** produced empty `<li></li>` elements. Filtered now.

## Known content problems

Raise these with the training department; several block a truthful attestation.

1. **The attestation says "all 15 sections."** There are 7. Staff can't attest to reading
   15 sections on a site showing 7. The prototype drops the count until this is settled.
2. **Medication Administration has one 2-page file** ("Topics to be covered") whose text
   layer is itself broken ("- mentation of medication", "- ation on PMOF's"). The source
   PDF needs replacing; no extractor change fixes it. The section will look empty.
3. **The Medicaid Waiver & CP packet disagrees with its own individual files.** Its
   Community Participation section is an older version — none of the four pages match
   `Community Participation July2026.pdf`. Printing the packet hands out superseded CP
   guidance.
4. **Address typo in the packets**: pages 1 and 3 read 218 Bridge Avenue, page 2 reads 210.
5. **Hours may double-count.** The certificate says 22.5 total, then FA/CPR certifies
   separately at 2.75 or 2.0 — but Day 3 on that same certificate already lists the
   FA/CPR skills session.
6. **The certificate covers more than the binder.** ~27 listed topics (Mission Statement,
   Worker's Compensation, Fatal Five HCQU, Fit Testing, the TED Talk) have no binder
   content. They're shown as "held outside this site".
7. **Community Participation placement.** The certificate lists it under Day 2; the files
   live in Independent Trainings. One is wrong.
8. **The digital binder still references DCI on pages 18, 20, 82, and 131** — including
   "Direct Care Innovations (DCI) integrated business management platform". The paper
   versions of those policies already dropped it.
9. **Filename typos become page titles**: "First Aid - CPR Referance Card".

## Content stats

61 PDFs, 646 pages, ~371k characters of clean text across 40 readable documents.

| Section | Docs | Image-only | Printables |
|---|---|---|---|
| DRC: Policies | 15 | 1 | 2 |
| Incident Management & Abuse | 1 | 0 | 0 |
| Driver's Safety | 4 | 0 | 2 |
| Disaster Preparedness | 1 | 0 | 1 |
| Independent Trainings | 6 | 1 | 3 |
| Alternative Routes | 12 | 4 | 2 |
| Medication Administration | 1 | 0 | 0 |

Eight files have no text layer (PBIS MANDT at 29 pages, the Red Cross reference card,
Diastat, Fatal 6, Fleet Enema, cover pages). These stay as page images with a download.
The Red Cross card is licensed: on the public site it's a notice only (no images, no
download, the PDF is never copied into `site/`); `--serve-licensed` adds the page images
for a host behind sign-in. **The repo is public**, so never push the binder PDFs to a
branch; the `binder-source` branch was deleted for that reason. The TED Talk file is one line of text with a YouTube link,
so it renders as a link rather than a scan.

A session that needs the PDFs can get them from the extract workflow's `publish_source`
option (`git archive origin/binder-source | tar -x` puts them under `source/`), but
only while the repo is private, and the branch must be deleted straight after.

## Design

The header, navigation, and signature sheets use `static/logo.png` (white on
transparent) on the maroon band when it exists. The sign page reproduces the three
packet pages (certificate with the full topic list, Fire Safety, FA/CPR cover) with the
wording in `training_config.py`, including the trainer's pre-printed signature
(`static/trainer-signature.png`, lifted from the packet at the training department's
request). The attestation states the real section count. Name, dates, and signature are
typed once on the first sheet and cascade to the other two until edited. Each section
shows one print link, preferring the "Easy Print" file. Under 860px the navigation is a
left drawer behind a hamburger button in a maroon top bar.

Palette and section colors are lifted from the printed binder — the maroon and gold of the
wordmark, and the actual tab colors, so the web nav maps to the tabs staff recognize. Body
type is a Minion-adjacent serif because the source is set in Minion Pro. Under 860px the rail
becomes a drawer behind a hamburger button; a lot of this audience reads on a phone mid-shift.

No binder page numbers anywhere — navigation is section and document. The corpus contains
one page cross-reference ("see page 1 of this policy") and it's internal to a document.

## Build order

1. ~~Static site over `content.json`~~ — done (`build_site.py`). Hosted on GitHub Pages
   at sharedsupport.github.io/Annual-Training via `.github/workflows/github-pages.yml`
   (Azure Static Web Apps workflow kept for later; Azure was having issues at setup
   time). Both build through `.github/actions/build-site`, which pulls the binder zip
   from the `BINDER_ZIP_URL` secret so no session or repo ever holds the PDFs.
2. Signature submission: fill the AcroForm blanks, flatten, store, email. **Interim:**
   the sign page opens the staff member's mail app with the sheets addressed to
   `SIGN_TO` (`training_config.py`, currently TrainingDept@sharedsupport.org). No backend,
   and the sender's own mailbox identifies them. `--submit-url` swaps in a POST endpoint.
3. Videos and knowledge checks. The binder already contains fill-in worksheets (the Jane
   Smith scheduling exercise, the site checklist) — cheapest path to interactivity.

Target stack is Azure to match the existing attendance app: Static Web Apps for the site,
FastAPI on App Service or Functions for the submission endpoint, Azure SQL and Blob.
