const base = require("@playwright/test");

function isLocal(url) {
  const parsed = new URL(url);
  return parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost";
}

function routeLocalOnly(router) {
  return router.route("**/*", (route) => {
    // Keep regression runs hermetic: local pages must not wait on CDN fonts
    // or production share images. The site still uses them in real browsers.
    if (isLocal(route.request().url())) return route.continue();
    return route.abort();
  });
}

const test = base.test.extend({
  page: async ({ page }, use) => {
    await routeLocalOnly(page);
    await use(page);
  },
});

async function newContext(browser, options = {}) {
  const context = await browser.newContext(options);
  await routeLocalOnly(context);
  return context;
}

module.exports = { test, expect: base.expect, newContext };
