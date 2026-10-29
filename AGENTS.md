# AGENTS.md

## Scope

A bilingual book publisher. Two Markdown manuscripts produce a language-aware landing page and two reading sites plus PDF/EPUB per language. Everything is written into `docs/`, committed, and served by GitHub Pages from `master` / `docs`. Do not add CI; builds run locally.

## Commands

```bash
make check   # compile build.py and scripts/*
make         # HTML, PDF, EPUB for both languages
make web     # HTML only
make pdf     # HTML + both PDFs
make epub    # HTML + both EPUBs
make serve   # preview at http://localhost:8000
make clean   # remove generated pages, PDFs, EPUBs, caches
make fonts   # rebuild Chinese and English font subsets
make verify  # web build + artifact checks + Playwright regression
make verify-full # full build (HTML/PDF/EPUB) + the same checks
make test-setup  # npm install + Playwright Chromium
npm run test:ui    # interactive Playwright debugging
npm run test:update # refresh visual baselines, then review the diff
```

Requirements: pandoc 3.x, Python 3.11+, local Chrome, `pip install -r requirements.txt`. Verification also needs Node 20+, `npm install`, and `npx playwright install chromium`.

## Sources and outputs

- `markdown/dialectics.md`, `markdown/dialectics_en.md` — book text; the user owns the prose.
- `book.toml` — site settings and one `[editions.<code>]` table per language.
- `docs/assets/` — CSS, JS, fonts (source files even though published).
- `templates/` — layout, print, and landing shells.
- `scripts/` — font subsetting, PDF bookmarks, LaTeX-to-text for EPUB, artifact verification.
- `tests/` — Playwright build, interaction, and visual regression specs; `tests/__screenshots__/` holds committed baselines.
- `playwright.config.js`, `package.json` — local static server, browser project, and test commands.
- Generated: `docs/index.html`, `docs/zh/*`, `docs/en/*`, `docs/*/dialectics.pdf|epub`.

Never hand-edit generated files. Change sources, assets, config, or templates, then rebuild.

## Bilingual rules

- The landing page is the only place that exposes PDF/EPUB downloads. Reading pages (`docs/zh`, `docs/en`) must not link downloads; they link to each other for language switching.
- The landing page selects its language from `localStorage` or `navigator.language` and persists manual choices. Keep this client-side.
- UI strings live in the `UI` dict in `build.py`. Adding a language means adding an edition table, a source file, and a `UI` entry; slugs and output paths derive from `code`.
- Titles may contain `*emphasis*`; use `title_html()` for headings and `title_text()`/full_title for TOC, navigation, and bookmarks.
- A leading `★` marks entry-level chapters; a trailing `（…）` or `(How ...)` becomes a subtitle line.

## Non-obvious constraints

- **Chinese web fonts come from a CDN.** Pages load Fontsource's unicode-range chunks (`book.toml` → `[fonts] chinese_cdn`), 400 and 700 weights by default (`web_bold = true`); turning it off saves about 1 MB but synthesizes bold. Do not commit CJK font files to `docs/`.
- **PDF fonts are generated locally.** `prepare_fonts` writes Noto 400/700 subsets to `build/fonts/` (ignored); they are embedded into the PDF. Static instances are mandatory: variable fonts make Chromium emit Type3 glyphs and inflate PDFs to about 24 MB.
- **English fonts are committed.** Newsreader (400/700/400 italic, about 100 KB) is used by web and PDF and embedded into both EPUBs.
- **Mixed-script stack is `"Newsreader", "Noto Serif SC", …`** for Chinese too: Latin/digits use Newsreader, CJK falls back to the CDN Noto chunks. Chinese pages preload Newsreader.
- **Currency dollars.** English prose must escape money as `\$`. The EPUB math converter only matches unescaped `$...$`; do not remove the negative lookbehind or prose will be wrapped into formulas.
- **Cover sizing.** The cover uses absolute `inset` inside a fixed-height page; `height: 100%` plus margins created a blank second page.
- **PDF bookmarks need page numbers.** Chromium writes named destinations only for linked anchors. Parts/chapters resolve from those; sections (`h3`) use line-start text search in `scripts/pdf_toc.py`. Advance the cursor for named entries or the preface guide page matches first.
- **Printed TOC has no page numbers**; navigation belongs to PDF bookmarks and the web sidebar.
- **EPUB is XHTML.** Self-close void tags. Scope string replacements to headings; global replacements previously corrupted code spans.
- **Asset cache busting.** Page templates append `?v=<timestamp>` to CSS/JS. Without it, browsers keep old styles after a rebuild.
- **AI prompt button.** The landing page copies a per-language book prompt linking to `/zh/dialectics.md` or `/en/dialectics.md`; every chapter page has the same button with a chapter prompt (book title, chapter title, absolute page URL). Both prompts ask for a structured analytical approach without prescribing a specific book method. The build copies the manuscripts there; keep URLs and prompt text in sync when editions or slugs change. Copy/status logic lives in `docs/assets/js/ai-copy.js` and is shared with the landing page.
- **Sidebar scroll and resume keys are per edition** (`dialectics.nav.<code>`, `dialectics.resume.<code>`).

## Verification

Before committing:

1. `make check` and `make verify` complete. Use `make verify-full` before a release or after changing PDF/EPUB generation.
2. Playwright covers: build artifacts and internal links; locale detection and persistence; manual language switch; light/dark/system theme; downloads only on the landing page; catalog, pager, keyboard navigation, language links, resume, sidebar scroll, progress and drawer animation; chapter AI prompt content; math, tables, subtitles; mobile overflow.
3. Visual baselines live in `tests/__screenshots__/` and must be reviewed. Refresh with `npm run test:update`; commit changed baselines only when the visual diff is intended.
4. Manual/long-form checks: PDFs have a one-page cover and three-level bookmarks; EPUBs open in at least two readers and render math/currency as text.
5. Privacy: `git grep -n "qliu23\|/Users/" docs` returns nothing.

Do not commit `test-results/`, `playwright-report/`, `node_modules/`, or `blob-report/`.

## Committing

Commit source changes and regenerated `docs/` together. Do not commit `build/`, `.cache/`, `__pycache__/`, `.DS_Store`, or `docs/assets/fonts/src/`.
