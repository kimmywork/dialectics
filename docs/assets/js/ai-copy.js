/* 「AI 帮我读」：复制提示词并提示结果。落地页与章节页共用。 */
(function () {
  "use strict";

  function showStatus(btn, text) {
    var box = btn.closest(".ai-read") || btn.parentElement;
    var status = box && box.querySelector(".ai-status");
    if (!status) return;
    status.textContent = text;
    status.hidden = false;
    if (status._timer) clearTimeout(status._timer);
    status._timer = setTimeout(function () {
      status.hidden = true;
      status.textContent = "";
    }, 2800);
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
        showStatus(btn, btn.dataset.toast || "Copied.");
      }).catch(function () {
        showStatus(btn, btn.dataset.fail || "Copy failed.");
      });
    });
  });
})();
