# Print and EPUB

## PDF pipeline

1. Build a print-only HTML document: cover, colophon, TOC, parts, chapters.
2. Concatenate `base.css` plus `print.css` into a `<style>` block. Replace font URLs with absolute `file://` paths.
3. Print with headless Chromium:

```bash
chrome --headless --disable-gpu --no-pdf-header-footer \
  --allow-file-access-from-files --run-all-compositor-stages-before-draw \
  --virtual-time-budget=15000 --user-data-dir=<temp> \
  --print-to-pdf=<out.pdf> <file:///.../print.html>
```

Add `--no-sandbox --disable-dev-shm-usage` on Linux.

4. Post-process with `pypdf` to add bookmarks and metadata.

## Print CSS

Use named pages:

```css
@page { size: A4; margin: 22mm 21mm 24mm; }
@page cover { margin: 0; background: #f0e7d8; }
@page front { /* no header/footer */ }
@page part  { /* no header/footer */ }
```

- Default page: running header (book title / subtitle) and centered page number.
- Cover page: no margins, no header/footer.
- Front matter and part pages: no header/footer.
- Body: 10.5pt, 1.9 line-height, justified for CJK, left-aligned for English.
- Indent paragraphs 2em; remove indent inside lists, quotes, table cells, math.
- Avoid page breaks after headings: `break-after: avoid`.
- Keep table headers repeating: `thead { display: table-header-group; }`.
- Printed TOC has no page numbers; navigation lives in PDF bookmarks and the web sidebar.

## Cover without a blank page

Symptoms: a blank second page, or the cover frame overflowing.

Fix:

- Give the cover section a fixed height slightly below the page: `height: 296mm` for A4.
- Position the frame with `position: absolute; inset: 13mm;`, not `height: 100%` plus margins.
- Put `break-before: page` on the next section (colophon), not on both cover and colophon.
- Set `background: transparent` on `html, body`; let `@page` paint the page.
- Ensure `print-color-adjust: exact`.

## PDF bookmarks

Chromium does not generate an outline. Add it after printing:

1. Give every part/chapter/section heading a stable `id`.
2. Build outline entries: `(slug, label, parent_slug_or_none)`.
3. Read named destinations from the PDF; Chromium writes them for linked anchors.
4. For missing entries, search page text from a cursor, requiring the running header to avoid matching the printed TOC or preface guide.
5. Advance the cursor after each found entry.
6. Write with `pypdf.PdfWriter.add_outline_item`, set `page_mode = "/UseOutlines"`, add `/Title` and `/Author`.
7. Target three levels: part, chapter, section.

Named destinations are cheap and reliable. Text search is the fallback; normalize whitespace and use NFKC so PDF extraction quirks do not break matching.

## EPUB pipeline

1. Preprocess the Markdown into a staging file.
2. Invoke pandoc:

```bash
pandoc staging.md \
  --from=markdown+smart+lists_without_preceding_blankline \
  --to=epub3 --toc --toc-depth=2 --split-level=1 \
  --metadata title="..." --metadata author="..." --metadata lang="..." \
  --metadata description="..." --metadata rights="..." --metadata date="YYYY-MM" \
  --metadata source="https://.../<code>/" \
  --css docs/assets/css/epub.css \
  --epub-cover-image build/cover-<code>.png \
  --epub-embed-font docs/assets/fonts/latin-400.woff2 \
  --output docs/<code>/book.epub staging.md
```

3. Generate the cover with Chromium (1200x1800 or 1600x2400), using the same typographic system as the PDF cover.
4. Validate the archive.

## EPUB preprocessing

- Self-close void tags: `<br>` becomes `<br />`.
- Do not emit raw MathML. Convert math to Unicode text with a small LaTeX-to-text converter. Skip code spans and escaped currency.
- Currency: in English prose, write `\$`. Math detection must use a negative lookbehind so `\$...$` is not treated as a formula.
- Scope string replacements to headings. A global replace of a tag or marker will corrupt code spans.
- Convert a trailing `（subtitle）` or `(subtitle)` on chapter headings into a `<p class="chapter-sub">` after the heading.
- Keep `[Deep Dive]`-style markers as badges only in headings, not in body code.
- Warn on unknown LaTeX commands instead of silently dropping them.

## EPUB validation

```bash
rm -rf /tmp/epub-check && mkdir -p /tmp/epub-check
unzip -q docs/<code>/book.epub -d /tmp/epub-check
find /tmp/epub-check \( -name '*.xhtml' -o -name '*.opf' -o -name '*.ncx' \) \
  | xargs -n1 xmllint --noout
grep -R "<math" /tmp/epub-check && echo "unexpected MathML"
grep -R "<br>" /tmp/epub-check && echo "unclosed br"
```

Open the EPUB in at least two readers (Apple Books and WeChat Reading if targeting Chinese readers). Readers cache imports; remove the old copy before retesting.
