# Failure Catalog

Each entry comes from a real publication history. Use it as a review checklist, not as a list of hypotheticals.

## 1. PDF is 24 MB and text is fuzzy

**Symptom:** PDF balloons; selecting text behaves like paths.
**Cause:** Chromium's PDF backend cannot embed variable fonts. It converts glyphs to Type3 paths.
**Fix:** Instantiate static weights (`wght=400/700`) with `fontTools.varLib.instancer`, then subset and embed the static instances. Keep the variable font out of the print CSS.

## 2. Blank page after the cover

**Symptom:** Cover is followed by an empty page.
**Cause:** `height: 100%` plus margins overflow the page box; two `break-before` rules stack.
**Fix:** Fixed cover height (296mm for A4), absolute `inset` frame, and a single `break-before: page` on the following section.

## 3. Apple Books rejects the EPUB

**Symptom:** "Tag mismatch" or the book fails to open.
**Cause:** Raw `<br>` in XHTML.
**Fix:** `re.sub(r"<br\s*/?>", "<br />", text, flags=re.I)` before pandoc; validate every `.xhtml` with `xmllint`.

## 4. Math disappears in WeChat Reading

**Symptom:** Formulas vanish; only surrounding text remains.
**Cause:** The reader ignores MathML.
**Fix:** Convert formulas to Unicode text before EPUB packaging. Keep a symbol table, sub/superscript maps, and a fraction wrapper. Skip code spans and `\$` currency.

## 5. Formula conversion eats prices

**Symptom:** `$5` becomes a formula or disappears.
**Cause:** Naive `\$...\$` regex.
**Fix:** Escape currency as `\$` in the manuscript; match only unescaped `$...$` with `(?<!\\)` on both ends.

## 6. Code spans corrupted by a global replace

**Symptom:** Documentation examples turn into HTML badges.
**Cause:** Replacing a marker across the whole document.
**Fix:** Anchor replacements to headings (`^#{2,6}\s+`) and keep body/code text untouched.

## 7. TOC and bookmarks show `*emphasis*`

**Symptom:** Asterisks leak into navigation or the PDF outline.
**Cause:** Using display HTML or raw Markdown in plain-text contexts.
**Fix:** `title_html()` for rendered headings; `title_text()` for TOC/nav/bookmarks/metadata.

## 8. New chapter gets a random slug

**Symptom:** URL changes when the title changes; links break.
**Cause:** Slug derived from the full title.
**Fix:** Derive from the structural label (`第 N 章`, `Chapter N`, `附录 A`) with a stable fallback (`ch<index>-x`).

## 9. Sidebar jumps to top on every chapter change

**Symptom:** The active item is off-screen after navigation.
**Cause:** A new page resets the scroll container.
**Fix:** Store `scrollTop` in `sessionStorage` keyed by edition; restore on load.

## 10. "Auto" theme never follows the system

**Symptom:** Dark mode only works after manual selection.
**Cause:** The script deletes `data-theme` for auto, but the media query targets `html[data-theme="auto"]`.
**Fix:** Keep `data-theme="auto"`; listen for `prefers-color-scheme` changes and reapply.

## 11. Horizontal scrollbar on mobile

**Symptom:** The page pans sideways; `scrollWidth > clientWidth`.
**Cause:** Decorative pseudo-elements with negative left/right insets; wide grids without `minmax(0, 1fr)`.
**Fix:** Use `inset: -Yrem 0 auto` for glows; set `html, body { overflow-x: clip; }`; wrap tables.

## 12. Copy confirmation is hidden on mobile

**Symptom:** The toast is behind the browser toolbar.
**Cause:** `position: fixed; bottom: ...` anchors to the layout viewport.
**Fix:** Put an inline status element under the button in normal flow; do not use a fixed toast for critical feedback.

## 13. CJK fonts bloat the repository

**Symptom:** Tens of MB of font files; slow clone.
**Cause:** Committing full CJK fonts.
**Fix:** Load CJK from a CDN with unicode-range chunks; generate PDF subsets into an ignored build directory.

## 14. Stale CSS after a rebuild

**Symptom:** Old styles persist.
**Cause:** Browser cache.
**Fix:** Append `?v=<asset mtime>` to CSS/JS URLs.

## 15. Part pages look cramped

**Symptom:** Chapter list touches the title when a part has no intro.
**Cause:** Empty intro renders nothing.
**Fix:** Render a min-height spacer (`.part-intro-empty`) on web and print.

## 16. PDF bookmarks point to the wrong page

**Symptom:** Outline entries land on the TOC or preface.
**Cause:** Text search matches the printed TOC first.
**Fix:** Prefer named destinations; for fallback search, require the running header and advance a cursor.

## 17. Share card is stale in WeChat

**Symptom:** Old title/image in chat previews.
**Cause:** Aggressive caching.
**Fix:** Absolute OG URLs; version the image path when the card changes; re-share with a fresh query string.

## 18. Download links appear on reading pages

**Symptom:** A Chinese reader can download the English PDF.
**Cause:** Shared layout includes download buttons.
**Fix:** Downloads only on the landing page; reading pages expose language switching only.

## 19. Local paths leak into the published site

**Symptom:** `/Users/...` or a username appears in `docs/`.
**Cause:** Absolute file paths in generated HTML or metadata.
**Fix:** Use `file://` only inside the temporary print CSS; run `git grep -n "/Users/\|username" docs` before committing.

## 20. Build succeeds but content is missing

**Symptom:** A chapter is absent from one format.
**Cause:** The web, PDF, and EPUB pipelines parse the source separately or use different filters.
**Fix:** Parse once into a shared model; render each format from the same chapters. Verify counts (parts, chapters, bookmarks).
