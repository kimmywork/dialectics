---
name: publication
description: Publish a Markdown manuscript as a static website with PDF and EPUB editions. Use when turning a .md book or long document into a browsable reading site, adding reading interactions (language-aware landing page, themes, resume, AI copy, share cards), generating print-quality PDF and reflowable EPUB files, or maintaining a Markdown-to-multi-format publishing pipeline.
---

# Publication

Turn one or more Markdown manuscripts into a static reading site plus PDF and EPUB editions, committed to `docs/` for GitHub Pages. No CI and no server runtime.

## Use when

- A user wants a `.md` file published as a website with chapters, navigation, and downloads.
- A book needs bilingual editions, PDF, EPUB, or social share cards.
- An existing static publication needs a new interaction, format, or language.

## Inputs and outputs

Inputs: manuscript `.md` files, `book.toml` metadata, CSS/JS/templates, locally installed `pandoc`, Python 3.11+, and Chrome/Chromium/Edge.

Outputs: `docs/index.html` (landing), `docs/<code>/index.html` plus one page per part/chapter, `docs/<code>/dialectics.pdf`, `docs/<code>/dialectics.epub`, and `docs/<code>/dialectics.md` for AI retrieval.

## One-step flow

1. **Inventory.** Confirm language editions, title/subtitle, author, license, repository, site URL, and whether both PDF and EPUB are required.
2. **Scaffold.** Create `book.toml`, `markdown/`, `templates/`, `scripts/`, and `docs/assets/`. Keep generated pages and hand-written assets separate.
3. **Parse once.** Build a Chapter/Part model from headings; derive stable slugs, labels, subtitles, stars, and section anchors. Render each chapter body once and reuse it for web, PDF, and EPUB.
4. **Build the site.** Render a language-aware landing page, per-edition home, part pages, chapter pages, sidebar, pager, and metadata. Add theme, language switch, progress, resume, and AI copy behavior.
5. **Build the PDF.** Render a print HTML shell, concatenate print CSS, print with Chromium, then add a three-level outline with `pypdf`.
6. **Build the EPUB.** Preprocess the Markdown (XHTML-safe tags, Unicode math, scoped heading rewrites), then invoke `pandoc --to=epub3` with metadata, cover, and embedded fonts.
7. **Verify.** Run the acceptance checks in `references/acceptance-checklist.md`; inspect mobile overflow, PDF bookmarks, EPUB XML validity, fonts, share metadata, and privacy.
8. **Publish.** Commit sources and regenerated `docs/` together, push `master`, and serve GitHub Pages from `/docs`.

## Non-negotiables

- The Markdown manuscript is the single source of truth. Never hand-edit generated HTML/PDF/EPUB; change sources and rebuild.
- Use relative links inside the site. Absolute URLs belong only in canonical/OG tags, AI prompts, and generated metadata.
- Put PDF/EPUB downloads only on the landing page. Reading pages link to the other edition, not to downloads.
- Keep language choice and theme client-side and persistent. Never require a backend.
- Escape all content in HTML; render titles with an emphasis-aware function and strip emphasis for plain-text contexts.
- Use static font instances for PDF. Variable fonts become Type3 glyphs and inflate the file.
- EPUB must be valid XHTML. Close void tags, avoid raw MathML, and keep currency `$` out of math detection.
- Avoid horizontal scrolling at every breakpoint; keep feedback inline in the document flow.
- Validate before committing. Commit sources and generated `docs/` in the same change.

## Reference map

- `references/pipeline-blueprint.md` — repository layout, config, parsing model, build stages, and code patterns.
- `references/web-experience.md` — landing page, reading shell, themes, resume, AI copy, share cards, fonts, CSS.
- `references/print-and-epub.md` — print CSS, Chromium PDF, bookmarks, EPUB preprocessing, validation.
- `references/failure-catalog.md` — symptoms, causes, and fixes distilled from a real publication history.
- `references/history-and-decisions.md` — commit-level timeline and the decisions behind the current pipeline.
- `references/acceptance-checklist.md` — the final gate before committing.
