const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const DOCS = path.join(ROOT, "docs");
const EDITIONS = ["zh", "en"];

function docsFile(...parts) {
  return path.join(DOCS, ...parts);
}

function readDocs(...parts) {
  return fs.readFileSync(docsFile(...parts), "utf8");
}

test.describe("build artifacts", () => {
  test("required entry points and editions exist", () => {
    for (const file of ["index.html", ".nojekyll", "CNAME"]) {
      expect(fs.existsSync(docsFile(file)), `${file} missing`).toBe(true);
    }

    for (const code of EDITIONS) {
      for (const file of ["index.html", "dialectics.md", "dialectics.pdf", "dialectics.epub"]) {
        const full = docsFile(code, file);
        expect(fs.existsSync(full), `${code}/${file} missing`).toBe(true);
        const minimum = file.endsWith(".html") ? 1_000 : 100_000;
        expect(fs.statSync(full).size, `${code}/${file} is suspiciously small`).toBeGreaterThan(minimum);
      }

      const pages = fs.readdirSync(docsFile(code)).filter((file) => file.endsWith(".html"));
      expect(pages.length, `${code} should contain many chapter pages`).toBeGreaterThanOrEqual(20);
    }
  });

  test("landing points to both editions and their downloads", () => {
    const landing = readDocs("index.html");
    expect(landing).toContain('data-lang-block="zh"');
    expect(landing).toContain('data-lang-block="en"');
    expect(landing).toContain("zh/dialectics.pdf");
    expect(landing).toContain("zh/dialectics.epub");
    expect(landing).toContain("en/dialectics.pdf");
    expect(landing).toContain("en/dialectics.epub");
    expect(landing).not.toContain("/Users/");
  });

  test("landing is the only place with download links", () => {
    for (const code of EDITIONS) {
      const pages = fs.readdirSync(docsFile(code)).filter((file) => file.endsWith(".html"));
      for (const page of pages) {
        const html = readDocs(code, page);
        expect(html, `${code}/${page} must not link downloads`).not.toMatch(/href="[^"]*\.(pdf|epub)"/);
      }
    }
  });

  test("chapter pages carry localized structured prompts", () => {
    const expectations = {
      zh: { phrase: "使用结构化的分析方法", prefix: "https://dialectics.kimleo.net/zh/" },
      en: { phrase: "Use a structured analytical approach", prefix: "https://dialectics.kimleo.net/en/" },
    };

    for (const code of EDITIONS) {
      const pages = fs.readdirSync(docsFile(code)).filter((file) => file.endsWith(".html"));
      let count = 0;
      for (const page of pages) {
        const html = readDocs(code, page);
        if (!html.includes('class="ai-read chapter-ai"')) continue;
        count += 1;
        const prompt = html.match(/data-prompt="([^"]*)"/)?.[1] || "";
        expect(prompt, `${code}/${page} prompt`).toContain(expectations[code].phrase);
        expect(prompt, `${code}/${page} URL`).toContain(expectations[code].prefix);
        expect(prompt, `${code}/${page} old method wording`).not.toMatch(
          /辩证阅读法|Four-Step Dialectical Book-Dissection Method/,
        );
      }
      expect(count, `${code} should have many chapter prompts`).toBeGreaterThan(20);
    }
  });

  test("every internal page, asset and download resolves", async ({ request }) => {
    const queue = ["/index.html", "/zh/index.html", "/en/index.html"];
    const seen = new Set();
    const htmlPages = [];

    while (queue.length) {
      const url = queue.shift();
      if (seen.has(url)) continue;
      seen.add(url);

      const head = await request.head(url);
      expect(head.status(), `HEAD ${url}`).toBe(200);
      const type = head.headers()["content-type"] || "";
      if (!type.includes("text/html")) continue;

      htmlPages.push(url);
      const response = await request.get(url);
      expect(response.status(), `GET ${url}`).toBe(200);
      const html = await response.text();

      for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
        const raw = match[1];
        if (/^(?:[a-z]+:|#)/i.test(raw)) continue;
        const resolved = new URL(raw, `http://example.test${url}`);
        if (resolved.origin !== "http://example.test") continue;
        const target = resolved.pathname;
        if (!/\.(?:html|css|js|md|pdf|epub|png|woff2)$/.test(target)) continue;
        if (!seen.has(target)) queue.push(target);
      }
    }

    expect(htmlPages.length, "crawler should visit many HTML pages").toBeGreaterThan(50);
    expect(seen.size, "crawler should visit HTML and assets").toBeGreaterThan(70);
  });

  test("CSS font and image URLs resolve", async ({ request }) => {
    for (const file of ["base.css", "web.css", "landing.css", "epub.css"]) {
      const css = readDocs("assets", "css", file);
      for (const match of css.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
        const raw = match[1];
        if (/^(?:data:|https?:|#)/i.test(raw)) continue;
        const target = new URL(raw, `http://example.test/assets/css/${file}`).pathname;
        const response = await request.head(target);
        expect(response.status(), `${file} references missing ${target}`).toBe(200);
      }
    }
  });

  test("generated pages contain no local paths or usernames", () => {
    const offenders = [];
    for (const entry of fs.readdirSync(DOCS, { recursive: true })) {
      const full = path.join(DOCS, entry);
      if (!fs.statSync(full).isFile()) continue;
      if (!/\.(?:html|css|js|md|json|xml|txt)$/.test(entry)) continue;
      const text = fs.readFileSync(full, "utf8");
      if (text.includes("/Users/") || text.includes("qliu23")) offenders.push(entry);
    }
    expect(offenders).toEqual([]);
  });

  test("markdown copies match a manuscript source", () => {
    const sources = fs
      .readdirSync(path.join(ROOT, "markdown"))
      .filter((file) => file.endsWith(".md"))
      .map((file) => fs.readFileSync(path.join(ROOT, "markdown", file)));

    for (const code of EDITIONS) {
      const copy = fs.readFileSync(docsFile(code, "dialectics.md"));
      expect(
        sources.some((source) => source.equals(copy)),
        `${code}/dialectics.md is out of date`,
      ).toBe(true);
    }
  });
});
