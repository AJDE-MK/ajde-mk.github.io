import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const P = require("../../tools/site/static/progress.js");

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
  };
}
const brokenStorage = {
  getItem() { throw new Error("blocked"); },
  setItem() { throw new Error("blocked"); },
};

test("emptyProgress has version 1 and empty sections", () => {
  const p = P.emptyProgress();
  assert.equal(p.version, 1);
  assert.deepEqual(p.learned, []);
  assert.deepEqual(p.lessons, {});
  assert.deepEqual(p.quiz, {});
  assert.equal(p.lastExport, null);
  assert.equal(p.since, null);
});

test("markLearned is idempotent, sorted and removable", () => {
  let p = P.emptyProgress();
  p = P.markLearned(p, 450, true);
  p = P.markLearned(p, 7, true);
  p = P.markLearned(p, 450, true);
  assert.deepEqual(p.learned, [7, 450]);
  p = P.markLearned(p, 7, false);
  assert.deepEqual(p.learned, [450]);
  p = P.markLearned(p, 99, false);
  assert.deepEqual(p.learned, [450]);
});

test("markLearned does not change the object it was given", () => {
  const p = P.emptyProgress();
  P.markLearned(p, 1, true);
  assert.deepEqual(p.learned, []);
});

test("completeLesson records the lesson", () => {
  const p = P.completeLesson(P.emptyProgress(), "alphabet");
  assert.equal(p.lessons.alphabet, true);
});

test("recordQuiz keeps the best score, the last score and the attempts", () => {
  let p = P.emptyProgress();
  p = P.recordQuiz(p, "alphabet", 7, 10);
  p = P.recordQuiz(p, "alphabet", 5, 10);
  assert.deepEqual(p.quiz.alphabet, { best: 7, last: 5, total: 10, attempts: 2 });
});

test("serialize then parseImport round-trips", () => {
  let p = P.emptyProgress();
  p = P.markLearned(p, 450, true);
  p = P.completeLesson(p, "alphabet");
  p = P.recordQuiz(p, "alphabet", 9, 10);
  const r = P.parseImport(P.serialize(p));
  assert.equal(r.ok, true);
  assert.deepEqual(r.progress, p);
});

test("parseImport rejects text that is not JSON", () => {
  const r = P.parseImport("not json");
  assert.equal(r.ok, false);
  assert.match(r.error, /not a progress file/i);
});

test("parseImport rejects a file from a newer version of the site", () => {
  const r = P.parseImport('{"version":99,"learned":[],"lessons":{},"quiz":{}}');
  assert.equal(r.ok, false);
  assert.match(r.error, /newer/i);
});

test("parseImport rejects wrong shapes", () => {
  assert.equal(P.parseImport('{"version":1,"learned":"x","lessons":{},"quiz":{}}').ok, false);
  assert.equal(P.parseImport('{"version":1,"learned":["a"],"lessons":{},"quiz":{}}').ok, false);
  assert.equal(P.parseImport("[]").ok, false);
  assert.equal(P.parseImport("null").ok, false);
});

test("importText leaves existing progress alone when the file is bad", () => {
  const good = P.serialize(P.markLearned(P.emptyProgress(), 5, true));
  const s = fakeStorage({ mk_progress: good });
  const r = P.importText(s, "junk");
  assert.equal(r.ok, false);
  assert.equal(s.data.mk_progress, good);
});

test("importText saves a good file", () => {
  const s = fakeStorage();
  const text = P.serialize(P.markLearned(P.emptyProgress(), 5, true));
  const r = P.importText(s, text);
  assert.equal(r.ok, true);
  assert.deepEqual(P.loadProgress(s).learned, [5]);
});

test("loadProgress returns empty progress when storage throws", () => {
  assert.deepEqual(P.loadProgress(brokenStorage), P.emptyProgress());
});

test("loadProgress returns empty progress when stored text is corrupt", () => {
  assert.deepEqual(P.loadProgress(fakeStorage({ mk_progress: "{oops" })), P.emptyProgress());
});

test("saveProgress returns false when storage throws and true otherwise", () => {
  assert.equal(P.saveProgress(brokenStorage, P.emptyProgress()), false);
  const s = fakeStorage();
  assert.equal(P.saveProgress(s, P.emptyProgress()), true);
  assert.ok(s.data.mk_progress);
});

test("saveProgress works with no storage at all", () => {
  assert.equal(P.saveProgress(null, P.emptyProgress()), false);
  assert.deepEqual(P.loadProgress(null), P.emptyProgress());
});

const DAY = 24 * 60 * 60 * 1000;
const NOW = 1_000_000_000_000;

test("store keeps progress in memory when saving is blocked, so undo still works", () => {
  const store = P.createStore(() => brokenStorage, () => 1000);
  let p = P.markLearned(store.load(), 7, true);
  assert.equal(store.save(p), false);
  assert.deepEqual(store.load().learned, [7]);
  p = P.markLearned(store.load(), 7, false);
  store.save(p);
  assert.deepEqual(store.load().learned, []);
});

test("store reports success and reads back from storage when saving works", () => {
  const s = fakeStorage();
  const store = P.createStore(() => s, () => 1000);
  assert.equal(store.save(P.markLearned(P.emptyProgress(), 3, true)), true);
  assert.deepEqual(P.loadProgress(s).learned, [3]);
  assert.equal(P.loadProgress(s).since, 1000);
  assert.deepEqual(store.load().learned, [3]);
});

test("store with no storage at all still works for the session", () => {
  const store = P.createStore(() => null, () => 5);
  store.save(P.markLearned(P.emptyProgress(), 2, true));
  assert.deepEqual(store.load().learned, [2]);
});

test("summaryText lists songs, lessons and quiz best", () => {
  let p = P.markLearned(P.emptyProgress(), 1, true);
  p = P.completeLesson(p, "alphabet");
  p = P.recordQuiz(p, "alphabet", 8, 10);
  assert.equal(P.summaryText(p), "Songs learned: 1. Lessons finished: 1. Alphabet quiz best: 8 of 10.");
  assert.equal(P.summaryText(P.emptyProgress()), "Songs learned: 0. Lessons finished: 0.");
});

test("export reminder is not due when there is no progress", () => {
  assert.equal(P.reminderDue(P.emptyProgress(), NOW), false);
});

test("export reminder waits 14 days from the first progress when never exported", () => {
  let p = P.markLearned(P.emptyProgress(), 1, true);
  assert.equal(P.reminderDue(p, NOW), false);
  p = P.touch(p, NOW - 3 * DAY);
  assert.equal(P.reminderDue(p, NOW), false);
  p = { ...p, since: NOW - 15 * DAY };
  assert.equal(P.reminderDue(p, NOW), true);
});

test("export reminder counts from the last export once there is one", () => {
  let p = P.touch(P.markLearned(P.emptyProgress(), 1, true), NOW - 40 * DAY);
  p = P.markExported(p, NOW - 3 * DAY);
  assert.equal(P.reminderDue(p, NOW), false);
  p = P.markExported(p, NOW - 15 * DAY);
  assert.equal(P.reminderDue(p, NOW), true);
});

test("touch sets since once and never moves it", () => {
  let p = P.touch(P.markLearned(P.emptyProgress(), 1, true), 111);
  assert.equal(p.since, 111);
  p = P.touch(p, 999);
  assert.equal(p.since, 111);
});

test("touch leaves empty progress alone", () => {
  assert.equal(P.touch(P.emptyProgress(), 5).since, null);
});

test("since survives export and import", () => {
  const p = P.touch(P.markLearned(P.emptyProgress(), 1, true), 123);
  assert.equal(P.parseImport(P.serialize(p)).progress.since, 123);
});

test("a version 1 file without since still imports", () => {
  const r = P.parseImport('{"version":1,"learned":[1],"lessons":{},"quiz":{}}');
  assert.equal(r.ok, true);
  assert.equal(r.progress.since, null);
});

test("mergeProgress keeps everything from both sides", () => {
  let a = P.markLearned(P.markLearned(P.emptyProgress(), 1, true), 3, true);
  a = P.completeLesson(a, "alphabet");
  a = P.recordQuiz(a, "alphabet", 6, 10);
  let b = P.markLearned(P.markLearned(P.emptyProgress(), 3, true), 9, true);
  b = P.recordQuiz(b, "alphabet", 8, 10);
  b = { ...b, lastExport: 50, since: 10 };
  a = { ...a, lastExport: 20, since: 30 };
  const m = P.mergeProgress(a, b);
  assert.deepEqual(m.learned, [1, 3, 9]);
  assert.equal(m.lessons.alphabet, true);
  assert.equal(m.quiz.alphabet.best, 8);
  assert.equal(m.quiz.alphabet.attempts, 1);
  assert.equal(m.lastExport, 50);
  assert.equal(m.since, 10);
});

test("mergeProgress handles missing dates", () => {
  const m = P.mergeProgress(P.emptyProgress(), P.emptyProgress());
  assert.equal(m.lastExport, null);
  assert.equal(m.since, null);
});

test("importing a backup never removes songs learned since the backup", () => {
  const backup = P.serialize(P.markLearned(P.emptyProgress(), 1, true));
  const now = P.markLearned(P.markLearned(P.emptyProgress(), 1, true), 2, true);
  const s = fakeStorage();
  P.saveProgress(s, now);
  const r = P.importText(s, backup);
  assert.equal(r.ok, true);
  assert.deepEqual(P.loadProgress(s).learned, [1, 2]);
});
