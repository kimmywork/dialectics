# Automated Verification

Use a browser suite for the reading experience and a small artifact verifier for the formats a browser cannot inspect.

## Stack

- `@playwright/test` drives Chromium against `docs/` served by `python3 -m http.server`.
- `playwright.config.js` owns the port (`8795`), base URL, web server, viewport, traces, HTML report, and screenshot path template.
- `scripts/verify_artifacts.py` checks PDF outline/page counts, EPUB archive/XML rules, Markdown copies, and privacy.
- `make verify` builds the web edition, runs the artifact verifier, then Playwright. `make verify-full` does a full HTML/PDF/EPUB build first.

## Spec layout

| Spec | Responsibility |
| --- | --- |
| `tests/build.spec.js` | Required files, page counts, internal link/asset crawler, download isolation, Markdown copies, local-path privacy |
| `tests/landing.spec.js` | Locale detection and persistence, manual switch, downloads, theme auto/manual, AI prompt copy, horizontal overflow |
| `tests/reading.spec.js` | Catalog/pager/keyboard navigation, language switch, resume, sidebar scroll, progress, drawer, chapter AI, math/table/subtitle |
| `tests/visual.spec.js` | Desktop/mobile and light/dark screenshot baselines |
| `tests/support/helpers.js` | `gotoAndSettle`, overflow assertion, background brightness |

## Browser test rules

- One project: Chromium desktop. Create a context when a test needs another locale, color scheme, permissions, or viewport. Do not multiply the whole suite by device projects.
- Wait for `document.fonts.ready` before layout or screenshot assertions. CDN CJK fonts are part of the design.
- Use `expect.poll` or locator assertions instead of fixed sleeps. A 50ms settle after load is enough for inline boot scripts.
- Test persistence by reloading the same context. Test system preference with a fresh context and `colorScheme`.
- Grant `clipboard-read` and `clipboard-write` on the context for AI-copy tests; read back the clipboard to prove the actual copy, not just the status text.
- For downloads, assert the landing href plus HTTP status/content type/length. Do not assume Chromium fires a download event for PDFs.
- For overflow, compare `document.documentElement.scrollWidth` with `clientWidth` at 375, 500, 768, and 1280.
- For animation, assert the computed transition is present and exercise the state change (drawer class, scrim visibility, progress width). Do not assert exact frame timing.
- Keep visual screenshots viewport-sized, mask the footer (it contains a year), and disable animations. Review baseline changes before committing.
- Use a fresh context per test so `localStorage` and `sessionStorage` do not leak between cases.

## Artifact verifier

`scripts/verify_artifacts.py` should fail loudly when:

- a PDF is under 1 MB, has fewer than 50 pages, fewer than 100 outline entries, no title metadata, or does not open the outline panel;
- an EPUB is under 100 KB, lacks a first-entry `mimetype`, has no cover, has no embedded fonts, contains invalid XML, still contains `<math`, contains an unclosed `<br>`, has too few chapter XHTML files, or its TOC is shallower than three levels;
- `docs/<code>/dialectics.md` differs from the manuscript;
- `docs/` contains `/Users/` or a username.

Keep it dependency-light: `pypdf`, `zipfile`, and `xml.etree.ElementTree`.

## Commands

```bash
make test-setup    # npm install + playwright install chromium

make verify        # web build + artifact checks + Playwright
make verify-full   # full HTML/PDF/EPUB build + checks
npm run test:ui    # interactive debugging
npm run test:update # refresh visual baselines; inspect the diff
```

Do not commit `node_modules/`, `test-results/`, `playwright-report/`, or `blob-report/`. Commit `tests/__screenshots__/`.

## Adding coverage

1. Add an interaction spec that exercises the user-visible state change, not an internal function.
2. Add a build assertion if the change introduces an artifact, URL, or link class.
3. Add or update a visual baseline only when the visual change is intentional.
4. Run `make verify` twice to catch order-dependent state.
5. If a test finds a real bug, fix the source and keep the regression test.

## Evidence from the first run

The first Playwright run found that the landing page theme button had no click handler: the theme logic had been removed when the AI-copy script was extracted, leaving an unused `THEME_KEY`. The suite caught it because it asserted the `data-theme` change, not just that the button existed. Keep tests at the level of observable behavior.
