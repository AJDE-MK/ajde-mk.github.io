import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { buildPayload, validateUrl, validateFields } = require("../../tools/site/static/feedback.js");

test("validateUrl needs a real video, not just a youtube.com address", () => {
  assert.equal(validateUrl("https://www.youtube.com/"), false);
  assert.equal(validateUrl("https://www.youtube.com/results?search_query=bilbil"), false);
  assert.equal(validateUrl("https://youtu.be/short"), false);
  assert.equal(validateUrl("https://www.youtube.com/embed/dQw4w9WgXcQ"), true);
  assert.equal(validateUrl("https://www.youtube.com/shorts/dQw4w9WgXcQ"), true);
  assert.equal(validateUrl("https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=9s"), true);
});

test("video reports need a YouTube link", () => {
  assert.equal(validateFields({ kind: "video", url: "", note: "x" }).ok, false);
  assert.equal(validateFields({ kind: "video", url: "hello", note: "" }).ok, false);
  assert.equal(validateFields({ kind: "video", url: "https://youtu.be/dQw4w9WgXcQ", note: "" }).ok, true);
});

test("words and other reports need a note, and no link", () => {
  assert.equal(validateFields({ kind: "words", url: "", note: "Line 3 is wrong" }).ok, true);
  assert.equal(validateFields({ kind: "other", url: "", note: "   " }).ok, false);
  assert.equal(validateFields({ kind: "words", url: "", note: "" }).ok, false);
});

test("an unknown kind is treated as a video report", () => {
  assert.equal(validateFields({ kind: "weird", url: "", note: "x" }).ok, false);
});

test("a failed check gives a plain-language message", () => {
  assert.match(validateFields({ kind: "video", url: "hello", note: "" }).error, /YouTube link/);
  assert.match(validateFields({ kind: "words", url: "", note: "" }).error, /tell us/i);
});

test("buildPayload carries the kind", () => {
  const p = buildPayload({ access_key: "K", subject: "S", song_id: "1", kind: "words", url: "", note: "n" });
  assert.equal(p.kind, "words");
});

test("validateUrl accepts a YouTube link", () => {
  assert.equal(validateUrl("https://youtu.be/dQw4w9WgXcQ"), true);
  assert.equal(validateUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), true);
});

test("validateUrl rejects text that is not a YouTube link", () => {
  assert.equal(validateUrl("hello"), false);
  assert.equal(validateUrl("https://example.com/video"), false);
  assert.equal(validateUrl(""), false);
});

test("buildPayload carries the song id and url", () => {
  const p = buildPayload({ access_key: "K", subject: "S", song_id: "450", url: "https://youtu.be/dQw4w9WgXcQ", note: "good one" });
  assert.equal(p.song_id, "450");
  assert.equal(p.url, "https://youtu.be/dQw4w9WgXcQ");
  assert.equal(p.note, "good one");
});

test("buildPayload drops an empty note", () => {
  const p = buildPayload({ access_key: "K", subject: "S", song_id: "450", url: "u", note: "   " });
  assert.equal("note" in p, false);
});

test("buildPayload trims the url", () => {
  const p = buildPayload({ access_key: "K", subject: "S", song_id: "450", url: "  https://youtu.be/dQw4w9WgXcQ  ", note: "" });
  assert.equal(p.url, "https://youtu.be/dQw4w9WgXcQ");
});
