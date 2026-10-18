# Macedonian Songbook Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static, free website of 1598 Macedonian songs (Cyrillic, Latin, English in three aligned columns, embedded YouTube video) plus an alphabet lesson, with browser-saved progress and an email feedback form.

**Architecture:** A Python build script reads `data/songs/*.json` and writes plain HTML, CSS and JS into `site/`. All behavior in the browser (column toggles, progress, quiz, feedback form) is small vanilla JavaScript. No server, no framework. GitHub Pages hosts `site/` via a GitHub Actions run.

**Tech Stack:** Python 3 (standard library only, `unittest`), vanilla JS (ES modules not required), Node `--test` for JS unit tests, GitHub Actions.

**Spec:** `D:\Repos\Macedonian\docs\2026-10-18-macedonian-songbook-site-design.md`

## Global Constraints

- Windows. Scripts in Python. No stubs, no TODOs, no placeholders. Small modular files.
- Static output only: HTML, CSS, a little JS. No framework, no gradients, no emoji, no generic card grids.
- Palette starting values: background `#f3ead8`, red `#a3151c`, ink `#1c1410`, serif Georgia. Red and black lead; multicolor stitch accents (green, yellow, blue, pink, white) small and rare.
- Three columns in order Cyrillic, Latin, English. Column toggles remembered in the browser.
- English source labels (exact wording):
  - `pesna`: "English: from Pesna.org"
  - `mt`: "English: machine translation, not checked by a native speaker"
  - `mixed`: "English: partly from Pesna.org, partly machine translation (marked)"
- Every song page keeps this attribution line: "Lyrics: Pesna.org (folk lyrics in the public domain; site content CC BY)."
- Progress record: JSON with `"version": 1`; tracks learned songs, lesson completion, quiz scores. Stored in `localStorage` under key `mk_progress`. Export/Import buttons. Every localStorage call wrapped in try/catch.
- Form: Web3Forms access key is a public value in `tools/site/config.py`. If the key is empty, every form shows "Feedback form coming soon" and sends nothing. A hidden honeypot field catches bots. Gmail address never appears in the repo.
- Site base path is one setting, `BASE_PATH` in `tools/site/config.py`, default `""`. No push to GitHub until Mike gives the final name.
- New commands and scripts carry debug logging (`logging`, DEBUG to a log file). Never remove it.
- No em-dash or en-dash characters anywhere in code, comments or site text.
- Do not modify `songbook\` or re-run `tools\build_data.py` (it would overwrite merged English).

## Review Focus

- Lyric text containing `&`, `<`, `>`, `'`, `"` renders as text, never as markup.
- A song with three lyric versions renders three tabs, and each version's English label matches that version's `en_source`.
- `localStorage` blocked (private window): the site still renders, toggles work for the session, and progress buttons explain that saving is off.
- Import of a malformed file, a non-JSON file, or a file with a newer `version` is rejected with a plain message and leaves existing progress untouched.
- A song with no video ID shows the search link and no broken player. A video ID that is not 11 URL-safe characters is rejected by the validator.
- With `BASE_PATH="/some-name"` every internal link and asset path still resolves.

---

## File Structure

```
tools/site/
  config.py            settings (SITE_TITLE, BASE_PATH, FORM_KEY, paths)
  layout.py            page(title, body, nav_active) -> full HTML string, border, nav, footer
  songs.py             load_songs() -> list[dict]; load_videos() -> dict[int, dict]
  render_song.py       render_song_page(song, video) -> str
  render_pages.py      render_home(), render_browse(), render_alphabet(), render_progress()
  alphabet.py          LETTERS: list of letter dicts (data), quiz_questions()
  videos_tool.py       validate_videos(), add_video(song_id, url, start=0) (CLI)
  build_site.py        orchestrates; writes site/ ; logs
  static/style.css     tokens, border, three-column table, toggles, responsive
  static/app.js        column toggles, version tabs, mark-learned button
  static/progress.js   load/save/export/import (pure functions + DOM wiring)
  static/quiz.js       alphabet quiz
  static/feedback.js   form submit to Web3Forms
data/videos.json       {"450": {"id": "XXXXXXXXXXX", "start": 0}}
data/alphabet.json     31 letters (source for alphabet.py)
tests/                 test_*.py (unittest), js/*.test.mjs (node --test)
.github/workflows/deploy.yml
```

---

### Task 1: Layout, styles, build skeleton

**Files:** Create `tools/site/config.py`, `layout.py`, `songs.py`, `build_site.py`, `static/style.css`; Test `tests/test_layout.py`, `tests/test_build_skeleton.py`.

**Interfaces:**
- Produces: `config.SITE_TITLE: str`, `config.BASE_PATH: str`, `config.FORM_KEY: str`, `config.ROOT: Path`, `config.SITE_DIR: Path`.
- Produces: `layout.page(title: str, body: str, active: str = "") -> str` (full HTML doc; links use `BASE_PATH`; includes top and bottom embroidery border, nav: Home, Songs, Alphabet, My progress).
- Produces: `songs.load_songs() -> list[dict]` (sorted by id), `songs.load_videos() -> dict[int, dict]`.
- Produces: `build_site.main(argv=None) -> int`, writes `site/index.html` and copies `static/` to `site/static/`.

- [ ] **Step 1: Write failing tests.** `test_layout`: `page("A & B", "<p>x</p>")` returns a string containing `<title>A &amp; B`, `class="border"` twice, and nav links starting with the base path; with `BASE_PATH="/x"` patched, `href="/x/songs/"` appears. `test_build_skeleton`: running `build_site.main(["--out", tmp])` returns 0 and `tmp/index.html` and `tmp/static/style.css` exist.
- [ ] **Step 2: Run** `python -I -m unittest discover -s tests` from `D:\Repos\Macedonian`. Expect FAIL (modules missing).
- [ ] **Step 3: Implement** the modules above. `style.css` defines the palette as CSS variables, the embroidery border as a repeating `linear-gradient` pattern (red/black/cream bars only, no color gradients), serif type, and a Cyrillic-safe font stack (`Georgia, "Times New Roman", serif`). `build_site.main` accepts `--out` and `--debug`, logs to `data/site_build.log`.
- [ ] **Step 4: Run tests.** Expect PASS.

### Task 2: Song page renderer

**Files:** Create `tools/site/render_song.py`; extend `style.css`; Create `static/app.js` (toggles and tabs); Test `tests/test_render_song.py`.

**Interfaces:**
- Consumes: `layout.page`, `songs.load_songs`.
- Produces: `render_song_page(song: dict, video: dict | None) -> str`; `song_url(song: dict) -> str` returning `"/songs/NNNN-slug/"` prefixed with `BASE_PATH`.

- [ ] **Step 1: Failing tests.** (a) A song whose lyric contains `a & <b> 'q'` renders `a &amp; &lt;b&gt; &#x27;q&#x27;` and no raw `<b>`. (b) A 3-version fixture renders three elements with `data-version` 0, 1, 2 and each shows the label text for its own `en_source`. (c) The page contains the attribution line exactly once and the Pesna.org link. (d) Song with `background` shows an "About this song" block; one without it does not. (e) Three column toggles exist (`data-col="cyr"`, `"lat"`, `"en"`). (f) A line with `en_mt: true` gets class `mt-line`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** One `<table class="lyrics">` per stanza with three cells per row, all text passed through `html.escape(quote=True)`. Version tabs are buttons that show or hide `<section data-version>`. `app.js` toggles column classes on `<body>` and stores choices in `localStorage` (try/catch). Show Cyrillic title as `h1`, Latin and English titles under it, Pesna id link, performers list, and the existing Pesna.org audio sample links in a collapsed `<details>`.
- [ ] **Step 4: Run tests, expect PASS.**

### Task 3: Video list, player and validator

**Files:** Create `tools/site/videos_tool.py`; modify `render_song.py` (player block); Create `data/videos.json` (`{}` to start); Test `tests/test_videos.py`.

**Interfaces:**
- Produces: `parse_youtube_id(url: str) -> str | None` (handles `youtu.be/ID`, `watch?v=ID`, `embed/ID`, `shorts/ID`); `validate_videos(videos: dict, song_ids: set[int]) -> list[str]` (problems: unknown song, bad ID, duplicate ID); `add_video(song_id: int, url: str, start: int = 0) -> None`; CLI `python tools\site\videos_tool.py add <song_id> <url> [--start N]` and `validate`.
- Consumes: Task 2 `render_song_page` player block: `render_player(song_id: int, video: dict | None, search_url: str) -> str`.

- [ ] **Step 1: Failing tests.** `parse_youtube_id("https://youtu.be/dQw4w9WgXcQ?t=5") == "dQw4w9WgXcQ"` and the other three URL forms; `parse_youtube_id("https://example.com/x") is None`. `validate_videos({"450": {"id": "short"}}, {450})` returns a problem. Unknown song id returns a problem. `render_player(450, {"id": "dQw4w9WgXcQ", "start": 12}, "u")` contains `youtube-nocookie.com/embed/dQw4w9WgXcQ?start=12`, a `loading="lazy"` iframe, and a "Watch on YouTube" link; `render_player(450, None, "u")` has no `<iframe` and contains the search link.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** The player block sits in a container that is sticky at the top on screens wider than 900px. Under the player show the "Wrong or missing video? Tell us" button that opens the Task 4 form.
- [ ] **Step 4: Run tests, expect PASS.**

### Task 4: Feedback form

**Files:** Create `static/feedback.js`; modify `render_song.py` (form markup); extend `style.css`; Test `tests/test_feedback_markup.py`, `tests/js/feedback.test.mjs`.

**Interfaces:**
- Produces: `render_feedback_form(song_id: int, title: str, form_key: str) -> str`; JS `buildPayload(fields) -> object` and `validateUrl(text) -> boolean` exported for tests.

- [ ] **Step 1: Failing tests.** With `form_key=""` the markup contains "Feedback form coming soon" and no `<form`. With a key it contains a form with hidden `access_key`, hidden `subject` containing the song title, hidden honeypot named `botcheck`, a URL input, an optional note, and `action="https://api.web3forms.com/submit"`. JS: `validateUrl("https://youtu.be/dQw4w9WgXcQ")` true; `validateUrl("hello")` false; `buildPayload` includes the song id and drops the note when empty.
- [ ] **Step 2: Run both test sets, expect FAIL** (`node --test tests/js`).
- [ ] **Step 3: Implement.** Plain-language steps above the field for people with little computer skill: "1. Open YouTube and find this song. 2. Copy the web address from the top of the page. 3. Paste it here and press Send." Success and failure messages are plain sentences. Form posts by `fetch` and shows the result in place.
- [ ] **Step 4: Run, expect PASS.**

### Task 5: Progress module

**Files:** Create `static/progress.js`; modify `app.js` (Mark as learned button), `render_pages.render_progress`; Test `tests/js/progress.test.mjs`.

**Interfaces:**
- Produces (pure, exported): `emptyProgress() -> {version:1, learned:[], lessons:{}, quiz:{}}`; `markLearned(p, songId, on) -> p`; `completeLesson(p, lessonId) -> p`; `recordQuiz(p, quizId, score, total) -> p`; `serialize(p) -> string`; `parseImport(text) -> {ok:true, progress} | {ok:false, error:string}`; `loadProgress(storage) -> p`; `saveProgress(storage, p) -> boolean`.

- [ ] **Step 1: Failing tests.** `parseImport("not json")` and `parseImport('{"version":99}')` return `ok:false` with a plain message; `parseImport(serialize(p))` round-trips; `markLearned` is idempotent and removable; `loadProgress` with a storage whose `getItem` throws returns `emptyProgress()`; `saveProgress` returns false when `setItem` throws.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** The DOM wiring requests persistent storage (`navigator.storage.persist`) once, shows an Export reminder after 14 days since the last export, and offers Export (downloads `macedonian-progress.json`) and Import (file picker). When saving is blocked it shows "Your browser is blocking saving. Use Export to keep your progress."
- [ ] **Step 4: Run, expect PASS.**

### Task 6: Alphabet lesson and quiz

**Files:** Create `data/alphabet.json`, `tools/site/alphabet.py`, `static/quiz.js`; modify `render_pages.py`; Test `tests/test_alphabet.py`, `tests/js/quiz.test.mjs`.

**Interfaces:**
- Produces: `alphabet.load_letters() -> list[dict]` with keys `upper`, `lower`, `latin`, `hint`, `word_cyr`, `word_lat`, `word_en`, `audio` (path or `null`), `special` (true for ѓ ќ ѕ љ њ џ); `render_alphabet() -> str`; JS `makeQuiz(letters, n, rng) -> questions[]`, `grade(q, answer) -> boolean`.

- [ ] **Step 1: Failing tests.** `len(load_letters()) == 31`; the six `special` letters are exactly ѓ ќ ѕ љ њ џ; every letter has non-empty `latin`, `hint`, `word_cyr`, `word_en`; every `word_cyr` starts with that letter (case-insensitive). Page contains the label "Sound hints and sample words are not yet checked by a Macedonian speaker." and an `<audio>` element only for letters with an `audio` path. JS: `makeQuiz(letters, 10, seededRng)` returns 10 questions with 4 distinct options, the right answer among them; `grade` is true only for the right answer.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** Grid of letter tiles; tapping a tile shows its detail panel. Latin matches follow the songbook's romanization (ѓ=ǵ, ќ=ḱ, ѕ=dz, љ=lj, њ=nj, џ=dž, ж=ž, ч=č, ш=š). Quiz: "Which sound is this letter?" with Latin options; the score is saved through `recordQuiz`; finishing marks lesson `alphabet` complete.
- [ ] **Step 4: Run, expect PASS.**

### Task 7: Home, browse and search

**Files:** modify `render_pages.py`, `build_site.py`; Create `static/search.js`; Test `tests/test_browse.py`, `tests/js/search.test.mjs`.

**Interfaces:**
- Produces: `render_home(songs) -> str`, `render_browse(songs) -> str`; build writes `site/search-index.json` as a list of `{id, cyr, lat, en, url}`; JS `filterSongs(index, query) -> list` (case-insensitive; matches Cyrillic, Latin and English titles; Latin match ignores diacritics so "zel" finds "Žel...").

- [ ] **Step 1: Failing tests.** Browse page lists every song exactly once, grouped by first Cyrillic letter, each linking to its song URL. `filterSongs` finds "Македонче" by "makedonce", by "Македонче", and by an English word in its title; empty query returns all.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** Home: short intro in the textile style, links to Songs and Alphabet, a "Start here: learn the alphabet" call. Browse: search box above a letter-grouped list with a jump bar.
- [ ] **Step 4: Run, expect PASS.**

### Task 8: Full build, deploy file, verification

**Files:** Create `.github/workflows/deploy.yml`, `README.md` (how to run, add videos, deploy), `.gitignore` (`site/`, `.superpowers/`, `*.log`); Test `tests/test_full_build.py`.

- [ ] **Step 1: Failing test.** Full build to a temp dir produces 1598 song pages; every internal `href`/`src` in every page resolves to an existing file (with default `BASE_PATH` and with `/some-name`); no page contains the characters U+2014 or U+2013 except inside lyric or translation text sourced from the data.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the workflow (checkout, setup-python, `python tools/site/build_site.py`, upload-pages-artifact, deploy-pages) and README.
- [ ] **Step 4: Run all tests** (`python -I -m unittest discover -s tests` and `node --test tests/js`). Expect all PASS. Then open `site/index.html` and one song page in the browser and check them by eye at desktop and phone widths.

### Task 9: Starter video candidates (needs Mike)

- [ ] Search the web for about 25 well-known songs and write candidates to `data/videos.candidates.json` with the video title and channel. Do not add them to `data/videos.json`. Mike checks each one, then they move over with `videos_tool.py add`.
