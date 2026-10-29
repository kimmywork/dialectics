/* 双语落地页：切换语言并记住选择。 */
(function () {
  "use strict";

  var root = document.documentElement;
  var THEME_KEY = "dialectics.theme";
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
