/* Progress: saved in this browser only (localStorage), with Export and Import.
   Pure functions at the top are unit tested with Node. Browser wiring is at the bottom. */
(function (root) {
  "use strict";

  var KEY = "mk_progress";
  var VERSION = 1;
  var DAY_MS = 24 * 60 * 60 * 1000;
  var REMINDER_DAYS = 14;

  function emptyProgress() {
    return { version: VERSION, learned: [], lessons: {}, quiz: {}, lastExport: null, since: null };
  }

  function clone(p) { return JSON.parse(JSON.stringify(p)); }

  function markLearned(p, songId, on) {
    var out = clone(p);
    var i = out.learned.indexOf(songId);
    if (on && i === -1) { out.learned.push(songId); }
    if (!on && i !== -1) { out.learned.splice(i, 1); }
    out.learned.sort(function (a, b) { return a - b; });
    return out;
  }

  function completeLesson(p, lessonId) {
    var out = clone(p);
    out.lessons[lessonId] = true;
    return out;
  }

  function recordQuiz(p, quizId, score, total) {
    var out = clone(p);
    var prev = out.quiz[quizId];
    out.quiz[quizId] = {
      best: prev ? Math.max(prev.best, score) : score,
      last: score,
      total: total,
      attempts: prev ? prev.attempts + 1 : 1
    };
    return out;
  }

  function markExported(p, nowMs) {
    var out = clone(p);
    out.lastExport = nowMs;
    return out;
  }

  function hasProgress(p) {
    return p.learned.length > 0 || Object.keys(p.lessons).length > 0 || Object.keys(p.quiz).length > 0;
  }

  /* Remember when progress first appeared, so the export reminder can wait 14 days. */
  function touch(p, nowMs) {
    if (p.since !== null || !hasProgress(p)) { return p; }
    var out = clone(p);
    out.since = nowMs;
    return out;
  }

  /* Due 14 days after the last export, or after the first progress if never exported. */
  function reminderDue(p, nowMs) {
    if (!hasProgress(p)) { return false; }
    var reference = p.lastExport !== null ? p.lastExport : p.since;
    if (reference === null) { return false; }
    return nowMs - reference > REMINDER_DAYS * DAY_MS;
  }

  function maxOf(a, b) { return a === null ? b : (b === null ? a : Math.max(a, b)); }
  function minOf(a, b) { return a === null ? b : (b === null ? a : Math.min(a, b)); }

  /* Union of two progress records. Nothing is ever removed. */
  function mergeProgress(a, b) {
    var out = emptyProgress();
    var seen = {};
    a.learned.concat(b.learned).forEach(function (id) {
      if (!seen[id]) { seen[id] = true; out.learned.push(id); }
    });
    out.learned.sort(function (x, y) { return x - y; });
    Object.keys(a.lessons).concat(Object.keys(b.lessons)).forEach(function (k) { out.lessons[k] = true; });
    Object.keys(a.quiz).concat(Object.keys(b.quiz)).forEach(function (k) {
      var qa = a.quiz[k];
      var qb = b.quiz[k];
      if (!qa) { out.quiz[k] = clone(qb); return; }
      if (!qb) { out.quiz[k] = clone(qa); return; }
      var pick = (qb.best > qa.best || (qb.best === qa.best && qb.attempts > qa.attempts)) ? qb : qa;
      out.quiz[k] = clone(pick);
    });
    out.lastExport = maxOf(a.lastExport, b.lastExport);
    out.since = minOf(a.since, b.since);
    return out;
  }

  function serialize(p) { return JSON.stringify(p, null, 1); }

  function isPlainObject(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }

  function parseImport(text) {
    var notFile = { ok: false, error: "This is not a progress file from this site." };
    var raw;
    try { raw = JSON.parse(text); } catch (e) { return notFile; }
    if (!isPlainObject(raw) || typeof raw.version !== "number") { return notFile; }
    if (raw.version > VERSION) {
      return { ok: false, error: "This file comes from a newer version of the site. Please update the page and try again." };
    }
    if (raw.version !== VERSION) { return notFile; }
    if (!Array.isArray(raw.learned) || !raw.learned.every(Number.isInteger)) { return notFile; }
    if (!isPlainObject(raw.lessons) || !Object.keys(raw.lessons).every(function (k) { return raw.lessons[k] === true; })) { return notFile; }
    if (!isPlainObject(raw.quiz)) { return notFile; }
    var quizOk = Object.keys(raw.quiz).every(function (k) {
      var q = raw.quiz[k];
      return isPlainObject(q) && ["best", "last", "total", "attempts"].every(function (f) { return Number.isFinite(q[f]); });
    });
    if (!quizOk) { return notFile; }
    var last = raw.lastExport === undefined ? null : raw.lastExport;
    if (last !== null && !Number.isFinite(last)) { return notFile; }
    var since = raw.since === undefined ? null : raw.since;
    if (since !== null && !Number.isFinite(since)) { return notFile; }
    return {
      ok: true,
      progress: {
        version: VERSION,
        learned: raw.learned.slice().sort(function (a, b) { return a - b; }),
        lessons: clone(raw.lessons),
        quiz: clone(raw.quiz),
        lastExport: last,
        since: since
      }
    };
  }

  function loadProgress(storage) {
    if (!storage) { return emptyProgress(); }
    try {
      var text = storage.getItem(KEY);
      if (!text) { return emptyProgress(); }
      var r = parseImport(text);
      return r.ok ? r.progress : emptyProgress();
    } catch (e) {
      return emptyProgress();
    }
  }

  function saveProgress(storage, p) {
    if (!storage) { return false; }
    try { storage.setItem(KEY, serialize(p)); return true; } catch (e) { return false; }
  }

  /* Importing merges the file into what is already saved, so nothing learned since the backup is lost. */
  function importText(storage, text) {
    var r = parseImport(text);
    if (!r.ok) { return r; }
    var merged = mergeProgress(loadProgress(storage), r.progress);
    if (!saveProgress(storage, merged)) {
      return { ok: false, error: "Your browser is blocking saving, so the file could not be loaded." };
    }
    return { ok: true, progress: merged };
  }

  /* A store reads and writes progress. If saving is blocked, the latest progress is kept in memory,
     so buttons keep working for this visit (undo included) even though nothing is saved. */
  function createStore(getStorage, now) {
    var memory = null;
    return {
      load: function () {
        return memory ? clone(memory) : loadProgress(getStorage());
      },
      save: function (p) {
        var stamped = touch(p, now());
        var ok = saveProgress(getStorage(), stamped);
        memory = ok ? null : clone(stamped);
        return ok;
      }
    };
  }

  function summaryText(p) {
    var text = "Songs learned: " + p.learned.length + ". Lessons finished: " + Object.keys(p.lessons).length + ".";
    var q = p.quiz.alphabet;
    if (q) { text += " Alphabet quiz best: " + q.best + " of " + q.total + "."; }
    return text;
  }

  var api = {
    createStore: createStore, summaryText: summaryText,
    emptyProgress: emptyProgress, markLearned: markLearned, completeLesson: completeLesson,
    recordQuiz: recordQuiz, markExported: markExported, reminderDue: reminderDue,
    touch: touch, mergeProgress: mergeProgress,
    serialize: serialize, parseImport: parseImport, importText: importText,
    loadProgress: loadProgress, saveProgress: saveProgress
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
    return;
  }

  /* ---- Browser wiring ---- */

  function getStorage() {
    try { return root.localStorage || null; } catch (e) { return null; }
  }

  var persistAsked = false;
  function askPersist() {
    if (persistAsked) { return; }
    persistAsked = true;
    try {
      if (root.navigator && root.navigator.storage && root.navigator.storage.persist) {
        root.navigator.storage.persist();
      }
    } catch (e) { /* best effort */ }
  }

  function banner(text, role) {
    var main = document.querySelector("main");
    if (!main) { return; }
    var el = document.createElement("p");
    el.className = "notice";
    el.setAttribute("role", role || "status");
    el.textContent = text;
    main.insertBefore(el, main.firstChild);
  }

  var store = createStore(getStorage, function () { return Date.now(); });
  var BLOCKED_TEXT = "Your browser is blocking saving, so your progress will be lost when you leave this page. " +
    "Try a normal (not private) window.";

  root.MKProgress = {
    load: function () { return store.load(); },
    save: function (p) { askPersist(); return store.save(p); },
    markLearned: markLearned, completeLesson: completeLesson, recordQuiz: recordQuiz,
    /* Show the warning next to the element that was just used, so it is on screen. */
    warnBlocked: function (near) {
      if (document.querySelector("[data-blocked-warning]")) { return; }
      var el = document.createElement("p");
      el.className = "notice";
      el.setAttribute("role", "alert");
      el.setAttribute("data-blocked-warning", "");
      el.textContent = BLOCKED_TEXT;
      if (near && near.parentNode) { near.parentNode.insertBefore(el, near.nextSibling); return; }
      var main = document.querySelector("main");
      if (main) { main.insertBefore(el, main.firstChild); }
    }
  };

  function download(name, text) {
    var blob = new Blob([text], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function wirePage() {
    var p = root.MKProgress.load();
    if (reminderDue(p, Date.now()) && !document.querySelector("[data-progress-page]")) {
      banner("Your progress is saved only in this browser. Visit My progress and press Export to keep a backup copy.");
    }
    if (!getStorage()) { root.MKProgress.warnBlocked(); }

    var page = document.querySelector("[data-progress-page]");
    if (!page) { return; }
    var status = page.querySelector("[data-progress-status]");
    var summary = page.querySelector("[data-progress-summary]");
    function say(t) { status.textContent = t; }
    function show() { summary.textContent = summaryText(root.MKProgress.load()); }
    show();

    page.querySelector("[data-export]").addEventListener("click", function () {
      var cur = markExported(root.MKProgress.load(), Date.now());
      root.MKProgress.save(cur);
      download("macedonian-progress.json", serialize(cur));
      say("Your progress file was saved to your downloads. Keep it somewhere safe.");
    });

    page.querySelector("[data-import]").addEventListener("change", function (ev) {
      var input = ev.target;
      var file = input.files && input.files[0];
      if (!file) { return; }
      var reader = new FileReader();
      reader.onload = function () {
        var r = importText(getStorage(), String(reader.result));
        say(r.ok ? "Your progress was added to this browser." : r.error);
        show();
        input.value = "";
      };
      reader.onerror = function () { say("The file could not be read."); input.value = ""; };
      reader.readAsText(file);
    });
  }

  document.addEventListener("DOMContentLoaded", wirePage);
})(typeof window !== "undefined" ? window : this);
