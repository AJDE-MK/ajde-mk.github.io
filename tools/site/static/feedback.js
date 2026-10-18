/* Feedback form: checks the link and sends it to Web3Forms. Plain-language messages only. */
(function (root) {
  "use strict";

  var YT_HOSTS = ["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"];
  var SHORT_HOSTS = ["youtu.be", "www.youtu.be"];
  var ID_RE = /^[A-Za-z0-9_-]{11}$/;

  /* True only for a link that points at one video, not a YouTube search or home page. */
  function validateUrl(text) {
    if (!text) { return false; }
    try {
      var u = new URL(String(text).trim());
      if (u.protocol !== "https:" && u.protocol !== "http:") { return false; }
      var host = u.hostname.toLowerCase();
      var parts = u.pathname.split("/").filter(Boolean);
      if (SHORT_HOSTS.indexOf(host) !== -1) { return parts.length >= 1 && ID_RE.test(parts[0]); }
      if (YT_HOSTS.indexOf(host) === -1) { return false; }
      if (u.pathname === "/watch") { return ID_RE.test(u.searchParams.get("v") || ""); }
      return parts.length >= 2 && ["embed", "shorts", "live", "v"].indexOf(parts[0]) !== -1 && ID_RE.test(parts[1]);
    } catch (e) {
      return false;
    }
  }

  var VIDEO_ERROR = "That does not look like a YouTube link. Please copy the web address from the top of the YouTube page and paste it here.";
  var NOTE_ERROR = "Please tell us what is wrong, in a few words.";

  /* A video report needs a YouTube link. Any other report needs a note. */
  function validateFields(fields) {
    var kind = fields.kind === "words" || fields.kind === "other" ? fields.kind : "video";
    if (kind === "video") {
      return validateUrl(fields.url) ? { ok: true } : { ok: false, error: VIDEO_ERROR };
    }
    return String(fields.note || "").trim() ? { ok: true } : { ok: false, error: NOTE_ERROR };
  }

  function buildPayload(fields) {
    var payload = {
      access_key: fields.access_key,
      subject: fields.subject,
      song_id: fields.song_id,
      kind: fields.kind || "video",
      url: String(fields.url || "").trim()
    };
    var note = String(fields.note || "").trim();
    if (note) { payload.note = note; }
    return payload;
  }

  var api = { validateUrl: validateUrl, validateFields: validateFields, buildPayload: buildPayload };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
    return;
  }
  root.MKFeedback = api;

  function wire() {
    var form = document.querySelector("[data-feedback-form]");
    if (!form) { return; }
    var status = form.querySelector(".feedback-status");
    function say(text) { status.textContent = text; }

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var data = new FormData(form);
      if (data.get("botcheck")) { say("Thank you! Your message was sent."); return; }
      var fields = {
        access_key: data.get("access_key"),
        subject: data.get("subject"),
        song_id: data.get("song_id"),
        kind: data.get("kind"),
        url: data.get("url"),
        note: data.get("note")
      };
      var check = validateFields(fields);
      if (!check.ok) { say(check.error); return; }
      var send = form.querySelector('button[type="submit"]');
      send.disabled = true;
      say("Sending...");
      fetch(form.action, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(buildPayload(fields))
      }).then(function (r) {
        return r.json().catch(function () { return null; });
      }).then(function (j) {
        send.disabled = false;
        if (j && j.success) {
          form.reset();
          say("Thank you! Your message was sent.");
        } else {
          say("Sorry, it did not send. Please try again in a little while.");
        }
      }).catch(function () {
        send.disabled = false;
        say("Sorry, it did not send. Please check your internet connection and try again.");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", wire);
})(typeof window !== "undefined" ? window : this);
