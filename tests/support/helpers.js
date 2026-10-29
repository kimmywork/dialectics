const { expect } = require("@playwright/test");

async function gotoAndSettle(page, url) {
  await page.goto(url, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  // Give the inline boot scripts and the first rAF a chance to run.
  await page.waitForTimeout(50);
}

async function expectNoHorizontalOverflow(page) {
  const dims = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(
    dims.scrollWidth,
    `horizontal overflow: scrollWidth=${dims.scrollWidth} > clientWidth=${dims.clientWidth}`,
  ).toBeLessThanOrEqual(dims.clientWidth);
}

async function bodyBackground(page) {
  return page.evaluate(() => getComputedStyle(document.body).backgroundColor);
}

function brightness(color) {
  const match = String(color).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) return null;
  const [r, g, b] = match.slice(1, 4).map(Number);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

module.exports = {
  gotoAndSettle,
  expectNoHorizontalOverflow,
  bodyBackground,
  brightness,
};
