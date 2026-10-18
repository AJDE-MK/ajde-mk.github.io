"""Non-song pages: progress (this task), alphabet, home and browse (later tasks)."""
import html
import json
import logging

import alphabet
import config
import layout
import render_song

log = logging.getLogger("site.render_pages")


def _e(text):
    return html.escape(text or "", quote=True)


def _asset_url(path):
    """Site paths start with '/' and get the base path; full URLs are left alone."""
    return layout.url(path) if path.startswith("/") else path


def _letter_detail(l):
    audio = ""
    for key, label in (("audio", "Hear the letter"), ("word_audio", "Hear the word")):
        if l.get(key):
            audio += f'<p>{label}: <audio controls src="{_e(_asset_url(l[key]))}"></audio></p>'
    special = (
        '<p class="special-note">English has no letter quite like this one. Listen for it in songs.</p>'
        if l["special"]
        else ""
    )
    return (
        f'<section class="letter-detail" data-detail-for="{_e(l["lower"])}">'
        f'<h3 lang="mk">{_e(l["upper"])} {_e(l["lower"])}</h3>'
        f'<p>Latin: <strong>{_e(l["latin"])}</strong></p>'
        f'<p>Sound: {_e(l["hint"])}</p>'
        f'<p>Example: <span lang="mk">{_e(l["word_cyr"])}</span> ({_e(l["word_lat"])}), {_e(l["word_en"])}</p>'
        f"{special}{audio}"
        "</section>"
    )


def render_alphabet():
    letters = alphabet.load_letters()
    log.debug("render alphabet page, %d letters", len(letters))
    tiles = "".join(
        f'<button type="button" class="tile" data-letter="{_e(l["lower"])}" aria-pressed="false" lang="mk">'
        f'{_e(l["upper"])}{_e(l["lower"])}</button>'
        for l in letters
    )
    details = "\n".join(_letter_detail(l) for l in letters)
    quiz_data = json.dumps(
        [{"upper": l["upper"], "latin": l["latin"]} for l in letters], ensure_ascii=False
    ).replace("</", "<\\/")
    body = f"""<section class="alphabet">
<h1>The Cyrillic alphabet</h1>
<p>Macedonian songs are written in Cyrillic. There are 31 letters. Tap a letter to see its sound, its Latin spelling, and a word that starts with it.</p>
<p class="notice">Sound hints and sample words are not yet checked by a Macedonian speaker.</p>
<div class="tiles" role="group" aria-label="Letters">{tiles}</div>
<div class="letter-details">
{details}
</div>
<section class="quiz" data-quiz>
<h2>Quiz</h2>
<p>Ten quick questions. Your score is saved in this browser.</p>
<div data-quiz-stage></div>
<p><button type="button" data-quiz-start>Start the quiz</button></p>
</section>
<script type="application/json" data-letters-json>{quiz_data}</script>
</section>
<script src="{layout.url('/static/quiz.js')}" defer></script>"""
    return layout.page("The Cyrillic alphabet", body, active="alphabet")


def build_search_index(songs):
    """Compact list the browser searches: one entry per song."""
    index = []
    for s in songs:
        entry = {
            "id": s["id"],
            "cyr": s["title_cyr"],
            "lat": s["title_latin"],
            "en": s["title_en"],
            "url": render_song.song_url(s),
        }
        if s.get("aliases"):
            entry["alt"] = " ".join(s["aliases"])
        index.append(entry)
    return index


def _group_key(title, cyr_uppers):
    """First Cyrillic letter of a title, '0-9' for digits, 'other' for anything else."""
    for ch in title:
        if ch.isdigit():
            return "0-9"
        if ch.isalpha():
            up = ch.upper()
            return up if up in cyr_uppers else "other"
    return "other"


def render_browse(songs):
    log.debug("render browse page, %d songs", len(songs))
    uppers = [l["upper"] for l in alphabet.load_letters()]
    order = ["0-9"] + uppers + ["other"]
    groups = {}
    for s in sorted(songs, key=lambda x: (x["title_cyr"].lower(), x["id"])):
        groups.setdefault(_group_key(s["title_cyr"], set(uppers)), []).append(s)
    present = [k for k in order if k in groups]
    jump = " ".join(f'<a href="#letter-{_e(k)}">{_e("Other" if k == "other" else k)}</a>' for k in present)
    sections = []
    for key in present:
        items = "\n".join(
            f'<li><a href="{_e(render_song.song_url(s))}" lang="mk">{_e(s["title_cyr"])}</a>'
            f' <span class="latin">{_e(s["title_latin"])}</span></li>'
            for s in groups[key]
        )
        heading = "Other" if key == "other" else key
        sections.append(f'<section class="letter-group" id="letter-{_e(key)}"><h2>{_e(heading)}</h2><ul>\n{items}\n</ul></section>')
    body = f"""<h1>Songs</h1>
<p>{len(songs)} songs. Search by Cyrillic, Latin letters, or the English title. You can type without accents.</p>
<section data-search data-search-index="{_e(layout.url('/search-index.json'))}">
<p><label>Search<br><input type="search" data-search-input size="40" autocomplete="off" placeholder="for example: bilbil, Билбил, nightingale"></label></p>
<p data-search-count role="status" aria-live="polite"></p>
<ul data-search-results class="results" hidden></ul>
</section>
<nav class="jump" aria-label="Jump to a letter" data-jump>{jump}</nav>
<div data-song-list>
{chr(10).join(sections)}
</div>
<script src="{layout.url('/static/search.js')}" defer></script>"""
    return layout.page("Songs", body, active="songs")


def render_home(songs):
    log.debug("render home page, %d songs", len(songs))
    body = f"""<section class="hero">
<h1>Learn Macedonian through its songs</h1>
<p class="lead">Read the words while you listen. Every song here shows the Cyrillic, the Latin spelling, and the English side by side.</p>
</section>
<section class="start">
<h2>Start here</h2>
<p>The songs are written in Cyrillic. The alphabet has 31 letters, and you can learn them in an evening.</p>
<p><a class="button" href="{layout.url('/alphabet/')}">Learn the alphabet</a></p>
</section>
<section class="songs-intro">
<h2>{len(songs)} songs</h2>
<p>Folk songs, wedding songs, songs of the homeland. Pick one, press play, and follow along.</p>
<p><a class="button" href="{layout.url('/songs/')}">Browse the songs</a></p>
</section>
<section class="progress-intro">
<p>Your progress is saved in your own browser. See <a href="{layout.url('/progress/')}">My progress</a> to keep a backup.</p>
</section>"""
    return layout.page(f"{config.SITE_TITLE} ({config.SITE_TAGLINE})", body, active="home")


def render_progress():
    log.debug("render progress page")
    body = """<section data-progress-page>
<h1>My progress</h1>
<p>Your progress is saved in this browser, on this device only. There is no account to create.</p>
<p data-progress-summary class="summary"></p>
<h2>Keep a backup</h2>
<p>If you clear your browser data, or use a private window, your progress is lost.
Press <strong>Export</strong> now and then to save a small file. If you ever lose your progress,
press <strong>Import</strong> and pick that file.</p>
<p><button type="button" data-export>Export my progress</button></p>
<p><label>Import a progress file<br>
<input type="file" accept="application/json,.json" data-import></label></p>
<p>Importing adds your saved file to what is already here. It never removes songs you learned since.</p>
<p data-progress-status role="status" aria-live="polite" class="status"></p>
</section>"""
    return layout.page("My progress", body, active="progress")
