/* 双语落地页：切换语言并记住选择。 */
(function () {
  "use strict";

  var root = document.documentElement;
  var THEME_KEY = "dialectics.theme";
  var toastTimer = null;

  function showToast(text) {
    var toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = text;
    toast.hidden = false;
    requestAnimationFrame(function () { toast.classList.add("is-visible"); });
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove("is-visible");
      setTimeout(function () { toast.hidden = true; }, 220);
    }, 2600);
  }

  function legacyCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(area);
    return ok ? Promise.resolve() : Promise.reject(new Error("copy failed"));
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () {
        return legacyCopy(text);
      });
    }
    return legacyCopy(text);
  }

  document.querySelectorAll("[data-ai-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      copyText(btn.dataset.prompt || "").then(function () {
        showToast(btn.dataset.toast || "Copied.");
      }).catch(function () {
        showToast(btn.dataset.fail || "Copy failed.");
      });
    });
  });

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
