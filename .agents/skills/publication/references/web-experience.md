# Web Experience

## Landing page

- Render one `<section data-lang-block="<code>">` per edition.
- Set `html[data-lang]` in an inline `<head>` script before paint. Resolution order: saved choice, then `navigator.language`, then configured default.
- Toggle visibility with CSS, not by rebuilding the page:
  `html[data-lang="zh"] [data-lang-block="zh"] { display: block; }`
- Manual buttons update `data-lang`, `lang`, `aria-pressed`, and `localStorage`.
- Downloads (PDF/EPUB) appear only here.
- Include `hreflang` alternates and `rel="alternate" type="text/markdown"` links.
- Include OG/Twitter tags with absolute URL and an 800x800 image.

## Reading shell

Desktop: CSS grid `sidebar minmax(0, 1fr)`; sticky sidebar with its own scroll area.
Mobile (<=900px): sidebar becomes a fixed drawer; add a topbar menu button and a scrim.

Required behaviors:

- Drawer opens/closes with button, scrim click, Escape; close on link click and on resize past the breakpoint.
- Progress bar: fixed 2px at top; update from `scrollY / (scrollHeight - innerHeight)` via `requestAnimationFrame`.
- Resume: on chapter pages store `{href, title}`; on home show a link to the last chapter. Key per edition: `app.nav.<code>`, `app.resume.<code>`.
- Sidebar scroll: store and restore `scrollTop` in `sessionStorage` per edition so changing chapters does not jump to top.
- Keyboard: Left/Right arrows follow pager links unless focus is in an input/textarea/select/contenteditable.
- Skip link to `#main`; `aria-current="page"` on the active nav item.

## Theme

- `html[data-theme="auto|light|dark"]`; default `auto`.
- Inline head script applies a saved theme before paint.
- Keep `data-theme="auto"`; do not delete the attribute. The dark-mode media query targets `html[data-theme="auto"]`.
- Toggle computes the effective theme from the attribute or `prefers-color-scheme`, then stores `light`/`dark`.
- Listen for `prefers-color-scheme` changes while in auto mode.
- Use CSS custom properties for all colors so both themes and print share tokens.

## AI-native reading buttons

Expose the Markdown source at `/<code>/dialectics.md` and link it with `rel="alternate" type="text/markdown"`.

Book-level button on the landing page:

```text
Help me interpret [<book title>](<absolute markdown URL>), using <named method> from Appendix C or another structured approach.
```

Chapter-level button below the chapter title, above the prose:

```text
Help me interpret this chapter from "<book title>":
"<chapter title>"
<absolute chapter URL>
```

Implementation:

- `button[data-ai-copy][data-prompt][data-toast][data-fail]`.
- Copy with `navigator.clipboard.writeText` when available and secure; fall back to a temporary textarea plus `execCommand("copy")`.
- Show feedback in an inline `<span class="ai-status" role="status" aria-live="polite" hidden>` inside the same `.ai-read` container. Never use a fixed bottom toast: mobile browser toolbars cover it.
- Clear the feedback after about 2.8 seconds.
- Keep prompts localized; use the absolute production URL, not `location.href` alone.

## Share cards

- Generate 800x800 PNGs per edition plus one bilingual landing card.
- Add `og:type`, `og:site_name`, `og:title`, `og:description`, `og:url`, `og:image` (plus type/width/height), `og:locale`, `og:locale:alternate`, Twitter equivalents, and `rel="image_src"`.
- Add a hidden 300x300 `<img class="share-thumb">`; some WeChat scrapers pick the first image.
- Use absolute image URLs.
- WeChat caches cards aggressively; to refresh, change the image URL or query string.

## Fonts

- Latin: self-host a small subset and preload 400.
- CJK: CDN with `unicode-range` chunks; load 400 and optionally 700. Avoid committing CJK files.
- Stack: `"Latin", "CJK", ..., serif` for both languages so digits and Latin use the Latin face.
- Keep `font-display: swap` for web.

## CSS architecture

- `base.css`: tokens, resets, prose typography shared by web and print.
- `web.css`: reading layout, sidebar, topbar, pager, buttons, AI status.
- `landing.css`: landing-only layout.
- `print.css`: `@page`, cover, colophon, TOC, print typography.
- `epub.css`: reader-friendly styles, no page assumptions.
- Use `color-mix()` for tints; keep a light/dark token pair.
- Set `html, body { overflow-x: clip; }` as a guard. Prefer `clip` over `hidden` so sticky positioning keeps working.
- Never give a decorative pseudo-element negative left/right insets; use `inset: -Yrem 0 auto` and keep the glow inside the viewport.
- Wrap wide tables in `.table-wrap { overflow-x: auto; }`.
- Keep `max-width` on prose (about 40rem) and `minmax(0, 1fr)` on grid columns.

## Mobile checks

- 500px viewport: `document.documentElement.scrollWidth === clientWidth`.
- Primary action full-width; secondary actions share a row or stack.
- Tap targets at least 40px.
- Drawer and scrim work without horizontal scroll.
- Feedback stays visible while the soft keyboard or toolbar is open.
