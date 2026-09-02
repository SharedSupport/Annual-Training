# Shared Support Annual Training — Digital Binder

Internal website replacing the 95 MB interactive Annual Training PDF.

## Setup

    pip install -r requirements.txt

Put the source material in `source/` — see `source/README.md`.

## Build

    python extract_binder.py "source/Annual Training - Paper Binder" --out content
    python build_site.py --source "source/Annual Training - Paper Binder"

`build_site.py` renders `content/content.json` into `site/`, a static multi-page
site: one page per section and per document, a search page over a prebuilt
index, print packets, page images for scanned handouts, the signature sheets,
and a `staticwebapp.config.json` for Azure Static Web Apps. Pass `--base
/Annual-Training/` when hosting under a sub-path (GitHub Pages) and
`--submit-url` to switch the signature form on once the endpoint exists.

Without the binder (a fresh clone, since `source/` is gitignored), recover the
extracted content from the committed prototype and build without `--source`:

    python content_from_prototype.py
    python build_site.py

That build has no PDFs or page images, and the Incident Management policy is
cut at 45,000 characters, because that's all the prototype carries. It's enough
to work on the site; use the binder for anything staff will read.

To serve it locally: `cd site && python -m http.server 8000`.

`extract_binder.py` walks the seven numbered binder folders and writes
`content/content.json`: a section → document tree with cleaned HTML, revision
dates, page counts, image-only flags, print packets, and external links. It
prints a warning for every exclusion, correction, and stale print packet — read
that output, it's how content problems surface.

`build_prototype.py` still renders the older single-file
`training-site-prototype.html` for sharing; it's superseded by `build_site.py`.

## Read first

`CLAUDE.md` has the project context: why this exists, how the training actually
runs, the no-login model, the AcroForm signature packets, extractor conventions,
and the known content problems. `BUILD-BRIEF.md` has the longer-form findings.
