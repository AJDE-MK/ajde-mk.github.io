import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const Q = require("../../tools/site/static/quiz.js");

const letters = "абвгдежзиклмнопрстуфхцчшјѓќ".split("").map((c, i) => ({
  upper: c.toUpperCase(), lower: c, latin: "L" + i,
}));

function seeded(seed) {
  let s = seed;
  return () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
}

test("makeQuiz returns n questions", () => {
  assert.equal(Q.makeQuiz(letters, 10, seeded(1)).length, 10);
});

test("every question has 4 distinct options including the right answer", () => {
  for (const q of Q.makeQuiz(letters, 10, seeded(7))) {
    assert.equal(q.options.length, 4);
    assert.equal(new Set(q.options).size, 4);
    assert.ok(q.options.includes(q.answer));
  }
});

test("the answer belongs to the letter asked about", () => {
  for (const q of Q.makeQuiz(letters, 10, seeded(3))) {
    const l = letters.find((x) => x.upper === q.letter);
    assert.equal(q.answer, l.latin);
  }
});

test("no letter is asked twice in one quiz", () => {
  const qs = Q.makeQuiz(letters, 10, seeded(5));
  assert.equal(new Set(qs.map((q) => q.letter)).size, 10);
});

test("grade is true only for the right answer", () => {
  const q = Q.makeQuiz(letters, 1, seeded(2))[0];
  assert.equal(Q.grade(q, q.answer), true);
  const wrong = q.options.find((o) => o !== q.answer);
  assert.equal(Q.grade(q, wrong), false);
});

test("passed is true from 70 percent up", () => {
  assert.equal(Q.passed(7, 10), true);
  assert.equal(Q.passed(10, 10), true);
  assert.equal(Q.passed(6, 10), false);
  assert.equal(Q.passed(0, 10), false);
  assert.equal(Q.passed(0, 0), false);
});

test("feedbackText says right or names the right answer", () => {
  const q = { letter: "Ж", answer: "ž", options: ["ž", "z", "s", "š"] };
  assert.equal(Q.feedbackText(q, "ž"), "Right!");
  assert.equal(Q.feedbackText(q, "z"), "Not quite. It is ž.");
});

test("makeQuiz never asks for more questions than there are letters", () => {
  assert.equal(Q.makeQuiz(letters.slice(0, 5), 10, seeded(1)).length, 5);
});
