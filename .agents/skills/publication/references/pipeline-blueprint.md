# Pipeline Blueprint

## Repository layout

```text
book.toml                  site + per-edition metadata
build.py                   one entry point: parse -> render -> web -> PDF -> EPUB
markdown/<name>.md         manuscripts, one per edition
templates/
  layout.html              reading shell
  landing.html             language-aware landing page
  print.html               print shell
scripts/
  prepare_fonts.py         static instance + subset + woff2
  pdf_toc.py               pypdf outline post-processing
  latex_text.py            LaTeX -> Unicode for EPUB
docs/
  index.html               generated landing page
  <code>/                  generated pages, PDF, EPUB, Markdown copy
  assets/                  hand-written CSS/JS/fonts/share images
```

`docs/` is both the output directory and the GitHub Pages root. Keep `docs/assets/` under version control; never let the builder delete it.

## Configuration

Use TOML so Python's `tomllib` can read it without dependencies. One `[editions.<code>]` table per language:

```toml
[site]
url = "https://example.com"
default = "zh"

[pdf]
page_size = "A4"

[editions.zh]
code = "zh"
language = "zh-CN"
title = "Book Title"
subtitle = "Subtitle"
full_title = "Book Title: Subtitle"
author = "Author"
description = "..."
source = "markdown/book.md"
homepage = "https://example.com"
repo = "https://github.com/user/repo"
license = "CC BY-NC-SA 4.0"
license_url = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
keywords = "..."

[fonts]
family = "Noto Serif SC"
chinese_cdn = "https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-sc@5"
web_bold = true
source = ""
newsreader_source = ""
```

Derive output paths, slugs, and navigation from `code`; adding a language should mean adding a table and a source file, not editing rendering code.

## Build stages

1. Load config; validate every source file exists.
2. Parse each manuscript into `Book`, `Part`, and `Chapter` objects.
3. Render each part intro and chapter body once with pandoc (`--to=html5 --mathml --wrap=none`).
4. Render all web pages from the model.
5. Subset fonts from the rendered text.
6. Re-render when font paths are known.
7. Write landing, pages, Markdown copies.
8. Print PDF; add outline.
9. Build EPUB.
10. Clean stale generated files without touching `docs/assets/`.

## Parsing contract

Use two heading levels for structure and lower levels for prose:

- `#` -> part or appendix cover.
- `##` -> chapter.
- `###` and below -> sections inside a chapter.
- A leading `★` marks an entry-level chapter; strip it before parsing and store it as a flag.
- A trailing `（...）` or `(...)` becomes a subtitle line when the remainder is long enough.
- Split labels such as `第 1 章`, `Chapter 1`, `附录 A`, `Appendix A`, `Part I`, `前言`, `Preface` from the name.
- Do not use the raw title as the slug. Use stable patterns: `ch01`, `appendix-a`, `part-1`, `preface`, `prologue`, `epilogue`.

```python
def slugify_chapter(title, index):
    if title.startswith(("前言", "Preface")): return "preface"
    if title.startswith(("序章", "Prologue")): return "prologue"
    if title.startswith(("结语", "Epilogue")): return "epilogue"
    if m := re.match(r"^第\s*(\d+)\s*章", title): return f"ch{int(m.group(1)):02d}"
    if m := re.match(r"^Chapter\s+(\d+)", title): return f"ch{int(m.group(1)):02d}"
    if m := re.match(r"^附录\s*([A-Za-z])", title): return f"appendix-{m.group(1).lower()}"
    if m := re.match(r"^Appendix\s+([A-Za-z])", title): return f"appendix-{m.group(1).lower()}"
    return f"ch{index:02d}-x"
```

Keep titles in three forms:

- Display HTML: `title_html()` converts `*emphasis*`, escapes the rest.
- Plain text: `title_text()` removes `*`.
- Full title: title plus subtitle, used in TOC, navigation, bookmarks, and metadata.

## Page model

Every page needs: language, edition code, title, description, canonical URL, OG image, nav markup, body markup, asset prefix, asset version, labels, language-switch link.

Generate:

- Landing: one section per edition; only the active one is visible.
- Edition home: hero, stats, license, resume link, catalog.
- Part page: label, title, intro, chapter list.
- Chapter page: kicker, title, subtitle, optional AI button, prose, pager.
- Footer on every reading page: book title, author/year/license/repo.

## Asset versioning

Append `?v=<max mtime of docs/assets>` to every CSS/JS URL. Without it, browsers keep stale styles after a rebuild. Do not use a random value: keep it stable between identical builds.

## Fonts

- Chinese web: load Fontsource/Noto Serif SC from a CDN with `unicode-range` chunks; do not commit CJK fonts.
- Latin web/PDF/EPUB: commit a small Newsreader subset (400/700/400 italic).
- PDF: instantiate static 400/700 weights and subset to the characters actually used. Put them in ignored `build/fonts/`.
- Mixed stack: Latin font first, CJK second, generic serif last. Preload the Latin font on CJK pages too.
- Cache font subsets by character digest and source mtime; regenerate when new characters appear.

## Commands

Provide a `Makefile` with short targets:

```make
make check   # py_compile build.py scripts/*.py
make         # web + PDF + EPUB
make web     # HTML only
make pdf     # HTML + PDFs
make epub    # HTML + EPUBs
make serve   # local preview
make clean   # remove generated pages/PDF/EPUB and caches
make fonts   # rebuild subsets
```

Use one `build.py` entry point with `--no-pdf`, `--no-epub`, `--no-fonts`, and `--clean` flags. Do not split the pipeline into scripts that must be run in a remembered order.

## Publishing

- Output to `docs/` and serve GitHub Pages from `master` / `docs`.
- Add `docs/.nojekyll`.
- Put the custom domain in `docs/CNAME`.
- Use relative links so project pages and custom domains both work.
- Commit sources and generated output together.
