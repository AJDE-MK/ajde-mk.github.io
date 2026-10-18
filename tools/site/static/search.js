/* Song search. Matches Cyrillic, Latin and English titles, ignoring case and accents. */
(function (root) {
  "use strict";

  /* Strip accents, lower-case, and fold the English spellings ch, sh, zh onto c, s, z,
     so "chupi" finds "čupi". Applied to both the query and the titles. */
  function normalize(text) {
    return String(text || "")
      .normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/ch/g, "c").replace(/sh/g, "s").replace(/zh/g, "z");
  }

  function filterSongs(index, query) {
    var words = normalize(query).split(/\s+/).filter(Boolean);
    if (!words.length) { return index.slice(); }
    return index.filter(function (s) {
      var hay = normalize(s.cyr + " " + s.lat + " " + s.en + " " + (s.alt || ""));
      return words.every(function (w) { return hay.indexOf(w) !== -1; });
    });
  }

  var api = { filterSongs: filterSongs, normalize: normalize };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
    return;
  }

  function wire() {
    var box = document.querySelector("[data-search]");
    if (!box) { return; }
    var input = box.querySelector("[data-search-input]");
    var results = box.querySelector("[data-search-results]");
    var count = box.querySelector("[data-search-count]");
    var list = document.querySelector("[data-song-list]");
    var jump = document.querySelector("[data-jump]");
    var index = null;
    var loading = false;
    var failed = false;

    function render() {
      var q = input.value;
      if (!q.trim()) {
        results.hidden = true; list.hidden = false; jump.hidden = false; count.textContent = "";
        return;
      }
      if (!index) { return; }
      var found = filterSongs(index, q);
      results.innerHTML = "";
      found.slice(0, 200).forEach(function (s) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = s.url; a.lang = "mk"; a.textContent = s.cyr;
        var sp = document.createElement("span");
        sp.className = "latin"; sp.textContent = " " + s.lat + (s.en ? " (" + s.en + ")" : "");
        li.appendChild(a); li.appendChild(sp); results.appendChild(li);
      });
      results.hidden = false; list.hidden = true; jump.hidden = true;
      count.textContent = found.length === 0 ? "No songs match that." :
        (found.length > 200 ? "Showing the first 200 of " + found.length + " songs." : found.length + " song(s).");
    }

    function ensureIndex() {
      if (index || loading || failed) { return; }
      loading = true;
      fetch(box.getAttribute("data-search-index")).then(function (r) { return r.json(); }).then(function (j) {
        index = j; loading = false; render();
      }).catch(function () {
        loading = false;
        failed = true;
        count.textContent = "Search could not load. You can still use the letter list below.";
      });
    }

    input.addEventListener("input", function () { ensureIndex(); render(); });
    input.addEventListener("focus", ensureIndex);
  }

  document.addEventListener("DOMContentLoaded", wire);
  root.MKSearch = api;
})(typeof window !== "undefined" ? window : this);
