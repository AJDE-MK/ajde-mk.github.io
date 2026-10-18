/* Page behavior: column toggles, version tabs, Mark as learned.
   Every localStorage call is wrapped, so the page works with saving blocked. */
(function () {
  "use strict";

  var COL_KEY = "mk_columns";
  var memory = {};

  function readCols() {
    try {
      var raw = window.localStorage.getItem(COL_KEY);
      if (raw) { return JSON.parse(raw); }
    } catch (e) { /* storage blocked: use in-memory choices */ }
    return memory;
  }

  function writeCols(cols) {
    memory = cols;
    try { window.localStorage.setItem(COL_KEY, JSON.stringify(cols)); } catch (e) { /* blocked */ }
  }

  function applyCols(cols) {
    ["cyr", "lat", "en"].forEach(function (c) {
      var hidden = cols[c] === false;
      document.body.classList.toggle("hide-" + c, hidden);
      var btn = document.querySelector('[data-col="' + c + '"]');
      if (btn) { btn.setAttribute("aria-pressed", hidden ? "false" : "true"); }
    });
  }

  function wireColumns() {
    var buttons = document.querySelectorAll("[data-col]");
    if (!buttons.length) { return; }
    var cols = readCols();
    applyCols(cols);
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var c = btn.getAttribute("data-col");
        var next = Object.assign({}, readCols());
        next[c] = next[c] === false;
        writeCols(next);
        applyCols(next);
      });
    });
  }

  function wireTabs() {
    var tabs = document.querySelectorAll("[data-tab]");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var idx = tab.getAttribute("data-tab");
        tabs.forEach(function (t) { t.setAttribute("aria-pressed", t === tab ? "true" : "false"); });
        document.querySelectorAll("[data-version]").forEach(function (s) {
          s.hidden = s.getAttribute("data-version") !== idx;
        });
      });
    });
  }

  function wireLearned() {
    var btn = document.querySelector("[data-learned-button]");
    if (!btn || !window.MKProgress) { return; }
    var id = Number(btn.getAttribute("data-song-id"));
    var p = window.MKProgress.load();
    function show(on) {
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.textContent = on ? "Learned (tap to undo)" : "Mark as learned";
    }
    show(p.learned.indexOf(id) !== -1);
    btn.addEventListener("click", function () {
      var cur = window.MKProgress.load();
      var on = cur.learned.indexOf(id) === -1;
      var ok = window.MKProgress.save(window.MKProgress.markLearned(cur, id, on));
      show(on);
      if (!ok) { window.MKProgress.warnBlocked(btn); }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wireColumns();
    wireTabs();
    wireLearned();
  });
})();
