const { test, expect } = require("./support/fixtures");
const { gotoAndSettle } = require("./support/helpers");

async function hideUnstableChrome(page) {
  // The footer contains a year; hide it without changing layout.
  await page.addStyleTag({
    content: ".landing-foot, .page-foot { visibility: hidden !important; }",
  });
}

test.describe("visual regression", () => {
  test("landing desktop, Chinese", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ colorScheme: "light" });
    await gotoAndSettle(page, "/");
    await expect(page.locator('[data-lang-block="zh"]')).toBeVisible();
    await hideUnstableChrome(page);
    await expect(page).toHaveScreenshot("landing-zh-desktop.png");
  });

  test("landing desktop, English", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ colorScheme: "light" });
    await gotoAndSettle(page, "/");
    await page.locator('[data-set-lang="en"]').click();
    await expect(page.locator('[data-lang-block="en"]')).toBeVisible();
    await hideUnstableChrome(page);
    await expect(page).toHaveScreenshot("landing-en-desktop.png");
  });

  test("landing mobile, Chinese", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ colorScheme: "light" });
    await gotoAndSettle(page, "/");
    await expect(page.locator('[data-lang-block="zh"]')).toBeVisible();
    await hideUnstableChrome(page);
    await expect(page).toHaveScreenshot("landing-zh-mobile.png");
  });

  test("chapter desktop, light", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ colorScheme: "light" });
    await gotoAndSettle(page, "/zh/ch01.html");
    await hideUnstableChrome(page);
    await expect(page).toHaveScreenshot("chapter-zh-desktop.png");
  });

  test("chapter desktop, dark", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ colorScheme: "dark" });
    await gotoAndSettle(page, "/zh/ch01.html");
    await hideUnstableChrome(page);
    await expect(page).toHaveScreenshot("chapter-zh-dark.png");
  });

  test("chapter mobile, light", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ colorScheme: "light" });
    await gotoAndSettle(page, "/zh/ch01.html");
    await hideUnstableChrome(page);
    await expect(page).toHaveScreenshot("chapter-zh-mobile.png");
  });
});
