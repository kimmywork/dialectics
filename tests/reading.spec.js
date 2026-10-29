const { test, expect } = require("@playwright/test");
const {
  gotoAndSettle,
  expectNoHorizontalOverflow,
  bodyBackground,
  brightness,
} = require("./support/helpers");

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

test.describe("reading home", () => {
  test("catalog opens a chapter and marks the sidebar item", async ({ page }) => {
    await gotoAndSettle(page, "/zh/index.html");
    await expect(page.locator(".hero-title")).toHaveText("走出二选一");

    const first = page.locator(".catalog-chapters a").first();
    const href = await first.getAttribute("href");
    await first.click();

    await expect(page).toHaveURL(new RegExp(`/zh/${escapeRegExp(href)}$`));
    await expect(page.locator(".chapter-head h1")).toBeVisible();
    await expect(page.locator('.nav-item[aria-current="page"]')).toHaveCount(1);
  });

  test("catalog button jumps to the catalog anchor", async ({ page }) => {
    await gotoAndSettle(page, "/zh/index.html");
    await page.locator('.hero-actions a[href="#catalog"]').click();
    await expect(page).toHaveURL(/#catalog$/);
    await expect(page.locator("#catalog")).toBeInViewport();
  });
});

test.describe("navigation", () => {
  test("pager moves forward and back", async ({ page }) => {
    await gotoAndSettle(page, "/zh/ch01.html");
    await page.locator(".pager-next").click();
    await expect(page).not.toHaveURL(/ch01\.html$/);

    await page.locator(".pager-prev").click();
    await expect(page).toHaveURL(/ch01\.html$/);
  });

  test("keyboard arrows follow pager links", async ({ page }) => {
    await gotoAndSettle(page, "/zh/ch01.html");
    await page.keyboard.press("ArrowRight");
    await expect(page).not.toHaveURL(/ch01\.html$/);
  });

  test("language switch goes to the other edition", async ({ page }) => {
    await gotoAndSettle(page, "/zh/index.html");
    await page.locator(".lang-link").click();
    await expect(page).toHaveURL(/\/en\/index\.html$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator(".hero-title")).toHaveText("Beyond Either/Or");
  });

  test("resume link returns to the last chapter", async ({ page }) => {
    await gotoAndSettle(page, "/zh/ch02.html");
    const title = (await page.locator(".chapter-head h1").innerText()).trim();

    await gotoAndSettle(page, "/zh/index.html");
    await expect(page.locator("#resume")).toBeVisible();
    await expect(page.locator("#resume")).toHaveAttribute("href", "ch02.html");
    await expect(page.locator("#resume-title")).toHaveText(title);
  });

  test("sidebar scroll position survives a page change", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 560 });
    await gotoAndSettle(page, "/zh/index.html");

    await page.evaluate(() => {
      const nav = document.querySelector(".sidebar-nav");
      nav.scrollTop = 260;
      nav.dispatchEvent(new Event("scroll"));
    });
    expect(await page.locator(".sidebar-nav").evaluate((el) => el.scrollTop)).toBe(260);

    await page.evaluate(() => document.querySelectorAll(".nav-item")[1].click());
    await expect(page).not.toHaveURL(/\/index\.html$/);
    await page.waitForLoadState("load");
    await expect(page.locator(".chapter-head h1, .part-title").first()).toBeVisible();
    expect(await page.locator(".sidebar-nav").evaluate((el) => el.scrollTop)).toBe(260);
  });
});

test.describe("reading theme", () => {
  test("manual toggle changes colors and persists", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await gotoAndSettle(page, "/zh/ch01.html");

    const light = await bodyBackground(page);
    await page.locator(".sidebar-foot [data-theme-toggle]").click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    expect(brightness(await bodyBackground(page))).toBeLessThan(brightness(light));

    await page.reload({ waitUntil: "load" });
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("auto follows the system preference", async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: "dark" });
    const page = await context.newPage();
    await gotoAndSettle(page, "/zh/ch01.html");

    await expect(page.locator("html")).toHaveAttribute("data-theme", "auto");
    expect(brightness(await bodyBackground(page))).toBeLessThan(80);

    await context.close();
  });
});

test.describe("progress and animation", () => {
  test("progress bar tracks scroll", async ({ page }) => {
    await gotoAndSettle(page, "/zh/ch01.html");
    expect(await page.locator("#progress-bar").evaluate((el) => parseFloat(el.style.width) || 0)).toBeLessThan(5);

    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await page.waitForFunction(
      () => parseFloat(document.querySelector("#progress-bar").style.width) > 80,
    );
  });

  test("drawer, progress and cards keep their transitions", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoAndSettle(page, "/zh/ch01.html");

    const drawerDuration = await page
      .locator("#sidebar")
      .evaluate((el) => getComputedStyle(el).transitionDuration);
    const progressDuration = await page
      .locator("#progress-bar")
      .evaluate((el) => getComputedStyle(el).transitionDuration);
    const cardTransition = await page
      .locator(".pager-card")
      .first()
      .evaluate((el) => getComputedStyle(el).transitionProperty);

    expect(drawerDuration).not.toBe("0s");
    expect(progressDuration).not.toBe("0s");
    expect(cardTransition).toContain("transform");
  });
});

test.describe("chapter presentation", () => {
  test("subtitle, star, math and tables render", async ({ page }) => {
    await gotoAndSettle(page, "/zh/ch01.html");
    await expect(page.locator(".chapter-sub")).toBeVisible();
    await expect(page.locator(".chapter-head .star")).toHaveCount(1);
    await expect(page.locator("math").first()).toBeVisible();
    await expect(page.locator(".table-wrap table")).toBeVisible();
  });

  test("chapter AI prompt includes book, chapter, URL and method", async ({ page }) => {
    await gotoAndSettle(page, "/zh/ch01.html");
    const button = page.locator(".chapter-ai [data-ai-copy]");
    const prompt = await button.getAttribute("data-prompt");

    expect(prompt).toContain("走出二选一：大众辩证思维手册");
    expect(prompt).toContain("第 1 章 张力的四种形态");
    expect(prompt).toContain("https://dialectics.kimleo.net/zh/ch01.html");
    expect(prompt).toContain("使用结构化的分析方法");

    await button.click();
    await expect(page.locator(".chapter-ai .ai-status")).toHaveText(/本章提示词已复制/);
  });

  test("part page lists its chapters", async ({ page }) => {
    await gotoAndSettle(page, "/zh/part-1.html");
    await expect(page.locator(".part-title")).toBeVisible();
    expect(await page.locator(".part-chapters a").count()).toBeGreaterThan(0);
  });
});

test.describe("mobile drawer and overflow", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("drawer opens, closes with scrim and Escape", async ({ page }) => {
    await gotoAndSettle(page, "/zh/ch01.html");
    await expect(page.locator(".topbar")).toBeVisible();

    const sidebar = page.locator("#sidebar");
    await expect(sidebar).not.toHaveClass(/is-open/);

    await page.locator("#menu-toggle").click();
    await expect(sidebar).toHaveClass(/is-open/);
    await expect(page.locator("#scrim")).toBeVisible();

    await page.locator("#scrim").click();
    await expect(sidebar).not.toHaveClass(/is-open/);
    await expect(page.locator("#scrim")).toBeHidden();

    await page.locator("#menu-toggle").click();
    await page.keyboard.press("Escape");
    await expect(sidebar).not.toHaveClass(/is-open/);
  });

  test("no horizontal overflow on mobile reading pages", async ({ page }) => {
    for (const path of ["/zh/index.html", "/zh/ch01.html", "/zh/part-1.html"]) {
      await gotoAndSettle(page, path);
      await expectNoHorizontalOverflow(page);
    }
  });
});
