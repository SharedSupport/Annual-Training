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

## Hosting

**GitHub Pages (current).** `.github/workflows/github-pages.yml` builds and
publishes to https://sharedsupport.github.io/Annual-Training/ on every push to
`main`, or on demand from the Actions tab. One-time setup: Settings > Pages >
Build and deployment > Source: **GitHub Actions**. The build passes
`--base /Annual-Training/` because the site lives under the repository path.

**Azure Static Web Apps (later).** `.github/workflows/azure-static-web-apps.yml`
does the same deploy to Azure, on demand only. It needs the app created in the
portal with deployment source **Other**, and its deployment token stored as the
secret `AZURE_STATIC_WEB_APPS_API_TOKEN`. `build_site.py` already writes the
`staticwebapp.config.json` it needs.

Both use `.github/actions/build-site`, which downloads the binder zip from the
`BINDER_ZIP_URL` secret (a private link, currently Dropbox), extracts it, and
builds. Without that secret the build falls back to the text embedded in the
prototype and says so. To update content: replace files in the zip, then re-run
the deploy workflow.
