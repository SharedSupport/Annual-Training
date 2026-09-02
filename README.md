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

## Signed sheets

Until the fill-and-flatten submission endpoint exists, the sign page emails the
three sheets: "Email your signed sheets" opens the staff member's own mail app
with the sheets filled in, addressed to `SIGN_TO` in `training_config.py`
(currently rwilliams@sharedsupport.org). The email arriving from the staff
member's own mailbox is what says who sent it. Change `SIGN_TO`, or pass
`--sign-to` at build time, to redirect it. Passing `--submit-url` switches the
form to POSTing JSON to an endpoint instead.

## Hosting: Azure Static Web Apps

`.github/workflows/azure-static-web-apps.yml` builds and deploys on every push
to `main`. Setup:

1. Create a Static Web App in the Azure portal with deployment source
   **Other** (so the portal doesn't add its own workflow), Free plan is fine.
2. Copy its deployment token (Overview > Manage deployment token) into the
   repository secret `AZURE_STATIC_WEB_APPS_API_TOKEN`.
3. Optional but recommended: put the binder zip somewhere private the workflow
   can download it from (a Blob container with a SAS link works) and store the
   link in the secret `BINDER_ZIP_URL`. With it the deployed site is built from
   the real binder; without it, from the text embedded in the prototype.

`build_site.py` writes `staticwebapp.config.json` into `site/`, so clean URLs,
the 404 page, and cache headers come with the build.

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
