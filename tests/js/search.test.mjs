import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const S = require("../../tools/site/static/search.js");

const index = [
  { id: 130, cyr: "А бре Македонче", lat: "A bre Makedonče", en: "Hey little Macedonian", url: "/songs/0130/" },
  { id: 9, cyr: "Ајде Лено да ојме", lat: "Ajde Leno da ojme", en: "Come on Leno, let's dance", url: "/songs/0009/" },
  { id: 1052, cyr: "Бабино девојче", lat: "Babino devojče", en: "Grandma's girl", url: "/songs/1052/" },
  { id: 164, cyr: "Ḱерка", lat: "Ḱerka", en: "Daughter", url: "/songs/0164/" },
];

test("finds a title by Latin letters without diacritics", () => {
  assert.deepEqual(S.filterSongs(index, "makedonce").map((s) => s.id), [130]);
});

test("finds a title by Cyrillic text", () => {
  assert.deepEqual(S.filterSongs(index, "Македонче").map((s) => s.id), [130]);
});

test("finds a title by an English word", () => {
  assert.deepEqual(S.filterSongs(index, "grandma").map((s) => s.id), [1052]);
});

test("is not case sensitive", () => {
  assert.deepEqual(S.filterSongs(index, "AJDE").map((s) => s.id), [9]);
  assert.deepEqual(S.filterSongs(index, "бабино").map((s) => s.id), [1052]);
});

test("accented k and g match plain k and g", () => {
  assert.deepEqual(S.filterSongs(index, "kerka").map((s) => s.id), [164]);
});

test("ch, sh and zh spellings match the accented letters", () => {
  const idx = [
    { id: 2, cyr: "Мори чупи костурчанки", lat: "Mori čupi kosturčanki", en: "Hey, girls", url: "/2/" },
    { id: 3, cyr: "Шума", lat: "Šuma", en: "Forest", url: "/3/" },
    { id: 4, cyr: "Жена", lat: "Žena", en: "Woman", url: "/4/" },
  ];
  assert.deepEqual(S.filterSongs(idx, "chupi").map((s) => s.id), [2]);
  assert.deepEqual(S.filterSongs(idx, "shuma").map((s) => s.id), [3]);
  assert.deepEqual(S.filterSongs(idx, "zhena").map((s) => s.id), [4]);
});

test("an alternative name finds the song", () => {
  const idx = [{ id: 473, cyr: "Сторил ниет", lat: "Storil niet", en: "The rabbit decided", alt: "Зајко Zajko", url: "/473/" }];
  assert.deepEqual(S.filterSongs(idx, "Зајко").map((s) => s.id), [473]);
  assert.deepEqual(S.filterSongs(idx, "zajko").map((s) => s.id), [473]);
  assert.deepEqual(S.filterSongs(idx, "kokorajko"), []);
});

test("empty or blank query returns everything", () => {
  assert.equal(S.filterSongs(index, "").length, 4);
  assert.equal(S.filterSongs(index, "   ").length, 4);
});

test("no match returns an empty list", () => {
  assert.deepEqual(S.filterSongs(index, "zzzz"), []);
});

test("every word of the query must match", () => {
  assert.deepEqual(S.filterSongs(index, "ajde leno").map((s) => s.id), [9]);
  assert.deepEqual(S.filterSongs(index, "ajde makedonce"), []);
});
