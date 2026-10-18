# Macedonian Songbook Site: Design

Date: 2026-10-18. Author: Claude, with Mike. Name: **Ајде (Ajde)**, chosen by Mike on 2026-10-18. It means "come on, let's go" and starts 43 of the 1598 song titles. Suggested repo name: `ajde`.

## Intent and why

Mike's father is Macedonian. Mike's Macedonian speaking is weak, his understanding is a little better, and his writing is very weak. His mother wrote a doctoral dissertation, later published as the book *Em Baba, Em Nevesta* (on Amazon KDP). This project extends that work: **re-learn Macedonian by listening to songs and reading along**, then grow into real lessons.

Almost nothing good exists online for people learning Macedonian, and most of what exists costs a monthly subscription. This site is free, and other people (family, friends, anyone with Macedonian roots) can use it too. It is mainly for Mike first.

## What is being built

One static website with two sections now, and room for more later:

1. **Songs.** 1598 folk songs. Each song page lets a person read the full lyrics while a YouTube video plays.
2. **Lessons.** The first lesson is the **Cyrillic alphabet**, because every song is written in Cyrillic. More lessons come later.

The whole site is plain files hosted free on GitHub Pages, the same way as Mike's book site (`https://thebriefyoudeserved.github.io/thebriefyoudeserved/`, source at `D:\Repos\thebriefyoudeserved`, which is hand-written HTML with no build step).

## Goals

- **Song page.**
  - Whole song shown at once, scrolling. **No line-by-line sync** with the video (timestamps for 1598 songs would be hand work, and every performer sings at a different speed).
  - **Three columns:** Cyrillic, Latin, English. A toggle for each column shows or hides it. Rows line up line by line.
  - Songs with two or three lyric versions show each version as a tab.
  - An "About this song" note appears on the 57 songs that have a Background note.
  - On a desktop the video stays pinned at the top while the lyrics scroll under it.
  - **Embedded YouTube video** (privacy-friendly embed address) with a "Watch on YouTube" link under it, because some uploaders block embedding and some viewers run ad blockers.
  - Songs with no video yet show the existing YouTube search link instead of a player.
- **Video list.** One data file maps song number to a YouTube video ID (and an optional start time). Claude finds a starter batch of about 20 to 30 well-known songs and Mike checks each one. Mike adds the rest over time.
- **"Wrong or missing video?" form.** On each song page. Fields: song (pre-filled), YouTube link, optional note, and a hidden trap field for spam bots. It sends an email to Mike through a free form service (Web3Forms is the first choice) to a **dedicated Gmail account Mike will create for this**. No account is needed for visitors. Mike decided against the GitHub-issue route because visitors would have to create GitHub accounts.
- **Alphabet lesson.** A grid of all 31 Macedonian letters. Tapping a letter shows its Latin match, a written sound hint (for example "like 'ts' in cats"), and a sample word. The letters English lacks (ѓ, ќ, ѕ, љ, њ, џ) get extra notice. A short quiz follows. Audio is **not recorded at launch**, but every letter and sample word has an empty slot ready for a recording (an audio file path in the data), so adding audio later needs no redesign. Mike or his mom may record it later.
- **Progress, saved in the visitor's browser** (localStorage), with no accounts.
  - Because clearing "site data" erases it, the site also has an **Export** button (saves a small file), an **Import** button, a periodic reminder to export, and a request to the browser for persistent storage.
  - Confirmed by Mike for launch: songs marked "learned", lesson completion, and quiz scores. A personal word list is not in the first release. One progress record covers the whole site.
- **Honest labelling of English.** Every English column carries a visible label for where it came from (see Data). Machine translation is never presented as checked.

## Non-goals

- No user accounts, no server, no database. (A free online database could be added later if people ask.)
- No line-synced lyrics.
- No recorded audio at launch.
- No full curriculum at launch. Only the alphabet lesson ships first; the structure must make adding lessons easy.
- No monthly fees or ads.

## Anti-goals (failure even if it technically works)

- **It looks like AI slop.** Mike named this as the thing that would make him wince. That means no purple or blue gradients, no emoji headings, no generic card grids, no stock "language app" look.
- Wrong or misaligned lyrics shown as if verified.
- A visitor loses their progress without warning.
- Machine-written English passed off as an official translation.

## Look and feel (decided by Mike: "A, woven textile")

Mike picked the **woven textile** direction from three sketches because it "brings out the red fustani colors" (fustan is the traditional dress). Intent, to be refined by the builder:
- Cream cloth background, deep red and near-black as the main colors, serif type.
- A repeating border, like Macedonian embroidery, along the top and bottom of pages.
- The sketch used roughly: background `#f3ead8`, red `#a3151c`, ink `#1c1410`, a serif such as Georgia. These are starting values, not final.
- **Mike's reference photo:** a person in a traditional dress. It has a near-black base with bold vertical deep-red stripes, a belt of small multicolored embroidery (green, yellow, blue, pink, white), and a white blouse with wide sleeves and a red-and-black embroidered bodice. Take the palette and rhythm from it: wide red and black stripes as the main structure, and tiny multicolor stitch motifs as rare accents (for example on the border, bullets, or the active letter in the alphabet grid). Keep the accents small. Red and black lead, so the page does not turn into a rainbow. The photo is mood reference only and is not to be used on the site.
- Must read well on a phone as well as a desktop. (Builder's call on exact breakpoints; the three-column view needs a sensible phone fallback, such as stacked lines.)
- Light, accessible text sizes. Cyrillic must be set in a font that renders it well.

## Data (already built)

All of this exists today in `D:\Repos\Macedonian\data\songs\NNNN.json`, one file per song, produced by scripts in `D:\Repos\Macedonian\tools`. The original songbook files in `D:\Repos\Macedonian\songbook` were not changed.

- 1598 songs, 31,059 lyric lines. **Every line has Cyrillic, Latin and English**, and each stanza has the same line count in all three.
- Each version records `en_source`:
  - `pesna`: English from Pesna.org, with line breaks possibly moved to line up. (479 versions)
  - `mt`: machine translation by Claude (1119 versions, including the 1089 songs that never had Pesna English).
  - `mixed`: Pesna English plus some lines written by Claude (44 versions). Those individual lines carry `en_mt: true`.
- 306 lines were written by helper agents (mostly second and third versions). Songs with the most uncertain ones: 560, 470, 1111, 407, 2, 928.
- Known unchecked items: Pesna's own English has errors (for example song 454 says "sixty" for the Cyrillic "seventy"). Song 1685 contains em-dashes from Pesna. A few misaligned songs may remain among the 391 that agents passed unchanged; the feedback form is meant to catch them.
- Each record also holds: title (Cyrillic, Latin, English), Pesna.org URL, Background note, English-source note, translator's notes, a "Words to learn" list (1089 songs have one), performers, and Pesna.org audio sample links.
- Pesna.org lyrics are public-domain folk lyrics and the site content is CC BY. **Every song page must keep the attribution line** the songbook pages already carry.
- Tools: `songbook_parse.py`, `build_data.py`, `check_alignment.py` (a weak heuristic, not trusted), `merge_work.py`, `ALIGN_INSTRUCTIONS.md`. Re-running `build_data.py` overwrites the merged English; run `merge_work.py` after it. Debug logging in these scripts must stay (Mike's standing rule).

## Constraints

- Windows machine. Scripts in **Python**. No stubs or placeholders. Modular, small files, no one giant file.
- Static output only: HTML, CSS, a little JavaScript. No framework. No server.
- Hosted on GitHub Pages in a **new GitHub repo** next to the book site. The repo name, and so the web address, comes from the final site name. Renaming after the first push changes the address and breaks old links, so the name must be settled before the first push. Everything is built and tested locally first.
- A secrets file such as the form key must be handled so private values stay out of the repo. (The form service's public key is designed to be visible on the page; the Gmail address itself must not be written into the repo.)
- Site text written by Claude avoids em-dashes and en-dashes (Mike's standing rule).
- Debug logging stays in any new command or script until Mike says to remove it.

## Calls Claude made (not yet agreed by Mike)

- Python build script turns the JSON into static HTML pages. The book site's hand-written approach does not scale to 1598 pages.
- GitHub Pages deploys through a GitHub Actions run that builds the site from the data, so generated pages need not be committed. (A simpler fallback is to commit the built output.)
- A song browse and search page: search by title in Cyrillic or Latin, plus an A-to-Z list. A site with 1598 songs is unusable without it.
- Web3Forms as the form service. Its free limits must be checked before wiring it (Claude's belief is a few hundred messages a month, not verified).
- The "Words to learn" lists in 1089 songs, and the songbook's glossary, history and artist guides, are held for later lessons and a Guides section. They are not part of the first release.

More calls Claude made after the reviewer read this document (all open to Mike's override):

- **Video list** is a hand-edited JSON file. The builder adds a validator (checks song numbers exist, IDs look like YouTube IDs, no duplicates) and a small helper script that adds an entry from a pasted YouTube link. The starter batch of 20 to 30 is committed as the first entries after Mike checks them.
- **Data after launch.** `data/songs/*.json` is the source of truth once the site is built. Corrections from the form are edited into those JSON files directly. `build_data.py` and `merge_work.py` are not re-run after launch, because that would overwrite fixes.
- **Deploy.** GitHub Actions builds and deploys. The data folder lives in the public repo, so the Pesna.org attribution line stays on every page. The machine-translated English is public, and it is always labelled.
- **Form key.** The Web3Forms access key is committed as a public value, since the service is built that way. The Gmail address is set only in the Web3Forms dashboard, never in the repo. Until the Gmail account exists, each form shows "Feedback form coming soon" and sends nothing. If the free limits turn out too low, the builder swaps the service in one setting.
- **Site name.** The builder uses one configurable base path. The builder builds and tests locally and does not push until Mike gives the final name.
- **Unreviewed alphabet content.** The sound hints and sample words may ship before a native-speaker review, with a visible "not yet checked by a Macedonian speaker" label, as with the English column.
- **English labels.** Plain, calm wording, for example: "English: from Pesna.org", "English: machine translation, not checked by a native speaker", "English: partly from Pesna.org, partly machine translation (marked)". The default view shows all three columns. Column toggles are remembered in the browser.
- **Progress record** carries a version number from day one, so the format can change later without breaking old exports.

## Left to the builder

Page layouts and the final visual design within the textile direction; the border pattern; exact file and folder structure; the quiz mechanics for the alphabet lesson; navigation; how the three-column view degrades on a phone; the JSON shape of the progress record; the exact sound hints and sample words for each letter (to be reviewed by a Macedonian speaker before launch).

## Open items for Mike

- **Site name: settled.** Ајде (Ajde). Which GitHub account hosts the repo, and so the web address, is still open.
- **Form email.** Mike will use his normal Gmail (a second account was refused). He signs up at Web3Forms himself; the address is never written into the repo. The access key is passed in as `MK_FORM_KEY`.
- **Layout change (2026-10-18).** The video sits in its own sticky left column on screens 900px wide or more, so it no longer covers the lyrics.
- **Which videos** to use for the starter batch, once Claude proposes them.
- **Native-speaker check** of the alphabet sound hints and sample words.
