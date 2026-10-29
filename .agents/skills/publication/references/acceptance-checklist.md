# Acceptance Checklist

Run from the repository root before committing. Mark each item with the command or observation that proves it.

## Build

- [ ] `make check` passes.
- [ ] `make verify` passes; `make verify-full` passes after changing PDF/EPUB generation.
- [ ] Visual baselines were reviewed, not blindly updated.
- [ ] No stale generated files remain (the builder removes old `*.html`, PDF, EPUB, Markdown copies).
- [ ] `docs/assets/` was not deleted.

## Landing page

- [ ] Opens in the browser's language; unknown locales fall back to the configured default.
- [ ] Manual language switch changes the visible edition and persists after reload.
- [ ] PDF/EPUB buttons point to the selected edition's files.
- [ ] Theme toggle works and persists; system preference is respected on first visit.
- [ ] Share metadata has absolute `og:url` and `og:image`; the image returns 200.
- [ ] AI button copies the book prompt and shows inline success/failure feedback.

## Reading pages

- [ ] `/zh/` and `/en/` (or all editions) open; sidebar, pager, and catalog work.
- [ ] No PDF/EPUB download links on reading pages.
- [ ] Language switch goes to the other edition's home.
- [ ] Stars, subtitles, tables, code, math, and footnotes render.
- [ ] Theme toggle works; `auto` follows the system.
- [ ] Resume link returns to the last chapter for that edition.
- [ ] Sidebar scroll position survives navigation.
- [ ] Chapter AI button copies the chapter prompt with the correct absolute URL.
- [ ] 500px viewport: `scrollWidth === clientWidth`; no horizontal panning.
- [ ] Feedback is visible without scrolling and is not covered by browser UI.

## PDF

- [ ] Exactly one cover page; no blank page after it.
- [ ] Running header and page numbers appear on body pages; not on cover/front matter/part pages.
- [ ] Printed TOC has no page numbers.
- [ ] Outline has three levels and the expected entry count.
- [ ] Outline entries open the correct pages.
- [ ] Chinese body uses the CJK face; English body uses the Latin face.
- [ ] File size is plausible (a few MB, not tens of MB); text is selectable.

## EPUB

- [ ] Every `.xhtml`, `.opf`, `.ncx` passes `xmllint --noout`.
- [ ] No raw `<br>` and no `<math>` remains.
- [ ] Currency renders as text, not formulas.
- [ ] Cover, TOC, code, tables, and math display in at least two readers.
- [ ] Fonts are embedded and render offline.
- [ ] The file opens from a clean import (readers cache old copies).

## Privacy and repository

- [ ] `git grep -n "/Users/\|username" docs` returns nothing.
- [ ] `.gitignore` excludes `build/`, `.cache/`, `__pycache__/`, `.DS_Store`, and font sources.
- [ ] Sources and regenerated `docs/` are in the same commit.
- [ ] `docs/.nojekyll` and `docs/CNAME` are present when using GitHub Pages with a custom domain.

## Evidence to report

State the commands run, page counts, bookmark counts, file sizes, and any checks not performed. Do not claim a check that was not run.
