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
```

Requirements: pandoc 3.x, Python 3.11+, local Chrome, `pip install -r requirements.txt`.

## Sources and outputs

- `markdown/dialectics.md`, `markdown/dialectics_en.md` — book text; the user owns the prose.
- `book.toml` — site settings and one `[editions.<code>]` table per language.
- `docs/assets/` — CSS, JS, fonts (source files even though published).
- `templates/` — layout, print, and landing shells.
- `scripts/` — font subsetting, PDF bookmarks, LaTeX-to-text for EPUB.
- Generated: `docs/index.html`, `docs/zh/*`, `docs/en/*`, `docs/*/dialectics.pdf|epub`.

Never hand-edit generated files. Change sources, assets, config, or templates, then rebuild.

## Bilingual rules

- The landing page is the only place that exposes PDF/EPUB downloads. Reading pages (`docs/zh`, `docs/en`) must not link downloads; they link to each other for language switching.
- The landing page selects its language from `localStorage` or `navigator.language` and persists manual choices. Keep this client-side.
- UI strings live in the `UI` dict in `build.py`. Adding a language means adding an edition table, a source file, and a `UI` entry; slugs and output paths derive from `code`.
- Titles may contain `*emphasis*`; use `title_html()` for headings and `title_text()`/full_title for TOC, navigation, and bookmarks.
- A leading `★` marks entry-level chapters; a trailing `（…）` or `(How ...)` becomes a subtitle line.

## Non-obvious constraints

- **Chinese web fonts come from a CDN.** Pages load Fontsource's unicode-range chunks (`book.toml` → `[fonts] chinese_cdn`), 400 weight only by default (`web_bold = false`); bold is synthesized. Do not commit CJK font files to `docs/`.
- **PDF fonts are generated locally.** `prepare_fonts` writes Noto 400/700 subsets to `build/fonts/` (ignored); they are embedded into the PDF. Static instances are mandatory: variable fonts make Chromium emit Type3 glyphs and inflate PDFs to about 24 MB.
- **English fonts are committed.** Newsreader (400/700/400 italic, about 100 KB) is used by web and PDF and embedded into the English EPUB.
- **Currency dollars.** English prose must escape money as `\$`. The EPUB math converter only matches unescaped `$...$`; do not remove the negative lookbehind or prose will be wrapped into formulas.
- **Cover sizing.** The cover uses absolute `inset` inside a fixed-height page; `height: 100%` plus margins created a blank second page.
- **PDF bookmarks need page numbers.** Chromium writes named destinations only for linked anchors. Parts/chapters resolve from those; sections (`h3`) use line-start text search in `scripts/pdf_toc.py`. Advance the cursor for named entries or the preface guide page matches first.
- **Printed TOC has no page numbers**; navigation belongs to PDF bookmarks and the web sidebar.
- **EPUB is XHTML.** Self-close void tags. Scope string replacements to headings; global replacements previously corrupted code spans.
- **Asset cache busting.** Page templates append `?v=<timestamp>` to CSS/JS. Without it, browsers keep old styles after a rebuild.
- **Sidebar scroll and resume keys are per edition** (`dialectics.nav.<code>`, `dialectics.resume.<code>`).

## Verification

Before committing:

1. `make check` and `make` complete.
2. Landing: correct language by browser locale; manual switch persists after reload; downloads point to the chosen language.
3. Reading pages: no PDF/EPUB links; language switch goes to the other edition; subtitles and stars render.
4. PDFs: one-page cover; three-level bookmarks; English body uses Newsreader, Chinese uses Noto. Chinese pages load the Fontsource CSS and only fetch chunks for visible text.
5. EPUBs: all `.xhtml`, `.opf`, `.ncx` parse as XML; no raw `<br>`; no `<math>`; currency renders as text, not formulas.
6. Privacy: `git grep -n "qliu23\|/Users/" docs` returns nothing.

## Committing

Commit source changes and regenerated `docs/` together. Do not commit `build/`, `.cache/`, `__pycache__/`, `.DS_Store`, or `docs/assets/fonts/src/`.
