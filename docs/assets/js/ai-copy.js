/* 「AI 帮我读」：复制提示词并提示结果。落地页与章节页共用。 */
(function () {
  "use strict";

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
})();
