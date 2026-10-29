const { test, expect } = require("@playwright/test");
const {
  gotoAndSettle,
  expectNoHorizontalOverflow,
  bodyBackground,
  brightness,
} = require("./support/helpers");

test.describe("language selection", () => {
  test("browser locale chooses the matching edition", async ({ browser }) => {
    for (const [locale, active, inactive] of [
      ["zh-CN", "zh", "en"],
      ["en-US", "en", "zh"],
    ]) {
      const context = await browser.newContext({ locale, viewport: { width: 1280, height: 900 } });
      const page = await context.newPage();
      await gotoAndSettle(page, "/");

      await expect(page.locator("html")).toHaveAttribute("data-lang", active);
      await expect(page.locator(`[data-lang-block="${active}"]`)).toBeVisible();
      await expect(page.locator(`[data-lang-block="${inactive}"]`)).toBeHidden();

      await context.close();
    }
  });

  test("manual switch persists across reloads", async ({ page }) => {
    await gotoAndSettle(page, "/");
    await page.locator('[data-set-lang="en"]').click();

    await expect(page.locator("html")).toHaveAttribute("data-lang", "en");
    await expect(page.locator('[data-set-lang="en"]')).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator('[data-lang-block="en"]')).toBeVisible();

    await page.reload({ waitUntil: "load" });
    await expect(page.locator("html")).toHaveAttribute("data-lang", "en");
    await expect(page.locator('[data-lang-block="en"]')).toBeVisible();
    await expect(page.locator('[data-lang-block="zh"]')).toBeHidden();
  });
});

test.describe("downloads", () => {
  test("landing exposes both formats for the active edition", async ({ page, request }) => {
    await gotoAndSettle(page, "/");

    for (const code of ["zh", "en"]) {
      await page.locator(`[data-set-lang="${code}"]`).click();
      const block = page.locator(`[data-lang-block="${code}"]`);
      const pdf = block.locator('a[href$=".pdf"]');
      const epub = block.locator('a[href$=".epub"]');

      await expect(pdf).toHaveAttribute("href", `${code}/dialectics.pdf`);
      await expect(epub).toHaveAttribute("href", `${code}/dialectics.epub`);

      const pdfHead = await request.head(`/${code}/dialectics.pdf`);
      expect(pdfHead.status()).toBe(200);
      expect(pdfHead.headers()["content-type"]).toContain("pdf");
      expect(Number(pdfHead.headers()["content-length"])).toBeGreaterThan(100_000);

      const epubHead = await request.head(`/${code}/dialectics.epub`);
      expect(epubHead.status()).toBe(200);
      expect(Number(epubHead.headers()["content-length"])).toBeGreaterThan(100_000);
    }
  });

  test("reading pages never expose downloads", async ({ page }) => {
    for (const path of ["/zh/ch01.html", "/en/ch01.html", "/zh/part-1.html"]) {
      await gotoAndSettle(page, path);
      await expect(page.locator('a[href$=".pdf"], a[href$=".epub"]')).toHaveCount(0);
    }
  });
});

test.describe("theme", () => {
  test("manual toggle changes colors and persists", async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: "light", locale: "zh-CN" });
    const page = await context.newPage();
    await gotoAndSettle(page, "/");

    await expect(page.locator("html")).toHaveAttribute("data-theme", "auto");
    const light = await bodyBackground(page);

    await page.locator("[data-theme-toggle]").click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    const dark = await bodyBackground(page);
    expect(brightness(dark)).toBeLessThan(brightness(light));

    await page.reload({ waitUntil: "load" });
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    await context.close();
  });

  test("auto follows the system preference", async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: "dark", locale: "zh-CN" });
    const page = await context.newPage();
    await gotoAndSettle(page, "/");

    await expect(page.locator("html")).toHaveAttribute("data-theme", "auto");
    expect(brightness(await bodyBackground(page))).toBeLessThan(80);

    await context.close();
  });
});

test.describe("AI prompts", () => {
  test.use({ permissions: ["clipboard-read", "clipboard-write"] });

  test("book prompt copies, asks for structured analysis, and auto-hides status", async ({ page }) => {
    await gotoAndSettle(page, "/");
    const block = page.locator('[data-lang-block="zh"]');
    const button = block.locator("[data-ai-copy]");
    const prompt = await button.getAttribute("data-prompt");

    expect(prompt).toContain("https://dialectics.kimleo.net/zh/dialectics.md");
    expect(prompt).toContain("使用结构化的分析方法");
    expect(prompt).not.toContain("附录 C");
    await expect(block.locator(".ai-hint a")).toHaveCount(0);

    await button.click();
    const status = block.locator(".ai-status");
    await expect(status).toBeVisible();
    await expect(status).toHaveText(/提示词已复制/);

    await page.bringToFront();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(prompt);
    await expect(status).toBeHidden({ timeout: 5_000 });
  });

  test("English prompt ignores the old reading-method wording", async ({ browser }) => {
    const context = await browser.newContext({
      locale: "en-US",
      permissions: ["clipboard-read", "clipboard-write"],
      viewport: { width: 1280, height: 900 },
    });
    const page = await context.newPage();
    await gotoAndSettle(page, "/");

    const block = page.locator('[data-lang-block="en"]');
    const button = block.locator("[data-ai-copy]");
    const prompt = await button.getAttribute("data-prompt");
    expect(prompt).toContain("https://dialectics.kimleo.net/en/dialectics.md");
    expect(prompt).toContain("Use a structured analytical approach");
    expect(prompt).not.toContain("Appendix C");
    await expect(block.locator(".ai-hint a")).toHaveCount(0);

    await button.click();
    await expect(block.locator(".ai-status")).toHaveText(/Prompt copied/);
    await page.bringToFront();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(prompt);

    const ogImage = await page.locator('meta[property="og:image"]').getAttribute("content");
    expect(ogImage).toBe("https://dialectics.kimleo.net/assets/share/index.png");
    expect((await context.request.get(ogImage)).status()).toBe(200);

    await context.close();
  });
});

test("landing has no horizontal overflow at any breakpoint", async ({ page }) => {
  for (const width of [375, 500, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await gotoAndSettle(page, "/");
    await expectNoHorizontalOverflow(page);
  }
});
