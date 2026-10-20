import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const R = require("../../tools/site/static/review.js");

const answers = [
  { song: 917, video: "5UB7oS7JMqE", vote: "yes" },
  { song: 948, video: "QHpvlr_kG6U", vote: "no" },
  { song: 253, video: "4honlU4aL1k", vote: "skip" },
];

test("only yes and no answers are counted", () => {
  const c = R.countAnswers(answers);
  assert.deepEqual(c, { yes: 1, no: 1, skipped: 1 });
});

test("the message lists one line per answer and leaves out the skipped ones", () => {
  const m = R.buildMessage(answers);
  assert.match(m, /song=917 video=5UB7oS7JMqE vote=yes/);
  assert.match(m, /song=948 video=QHpvlr_kG6U vote=no/);
  assert.doesNotMatch(m, /song=253/);
  assert.match(m, /Video review answers: 1 yes, 1 no/);
});

test("nothing to send when every answer is skipped", () => {
  assert.equal(R.hasAnswers([{ song: 1, video: "A", vote: "skip" }]), false);
  assert.equal(R.hasAnswers(answers), true);
  assert.equal(R.hasAnswers([]), false);
});

test("unknown votes and malformed rows are ignored", () => {
  const m = R.buildMessage([{ song: 1, video: "A", vote: "maybe" }, { vote: "yes" }, null, answers[0]]);
  assert.match(m, /song=917/);
  assert.doesNotMatch(m, /song=1 /);
  assert.equal((m.match(/vote=/g) || []).length, 1);
});

test("buildPayload carries the key, a subject and the message", () => {
  const p = R.buildPayload("KEY", answers);
  assert.equal(p.access_key, "KEY");
  assert.match(p.subject, /Video review/);
  assert.match(p.message, /song=917/);
  assert.equal(p.kind, "review");
});

test("parseSaved only trusts a plain object of yes/no/skip choices", () => {
  assert.deepEqual(R.parseSaved('{"917":"yes","948":"no","1":"skip","2":"banana"}'), { 917: "yes", 948: "no", 1: "skip" });
  assert.deepEqual(R.parseSaved("not json"), {});
  assert.deepEqual(R.parseSaved("[1,2]"), {});
  assert.deepEqual(R.parseSaved(null), {});
});
