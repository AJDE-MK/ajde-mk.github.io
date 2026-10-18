/* Alphabet quiz: "Which sound is this letter?" Pure functions are unit tested with Node. */
(function (root) {
  "use strict";

  function shuffle(list, rng) {
    var a = list.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function makeQuiz(letters, n, rng) {
    var picked = shuffle(letters, rng).slice(0, Math.min(n, letters.length));
    return picked.map(function (l) {
      var wrong = shuffle(letters.filter(function (x) { return x.latin !== l.latin; }), rng)
        .slice(0, 3).map(function (x) { return x.latin; });
      return { letter: l.upper, answer: l.latin, options: shuffle(wrong.concat([l.latin]), rng) };
    });
  }

  function grade(question, answer) { return answer === question.answer; }

  /* The lesson counts as finished from 70 percent up. */
  function passed(score, total) { return total > 0 && score / total >= 0.7; }

  function feedbackText(question, answer) {
    return grade(question, answer) ? "Right!" : "Not quite. It is " + question.answer + ".";
  }

  var api = { makeQuiz: makeQuiz, grade: grade, passed: passed, feedbackText: feedbackText };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
    return;
  }

  /* ---- Browser wiring ---- */

  function wire() {
    var box = document.querySelector("[data-quiz]");
    var dataEl = document.querySelector("[data-letters-json]");
    if (!box || !dataEl) { return; }
    var letters = JSON.parse(dataEl.textContent);
    var stage = box.querySelector("[data-quiz-stage]");
    var QUIZ_LENGTH = 10;

    function start() {
      var qs = makeQuiz(letters, QUIZ_LENGTH, Math.random);
      var index = 0;
      var score = 0;

      function render() {
        var q = qs[index];
        stage.innerHTML = "";
        var h = document.createElement("p");
        h.className = "quiz-letter";
        h.textContent = q.letter;
        var ask = document.createElement("p");
        ask.textContent = "Question " + (index + 1) + " of " + qs.length + ". Which sound is this letter?";
        var row = document.createElement("div");
        row.className = "quiz-options";
        var result = document.createElement("p");
        result.className = "quiz-result";
        result.setAttribute("role", "status");
        result.setAttribute("aria-live", "polite");
        var next = document.createElement("button");
        next.type = "button";
        next.hidden = true;
        next.textContent = index + 1 < qs.length ? "Next question" : "See my score";
        next.addEventListener("click", function () {
          index += 1;
          if (index < qs.length) { render(); } else { finish(); }
        });
        q.options.forEach(function (opt) {
          var b = document.createElement("button");
          b.type = "button";
          b.textContent = opt;
          b.addEventListener("click", function () {
            if (grade(q, opt)) { score += 1; }
            result.textContent = feedbackText(q, opt);
            row.querySelectorAll("button").forEach(function (x) { x.disabled = true; });
            next.hidden = false;
            next.focus();
          });
          row.appendChild(b);
        });
        stage.appendChild(h);
        stage.appendChild(ask);
        stage.appendChild(row);
        stage.appendChild(result);
        stage.appendChild(next);
        row.querySelector("button").focus();
      }

      function finish() {
        var p = window.MKProgress ? window.MKProgress.load() : null;
        var saved = true;
        var done = passed(score, qs.length);
        if (p) {
          p = window.MKProgress.recordQuiz(p, "alphabet", score, qs.length);
          if (done) { p = window.MKProgress.completeLesson(p, "alphabet"); }
          saved = window.MKProgress.save(p);
        }
        stage.innerHTML = "";
        var msg = document.createElement("p");
        msg.setAttribute("tabindex", "-1");
        msg.textContent = "You got " + score + " out of " + qs.length + "." +
          (done ? " Alphabet lesson finished!" : " Get 7 or more to finish the lesson. Try again!");
        var again = document.createElement("button");
        again.type = "button";
        again.textContent = "Try again";
        again.addEventListener("click", start);
        stage.appendChild(msg);
        stage.appendChild(again);
        if (!saved && window.MKProgress) { window.MKProgress.warnBlocked(again); }
        msg.focus();
      }

      render();
    }

    box.querySelector("[data-quiz-start]").addEventListener("click", start);
  }

  function wireTiles() {
    var tiles = document.querySelectorAll("[data-letter]");
    var details = document.querySelectorAll("[data-detail-for]");
    if (!tiles.length) { return; }
    function show(letter) {
      details.forEach(function (d) { d.hidden = d.getAttribute("data-detail-for") !== letter; });
      tiles.forEach(function (t) { t.setAttribute("aria-pressed", t.getAttribute("data-letter") === letter ? "true" : "false"); });
    }
    tiles.forEach(function (t) {
      t.addEventListener("click", function () { show(t.getAttribute("data-letter")); });
    });
    show(tiles[0].getAttribute("data-letter"));
  }

  document.addEventListener("DOMContentLoaded", function () { wireTiles(); wire(); });
  root.MKQuiz = api;
})(typeof window !== "undefined" ? window : this);
