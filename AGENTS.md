# AGENTS.md

## Scope

One Markdown manuscript produces three committed artifacts in `docs/`: an HTML site, an A4 PDF, and an EPUB. GitHub Pages serves `master` / `docs`. Do not add CI; builds run locally and artifacts are committed.

## Commands

```bash
make check   # compile build.py and scripts/*
make         # build HTML, PDF, EPUB into docs/
make web     # HTML only
make pdf     # HTML + PDF
make epub    # HTML + EPUB, no PDF
make serve   # preview at http://localhost:8000
make clean   # remove generated pages, PDF, EPUB, caches
make fonts   # rebuild the font subset
```

Requirements: pandoc 3.x, Python 3.11+, local Chrome, `pip install -r requirements.txt`.

## Sources

- `docs/dialectics.md` — book text; the user owns the prose, do not rewrite it.
- `book.toml` — title, author, homepage, license, source path.
- `templates/` — page shells.
- `docs/assets/` — CSS, JS, fonts. These are source files even though they are published.
- `scripts/` — font subsetting, PDF bookmarks, LaTeX-to-text for EPUB.

Never hand-edit generated files: `docs/*.html`, `docs/dialectics.pdf`, `docs/dialectics.epub`. Change source, assets, or templates, then rebuild.

## Manuscript conventions

- `# ` part, `## ` chapter, `### ` section.
- A leading `★` on a chapter marks an entry-level chapter. The build renders it as a badge and keeps TOC numbers aligned.
- A trailing `（…）` on a chapter title becomes a smaller subtitle line in every output.
- Leave a blank line before lists.
- Use single backslashes in LaTeX. Control characters in the source mean corrupted escapes; the build warns about them.
- EPUB math is Unicode text. `scripts/latex_text.py` handles fractions, scripts, Greek letters, arrows, and operators; unknown commands are reported. Extend the converter instead of returning to MathML.

## Non-obvious build constraints

- **Fonts must be static instances.** Variable fonts make Chromium emit Type3 glyph fonts and inflate the PDF from about 4 MB to 24 MB. `scripts/prepare_fonts.py` instances the variable font at 400/700 before subsetting.
- **Cover sizing.** The cover uses absolute `inset` inside a fixed-height page. `height: 100%` plus margins overflowed onto a second page.
- **PDF bookmarks need page numbers.** Chromium writes named destinations only for linked anchors. Parts and chapters resolve from those destinations; sections (`h3`) use line-start text search in `scripts/pdf_toc.py`. Keep the section search line-based and advance the cursor for named entries, or the preface guide page matches first.
- **The printed TOC intentionally has no page numbers.** Navigation belongs to PDF bookmarks and the web sidebar.
- **EPUB is XHTML.** Self-close void tags (`<br />`). Never run global string replacements that reach code spans (for example the backticked tag name in the preface); scope replacements to headings.
- **EPUB math.** WeChat Reading and Apple Books ignore MathML, so formulas are converted to Unicode text at packaging time.
- **Sidebar scroll.** `docs/assets/js/app.js` stores the nav scroll position in `sessionStorage` so page changes do not jump to the top.

## Verification

Before committing:

1. `make check` and `make` complete.
2. PDF: cover is one page; bookmarks have three levels (part, chapter, section); printed TOC shows subtitles.
3. EPUB: every `.xhtml`, `.opf`, and `.ncx` parses as XML; no `<math>` elements; no raw `<br>`; formulas appear as text.
4. Web: home, one chapter, and one part page render; mobile actions show a single full-width primary button.
5. Privacy: `git grep -n "qliu23\|/Users/" docs` returns nothing.

Quick checks:

```bash
python3 - <<'PY'
from pypdf import PdfReader
r = PdfReader("docs/dialectics.pdf")
def walk(items, depth=0, out=None):
    out = out if out is not None else []
    for item in items:
        if isinstance(item, list):
            walk(item, depth + 1, out)
        else:
            out.append(depth)
    return out
print("pages", len(r.pages), "max bookmark depth", max(walk(r.outline)))
PY
unzip -l docs/dialectics.epub | head
```

## Committing

Commit source changes and regenerated `docs/` artifacts together. Do not commit `build/`, `.cache/`, `__pycache__/`, `.DS_Store`, or `docs/assets/fonts/src/`.
