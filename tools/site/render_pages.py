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


def _count(n, noun):
    return f"{n} {noun}{'s' if n != 1 else ''}"


def _review_link(review_count, intro):
    if not review_count:
        return ""
    return (
        f'<p class="review-link">{intro} <a href="{layout.url("/review/")}">'
        f"Help by reviewing {_count(review_count, 'video')}</a>.</p>"
    )


def _peek_lines(song, n=4):
    try:
        lines = [l["cyr"] for st in song["versions"][0]["stanzas"] for l in st["lines"]]
    except (KeyError, IndexError):
        return []
    return lines[:n]


def _review_row(row):
    s, v = row["song"], row["video"]
    sid = s["id"]
    peek = "<br>".join(_e(line) for line in _peek_lines(s))
    note = f' <span class="note">({_e(v["note"])})</span>' if v.get("note") else ""
    watch = f"https://www.youtube.com/watch?v={_e(v['id'])}"
    return f"""<article class="review-row" data-song-id="{sid}" data-video-id="{_e(v['id'])}">
<h3><a href="{_e(render_song.song_url(s))}" lang="mk">{_e(s['title_cyr'])}</a> <span class="latin">{_e(s['title_latin'])}</span> <span class="en">&middot; {_e(s['title_en'])}</span></h3>
<p class="lyric-peek" lang="mk">{peek}</p>
<p class="video-line"><a href="{watch}" rel="noopener">Watch: {_e(v['title'])}</a> <span class="meta">{_e(v['channel'])}, {v['views']:,} views</span>{note}</p>
<p><button type="button" data-play data-video-id="{_e(v['id'])}">Play it here</button></p>
<div class="play-slot"></div>
<fieldset class="vote"><legend>Is the video the same song as the words above?</legend>
<label><input type="radio" name="vote-{sid}" value="yes"> Yes, same song</label>
<label><input type="radio" name="vote-{sid}" value="no"> No, a different song</label>
<label><input type="radio" name="vote-{sid}" value="skip" checked> Not sure</label>
</fieldset>
</article>"""


def render_review(rows, form_key):
    """Page where visitors listen to a candidate video and say whether it is the right song."""
    log.debug("render review page, %d rows", len(rows))
    if not rows:
        body = (
            "<h1>Please help by reviewing these</h1>"
            "<p>Nothing is waiting for review right now. Thank you to everyone who helped.</p>"
        )
        return layout.page("Review videos", body, active="review")
    n = len(rows)
    if form_key:
        send = (
            '<section class="review-send">'
            '<div class="botcheck" aria-hidden="true"><input type="checkbox" name="botcheck" tabindex="-1" autocomplete="off"></div>'
            f'<button type="button" data-review-send data-access-key="{_e(form_key)}">Send my answers</button>'
            '<p data-review-status role="status" aria-live="polite"></p>'
            "</section>"
        )
        script = f'<script src="{layout.url("/static/review.js")}" defer></script>'
    else:
        send = '<section class="review-send"><p>Sending answers is coming soon.</p></section>'
        script = ""
    articles = "\n".join(_review_row(r) for r in rows)
    body = f"""<h1>Please help by reviewing these</h1>
<p>A computer found a video for each song below, but it cannot hear whether it is the right one.
{_count(n, 'video')} still need a second pair of ears.</p>
<ol class="steps">
<li>Read the first lines of the song.</li>
<li>Listen to the video. Press "Play it here", or open it on YouTube.</li>
<li>If it is the same song, choose <strong>Yes</strong>. If it is a different song, choose <strong>No</strong>. If you are not sure, leave it.</li>
<li>Press <strong>Send my answers</strong> at the end. You can answer a few or all of them.</li>
</ol>
{send}
{articles}
{send}
{script}"""
    return layout.page("Review videos", body, active="review")


def render_needs_video(songs, videos, review_count=0):
    """List of songs that have no video yet, so visitors can see where they could help."""
    missing = [s for s in songs if s["id"] not in videos]
    log.debug("render needs-video page, %d songs", len(missing))
    n = len(missing)
    if not missing:
        body = (
            "<h1>Which songs have no video yet?</h1>"
            "<p>Every song has a video. Thank you to everyone who helped.</p>"
        )
        return layout.page("Songs with no video yet", body, active="songs")
    uppers = [l["upper"] for l in alphabet.load_letters()]
    order = ["0-9"] + uppers + ["other"]
    groups = {}
    for s in sorted(missing, key=lambda x: (x["title_cyr"].lower(), x["id"])):
        groups.setdefault(_group_key(s["title_cyr"], set(uppers)), []).append(s)
    present = [k for k in order if k in groups]
    jump = " ".join(f'<a href="#letter-{_e(k)}">{_e("Other" if k == "other" else k)}</a>' for k in present)
    sections = []
    for key in present:
        items = "\n".join(
            f'<li><a href="{_e(render_song.song_url(s))}" lang="mk">{_e(s["title_cyr"])}</a>'
            f' <span class="latin">{_e(s["title_latin"])}</span>'
            f' <a class="yt-search" href="{_e(render_song.search_url(s))}" rel="noopener">Search YouTube</a></li>'
            for s in groups[key]
        )
        heading = "Other" if key == "other" else key
        sections.append(
            f'<section class="letter-group" id="letter-{_e(key)}"><h2>{_e(heading)}</h2><ul>\n{items}\n</ul></section>'
        )
    count = f"{n} song{'s' if n != 1 else ''} {'have' if n != 1 else 'has'} no video yet."
    body = f"""<h1>Which songs have no video yet?</h1>
<p>{count} If you know a recording of one, open the song and use the "Wrong or missing video? Tell us" box.
All we need is a link to the YouTube video. A real recording by a singer or group is best.</p>
{_review_link(review_count, "Not sure of any? You can still help.")}
<nav class="jump" aria-label="Jump to a letter">{jump}</nav>
{chr(10).join(sections)}"""
    return layout.page("Songs with no video yet", body, active="songs")


def render_home(songs, videos=None, review_count=0):
    log.debug("render home page, %d songs", len(songs))
    help_line = ""
    if videos is not None:
        missing = sum(1 for s in songs if s["id"] not in videos)
        parts = []
        if missing:
            parts.append(
                f'<p>{missing} song{"s" if missing != 1 else ""} still '
                f'{"have" if missing != 1 else "has"} no video. '
                f'<a href="{layout.url("/needs-video/")}">Help find them</a>.</p>'
            )
        if review_count:
            parts.append(_review_link(review_count, "Or listen and check:").replace(' class="review-link"', ""))
        if parts:
            help_line = '<section class="help-intro">' + "".join(parts) + "</section>"
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
</section>
{help_line}
<section class="book-intro">
<p>Inspired by the book <em>Em Baba, Em Nevesta</em>. <a href="{layout.url('/about/')}">About this site and the book</a>.</p>
</section>"""
    return layout.page(f"{config.SITE_TITLE} ({config.SITE_TAGLINE})", body, active="home")


BOOK_URL = "https://www.amazon.com/dp/B08N3PJH7K"
BOOK_TITLE = "Macedonia . . . Em Baba, Em Nevesta: The history and culture of Macedonia told through its folk songs"


def render_about():
    log.debug("render about page")
    body = f"""<section class="about-page">
<h1>About Ајде</h1>
<p><em>Ајде</em> was inspired by <em>Em Baba, Em Nevesta</em>, a book by Dr. Kathy Dimitrievski about the history and
culture of Macedonia told through its folk songs. The book follows the language and the culture through music, and it
includes interviews she recorded in Macedonia.</p>
<p>The title means "both a grandmother and a young bride": the author's way of describing a country that is
ancient and new at the same time.</p>
<p>This site is a separate project, made by her son, Michael Dimitrievski, to help people learn Macedonian the same
way: through the songs.</p>
<p><a class="button" href="{BOOK_URL}" rel="noopener">Get the book on Amazon</a></p>
<p class="book-title">{_e(BOOK_TITLE)}</p>
<h2>Where the words come from</h2>
<ul>
<li>The lyrics come from <a href="https://pesna.org/" rel="noopener">Pesna.org</a>. They are folk lyrics in the public domain, and the site content is CC BY.</li>
<li>Pesna.org's English is used where it exists. Each song says which English you are reading.</li>
<li>Where Pesna.org has no English, or no English for a version, the English was written with the help of an AI (Claude). It is machine translation, not checked by a native speaker. Treat it as a study aid.</li>
<li>The videos are on YouTube and play from there. A song with no video has a search link instead.</li>
<li>The Cyrillic spelling and the English for a few versions that people sing differently were written by hand and are marked in the same way.</li>
</ul>
<h2>Something wrong?</h2>
<p>Every song page has a box called "Wrong or missing video? Tell us". It also takes reports of mistakes in the words.
The message goes straight to the person who runs this site. Thank you for helping.</p>
</section>"""
    return layout.page(f"About - {config.SITE_TITLE}", body, active="about")


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
