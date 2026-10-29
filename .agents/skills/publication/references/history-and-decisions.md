# History and Decisions

This skill was distilled from a 20-commit publication history. The timeline explains why the pipeline has its current shape; use it to avoid re-litigating decisions that already have evidence.

## Phase 1: manuscript and first framework

1. Two manuscript revisions established the Markdown source as the only editable artifact.
2. The first framework added `build.py`, `book.toml`, a `Makefile`, and output to `docs/`.
   - pandoc renders chapter HTML.
   - Chromium prints A4 PDF.
   - pypdf writes the outline.
   - Fonts are subset to the characters actually used.
3. Early fixes:
   - LaTeX commands were being eaten by escaping; the parser now warns on control characters.
   - A cover with `height: 100%` produced a blank second page; the cover became a fixed-height page with an absolute frame.
   - The printed TOC dropped page numbers; navigation moved to PDF bookmarks and the web sidebar.

## Phase 2: structure and EPUB

4. The manuscript gained `★` entry markers and `[Deep Dive]` labels. Parsing strips the star, stores a flag, and renders a badge only in headings.
5. EPUB generation was added with pandoc, a generated cover, a clickable TOC, and embedded fonts.
6. PDF bookmarks grew to three levels: part, chapter, section.
7. The sidebar scroll position was persisted per edition so chapter navigation no longer jumped to the top.
8. EPUB fixes:
   - Raw `<br>` broke Apple Books; all void tags are now self-closed.
   - MathML disappeared in WeChat Reading; formulas are converted to Unicode text before packaging.
   - A global marker replacement corrupted code spans; replacements are now scoped to headings.
   - Chapter subtitles are split into a separate line in web, PDF, and EPUB.
9. Mobile layout fixes: the primary action spans the row, secondary actions share the remaining space, and the duplicate home footer was removed.

## Phase 3: bilingual publishing

10. Sources moved to `markdown/`; `book.toml` gained `[editions.zh]` and `[editions.en]`.
11. The root landing page selects a language from storage or `navigator.language`; downloads live only there.
12. Reading sites link to each other for language switching and never expose downloads.
13. English typography:
    - Newsreader became the Latin face for web, PDF, and EPUB.
    - Titles allow `*emphasis*`; display HTML and plain text use separate helpers.
    - Currency must be written as `\$` so the EPUB math converter does not treat it as a formula.
14. The theme toggle was fixed: auto mode must keep `data-theme="auto"` for the dark-mode media query to work.
15. CJK web fonts moved to a Fontsource CDN with unicode-range chunks; the repository no longer stores CJK fonts.
16. The mixed-script stack puts Newsreader first so Latin letters and digits use it, with CJK falling back to Noto Serif SC.
17. The 700 web weight was restored after the CDN split made it affordable.

## Phase 4: sharing and AI-native reading

18. Social sharing:
    - Open Graph and Twitter metadata with absolute URLs.
    - 800x800 share cards per edition plus a bilingual landing card.
    - `rel="image_src"` and a hidden 300x300 image for WeChat's first-image scraper.
19. AI reading:
    - The landing page copies a book-level prompt that links to the published Markdown.
    - The build copies the manuscripts to `docs/<code>/dialectics.md`.
    - Every chapter page copies a chapter-specific prompt with the book title, chapter title, and absolute URL.
20. Feedback and layout:
    - The fixed bottom toast was covered by mobile browser toolbars; it became an inline status under the button.
    - Decorative glow pseudo-elements with negative lateral insets caused horizontal scrolling; lateral insets became zero and `overflow-x: clip` was added as a guard.

## Reusable conclusions

- Parse once, render three times. Separate format pipelines drift.
- Stable structural slugs beat title-derived slugs.
- Prefer named PDF destinations; use text search only as a fallback with a cursor.
- Static font instances are mandatory for Chromium PDF.
- EPUB readers are less capable than browsers: assume no MathML and strict XHTML.
- Keep generated output and hand-written assets in the same directory but never let cleanup delete assets.
- Validate on a narrow viewport, in a real PDF reader, and in at least two EPUB readers.
