/* 双语落地页：切换语言并记住选择。 */
(function () {
  "use strict";

  var root = document.documentElement;
  var THEME_KEY = "dialectics.theme";

  function effectiveTheme() {
    var attr = root.dataset.theme;
    if (attr === "dark" || attr === "light") return attr;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark" : "light";
  }

  function applyTheme(theme, persist) {
    root.dataset.theme = theme;
    if (persist) {
      try {
        if (theme === "auto") localStorage.removeItem(THEME_KEY);
        else localStorage.setItem(THEME_KEY, theme);
      } catch (e) { /* ignore */ }
    }
  }

  applyTheme(root.dataset.theme || "auto", false);

  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      applyTheme(effectiveTheme() === "dark" ? "light" : "dark", true);
    });
  });

  function apply(lang, persist) {
    root.dataset.lang = lang;
    root.lang = lang === "zh" ? "zh-CN" : "en";
    document.querySelectorAll("[data-set-lang]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", String(btn.dataset.setLang === lang));
    });
    if (persist) {
      try { localStorage.setItem("dialectics.lang", lang); } catch (e) { /* ignore */ }
    }
  }

  apply(root.dataset.lang || "zh", false);

  document.querySelectorAll("[data-set-lang]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      apply(btn.dataset.setLang, true);
    });
  });
})();
