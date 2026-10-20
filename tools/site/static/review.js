/* Review page: answer "is this video the same song?" and send all answers in one message.
   Pure functions at the top are unit tested with Node. Browser wiring is at the bottom. */
(function (root) {
  "use strict";

  var SAVE_KEY = "mk_review";
  var VOTES = ["yes", "no", "skip"];

  function valid(a) {
    return a && Number.isInteger(a.song) && typeof a.video === "string" && VOTES.indexOf(a.vote) !== -1;
  }

  function countAnswers(answers) {
    var c = { yes: 0, no: 0, skipped: 0 };
    answers.filter(valid).forEach(function (a) {
      if (a.vote === "yes") { c.yes += 1; } else if (a.vote === "no") { c.no += 1; } else { c.skipped += 1; }
    });
    return c;
  }

  function hasAnswers(answers) {
    var c = countAnswers(answers);
    return c.yes + c.no > 0;
  }

  function buildMessage(answers) {
    var c = countAnswers(answers);
    var lines = ["Video review answers: " + c.yes + " yes, " + c.no + " no"];
    answers.filter(valid).forEach(function (a) {
      if (a.vote !== "skip") { lines.push("song=" + a.song + " video=" + a.video + " vote=" + a.vote); }
    });
    return lines.join("\n");
  }

  function buildPayload(accessKey, answers) {
    return {
      access_key: accessKey,
      subject: "Video review answers",
      kind: "review",
      message: buildMessage(answers)
    };
  }

  function parseSaved(text) {
    var out = {};
    var raw;
    try { raw = JSON.parse(text); } catch (e) { return out; }
    if (raw === null || typeof raw !== "object" || Array.isArray(raw)) { return out; }
    Object.keys(raw).forEach(function (k) {
      if (/^\d+$/.test(k) && VOTES.indexOf(raw[k]) !== -1) { out[k] = raw[k]; }
    });
    return out;
  }

  var api = { countAnswers: countAnswers, hasAnswers: hasAnswers, buildMessage: buildMessage,
              buildPayload: buildPayload, parseSaved: parseSaved };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
    return;
  }

  /* ---- Browser wiring ---- */

  function storage() {
    try { return root.localStorage; } catch (e) { return null; }
  }

  function loadSaved() {
    var s = storage();
    try { return parseSaved(s ? s.getItem(SAVE_KEY) : null); } catch (e) { return {}; }
  }

  function save(choices) {
    var s = storage();
    try { if (s) { s.setItem(SAVE_KEY, JSON.stringify(choices)); } } catch (e) { /* saving is optional */ }
  }

  function readAnswers() {
    return Array.prototype.map.call(document.querySelectorAll(".review-row"), function (row) {
      var sid = Number(row.getAttribute("data-song-id"));
      var checked = row.querySelector('input[name="vote-' + sid + '"]:checked');
      return { song: sid, video: row.getAttribute("data-video-id"), vote: checked ? checked.value : "skip" };
    });
  }

  function wire() {
    var rows = document.querySelectorAll(".review-row");
    if (!rows.length) { return; }

    var saved = loadSaved();
    rows.forEach(function (row) {
      var sid = row.getAttribute("data-song-id");
      if (saved[sid]) {
        var input = row.querySelector('input[name="vote-' + sid + '"][value="' + saved[sid] + '"]');
        if (input) { input.checked = true; }
      }
      row.addEventListener("change", function () {
        var choices = {};
        readAnswers().forEach(function (a) { choices[a.song] = a.vote; });
        save(choices);
      });
    });

    document.querySelectorAll("[data-play]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var slot = btn.closest(".review-row").querySelector(".play-slot");
        if (slot.firstChild) { slot.innerHTML = ""; btn.textContent = "Play it here"; return; }
        var frame = document.createElement("iframe");
        frame.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(btn.getAttribute("data-video-id"));
        frame.title = "YouTube video player";
        frame.setAttribute("allow", "encrypted-media; picture-in-picture");
        frame.setAttribute("allowfullscreen", "");
        frame.setAttribute("loading", "lazy");
        slot.appendChild(frame);
        btn.textContent = "Close the video";
      });
    });

    document.querySelectorAll("[data-review-send]").forEach(function (button) {
      button.addEventListener("click", function () {
        var section = button.closest(".review-send");
        var status = section.querySelector("[data-review-status]");
        var bot = section.querySelector('input[name="botcheck"]');
        var answers = readAnswers();
        if (bot && bot.checked) { status.textContent = "Thank you! Your answers were sent."; return; }
        if (!hasAnswers(answers)) {
          status.textContent = "Choose Yes or No for at least one song first.";
          return;
        }
        button.disabled = true;
        status.textContent = "Sending...";
        fetch("https://api.web3forms.com/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(buildPayload(button.getAttribute("data-access-key"), answers))
        }).then(function (r) { return r.json().catch(function () { return null; }); }).then(function (j) {
          button.disabled = false;
          if (j && j.success) {
            status.textContent = "Thank you! Your answers were sent.";
            save({});
            document.querySelectorAll(".review-row input[value='skip']").forEach(function (i) { i.checked = true; });
          } else {
            status.textContent = "Sorry, it did not send. Your answers are still here. Please try again in a little while.";
          }
        }).catch(function () {
          button.disabled = false;
          status.textContent = "Sorry, it did not send. Please check your internet connection and try again.";
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", wire);
})(typeof window !== "undefined" ? window : this);
