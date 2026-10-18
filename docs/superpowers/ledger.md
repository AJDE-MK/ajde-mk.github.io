# Ledger, plan: docs/superpowers/plans/2026-10-18-macedonian-songbook-site.md

Pre-flight: Task 2 consumes Task 1 `layout.page` and `songs.load_songs`; Task 3 extends Task 2 `render_song_page`; Task 4 adds a form to the Task 2/3 page; Task 5 wires Task 2's learned button; Task 6 and 7 extend `render_pages.py`. No conflicts found.

Ruling: no git repo and no worktree, Bash tool is blocked on this machine, so no commit steps and no sdd scripts. Progress is recorded here by hand. Cost if wrong: no per-task commit history; a `git init` can be added at the first push.
Ruling: tests are run as `python -I -m unittest discover -s tests` plus `node --test "tests/js/*.test.mjs"` (the folder form fails on this Node). `tests/support.py` puts `tools/site` on sys.path and clears MK_BASE_PATH and MK_FORM_KEY. Cost if wrong: none.

Task 1: complete (layout, config, songs, build skeleton; tests 7/7)
Task 2: complete (song page renderer; suite 16/16)
Task 3: complete (video list, validator, player; suite 28/28). Ruling: the feedback form and player live in `feedback.py` and `render_song.py`, not one file; cost: none.
Task 4: complete (feedback form; python 34/34, js 5/5)
Task 5: complete (progress module and page; python 37/37, js 21/21)
Task 6: complete (alphabet data, page, quiz; python 50/50, js 27/27)
Task 7: complete (home, browse, search; python 59/59, js 35/35)
Task 8: complete (full build, 404, workflow, README; python 73/73, js 35/35). 1598 song pages built, link check clean at root and under a sub-path.
Task 9: search done (2026-10-18). 40 candidates in `data/videos.candidates.json` and `docs/video-candidates.md`, chosen by highest views among title-matching, embeddable videos under 10 minutes. NOT added to `data/videos.json` until Mike checks them. Ruling: "well known" is approximated by number of performers on Pesna.org; cost if wrong: a few lesser-known songs picked first.
Later pass (Mike asked to fix the deferred minors): fixed quiz focus and per-question feedback, lesson done only at 7 of 10 or more, quiz best on My progress, in-memory fallback when saving is blocked, warning shown next to the button, feedback link must point at one video, videos_tool no longer crashes on odd files, search folds ch/sh/zh, no retry loop on failed index, Markdown emphasis shown as italics with an "unchecked" note, watch link keeps start time, base font size follows the browser, audio paths get the base path plus a word_audio slot. Suite: python 106/106, js 57/57. Still deferred: long dashes from Pesna source text in songs 547, 1228, 1248, 1534, 1630, 1685 (not typed by the builder).

Final review: fresh Opus reviewer, one pass.
Final: fixed C1 CI env breaks tests: ran suite with MK_BASE_PATH and MK_FORM_KEY set RED, support.py clears them, GREEN 79/79. Workflow now sets them only on the build step and also runs the JS tests.
Final: fixed I1 translator credit missing: test_pesna_translator_credit_is_shown RED to GREEN.
Final: fixed I2 machine-line marker lost on phones and unexplained: css rule `table.lyrics td.mt-line` plus visible legend, tests RED to GREEN.
Final: fixed I3 reminder on every page: `since` field, reminder waits 14 days, tests RED to GREEN.
Final: fixed I4 import replaced progress: import now merges (nothing removed), input reset after use, tests RED to GREEN.
Final: fixed I5 import not keyboard reachable: file input is visible, test RED to GREEN.
Final: fixed I6 form could not report lyric errors: kind selector, words and other reports need a note not a link, tests RED to GREEN. Also disables Send while sending and handles non-JSON replies.
Suite after fixes: python 79/79, js 49/49, also 79/79 with CI environment variables set.

Final: minor (deferred): quiz drops keyboard focus after each answer and gives no per-question feedback.
Final: minor (deferred): lesson marked complete at 0/10; quiz scores not shown on My progress.
Final: minor (deferred): with saving blocked, "Mark as learned" flips but cannot undo; blocked warning appears at the top of the page, off screen from the quiz.
Final: minor (deferred): feedback accepts any youtube.com address, such as the home page.
Final: minor (deferred): videos_tool crashes with a traceback on a number as an ID or a top-level list in videos.json.
Final: minor (deferred): search does not match ch, sh, zh spellings; failed index load is retried on every keystroke.
Final: minor (deferred): Markdown asterisks show literally in "About this song" (18 songs); the "Source of these notes: Qwen's draft" line has no "not checked" wording.
Final: minor (deferred): "Watch on YouTube" link drops the start time.
Final: minor (deferred): html font size is fixed at 17px and ignores the visitor's browser text size.
Final: minor (deferred): future audio paths do not get BASE_PATH; one audio slot per letter, none per sample word.
Final: minor (deferred): long dashes from Pesna data remain in songs 547, 1228, 1248, 1534, 1630, 1685.
