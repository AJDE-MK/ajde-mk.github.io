# Ајде (Ajde)

"Ajde" means "come on, let's go". It is the word that starts more song titles than almost any other. This is a free website of 1598 Macedonian songs. Each song shows Cyrillic, Latin and English side by side, with an embedded video. There is also an alphabet lesson. Progress is saved in the visitor's browser.

Design: `docs/2026-10-18-macedonian-songbook-site-design.md`. Plan: `docs/superpowers/plans/2026-10-18-macedonian-songbook-site.md`.

## Build the site on your computer

```
python tools\site\build_site.py --debug
```

The site is written to `site\`. Open `site\index.html` in a browser. Links start with `/`, so for a proper preview serve the folder:

```
python -m http.server 8000 --directory site
```

Then open http://localhost:8000/. The build writes a debug log to `data\site_build.log`.

## Run the tests

```
python -I -m unittest discover -s tests
node --test "tests/js/*.test.mjs"
```

## Add or change a video

Paste a YouTube link. The tool checks it and saves it to `data\videos.json`:

```
python tools\site\videos_tool.py add 450 https://www.youtube.com/watch?v=VIDEOID
python tools\site\videos_tool.py add 450 https://youtu.be/VIDEOID --start 12
python tools\site\videos_tool.py validate
```

A bad entry in `videos.json` stops the build with a plain message.

To look for more candidates (highest views among matching videos, embeddable only, under 10 minutes):

```
python tools\site\video_search.py --count 40
```

It writes `data\videos.candidates.json` and `docs\video-candidates.md` for you to check. It never edits `videos.json`.

## Settings

Set these as environment variables, or edit `tools\site\config.py`:

| Name | Meaning |
| --- | --- |
| `MK_BASE_PATH` | Folder prefix when the site lives at `user.github.io/repo-name`. Example: `/repo-name`. Empty for a root site. |
| `MK_FORM_KEY` | Web3Forms access key for the "Wrong or missing video?" form. Empty shows "Feedback form coming soon". The key is public by design. The email address that receives messages is set in the Web3Forms dashboard, never in this repo. |

## Deploy

`.github/workflows/deploy.yml` runs the tests, builds the site, and publishes it to GitHub Pages on every push to `main`. In the GitHub repo: Settings, Pages, set Source to "GitHub Actions". The Web3Forms access key is set in the workflow file. To change it, add a repository variable named `MK_FORM_KEY`, which overrides it. The key is public by design. The email address that receives messages is set only in the Web3Forms dashboard.

## Data

`data\songs\*.json` is the source of truth for the lyrics. Fix a wrong line by editing that file. Do not re-run `tools\build_data.py` or `tools\merge_work.py`: they rebuild from the original Markdown and would overwrite fixes.

Lyrics come from Pesna.org (folk lyrics in the public domain; site content CC BY). English lines are labelled by source on every song page. Machine translations were written by Claude and are not checked by a native speaker.
