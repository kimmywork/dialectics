/* 阅读器交互：主题、抽屉目录、阅读进度、续读、键盘翻页。无第三方依赖。 */
(function () {
  "use strict";

  var root = document.documentElement;
  var THEME_KEY = "dialectics.theme";
  var RESUME_KEY = "dialectics.resume";

  function store(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* 隐私模式下忽略 */ }
  }
  function read(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  /* ---------------- 主题 ---------------- */

  var themeButtons = document.querySelectorAll("[data-theme-toggle]");
  var media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function effectiveTheme() {
    var attr = root.dataset.theme;
    if (attr === "light" || attr === "dark") return attr;
    return media && media.matches ? "dark" : "light";
  }

  function applyTheme(theme, persist) {
    if (theme === "auto") {
      delete root.dataset.theme;
      if (persist) { try { localStorage.removeItem(THEME_KEY); } catch (e) {} }
    } else {
      root.dataset.theme = theme;
      if (persist) store(THEME_KEY, theme);
    }
    themeButtons.forEach(function (btn) {
      btn.setAttribute("title", "切换深色 / 浅色（当前：" + (theme === "dark" ? "深色" : theme === "light" ? "浅色" : "跟随系统") + "）");
    });
  }

  themeButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      applyTheme(effectiveTheme() === "dark" ? "light" : "dark", true);
    });
  });

  if (media && media.addEventListener) {
    media.addEventListener("change", function () {
      if (!root.dataset.theme) applyTheme("auto", false);
    });
  }
  applyTheme(root.dataset.theme || "auto", false);

  /* ---------------- 抽屉目录 ---------------- */

  var sidebar = document.getElementById("sidebar");
  var scrim = document.getElementById("scrim");
  var menuBtn = document.getElementById("menu-toggle");

  function setMenu(open) {
    if (!sidebar || !scrim || !menuBtn) return;
    sidebar.classList.toggle("is-open", open);
    document.body.classList.toggle("menu-open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    menuBtn.setAttribute("aria-label", open ? "关闭目录" : "打开目录");
    if (open) {
      scrim.hidden = false;
      requestAnimationFrame(function () { scrim.classList.add("is-visible"); });
    } else {
      scrim.classList.remove("is-visible");
      window.setTimeout(function () { scrim.hidden = true; }, 260);
    }
  }

  if (menuBtn) {
    menuBtn.addEventListener("click", function () {
      setMenu(!sidebar.classList.contains("is-open"));
    });
  }
  if (scrim) scrim.addEventListener("click", function () { setMenu(false); });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") setMenu(false);
  });

  if (sidebar) {
    sidebar.addEventListener("click", function (event) {
      if (event.target.closest("a")) setMenu(false);
    });
  }

  if (media) {
    window.addEventListener("resize", function () {
      if (window.innerWidth > 900) setMenu(false);
    });
  }

  /* ---------------- 阅读进度 ---------------- */

  var bar = document.getElementById("progress-bar");
  if (bar) {
    var ticking = false;
    var update = function () {
      var doc = document.documentElement;
      var total = doc.scrollHeight - window.innerHeight;
      var ratio = total > 0 ? Math.min(1, Math.max(0, window.scrollY / total)) : 0;
      bar.style.width = (ratio * 100).toFixed(2) + "%";
      ticking = false;
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  /* ---------------- 续读 ---------------- */

  var chapterTitle = document.querySelector(".chapter-head h1");
  if (chapterTitle) {
    var href = location.pathname.split("/").pop() || "index.html";
    store(RESUME_KEY, JSON.stringify({ href: href, title: chapterTitle.textContent.trim() }));
  }

  var resume = document.getElementById("resume");
  if (resume) {
    var saved = read(RESUME_KEY);
    if (saved) {
      try {
        var data = JSON.parse(saved);
        if (data && data.href) {
          resume.href = data.href;
          document.getElementById("resume-title").textContent = data.title || "";
          resume.hidden = false;
        }
      } catch (e) { /* 忽略损坏的记录 */ }
    }
  }

  /* ---------------- 键盘翻页 ---------------- */

  document.addEventListener("keydown", function (event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    var tag = (event.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select" || event.target.isContentEditable) return;
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    var link = document.querySelector(event.key === "ArrowLeft" ? ".pager-prev" : ".pager-next");
    if (link && link.href) location.href = link.href;
  });
})();
