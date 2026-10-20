"""Render one song page: three aligned columns, version tabs, labels, attribution."""
import html
import logging
import re
from urllib.parse import quote_plus

import config
import layout
from feedback import render_feedback_form

log = logging.getLogger("site.render_song")

EN_LABELS = {
    "pesna": "English: from Pesna.org",
    "mt": "English: machine translation, not checked by a native speaker",
    "mixed": "English: partly from Pesna.org, partly machine translation (marked)",
}
MIXED_LEGEND = "Lines with a blue bar on the left are machine translation."
COLUMNS = [("cyr", "Cyrillic"), ("lat", "Latin"), ("en", "English")]


def _e(text):
    return html.escape(text or "", quote=True)


_EMPHASIS = re.compile(r"\*(?=\S)([^*\n]*?\S)\*")
UNCHECKED_NOTE = "These notes are a draft and have not been checked by a native speaker."


def source_note(raw):
    """Plain wording for where a background note came from. Hides internal names from the public page."""
    if "Pesna.org" in (raw or ""):
        return "Notes from Pesna.org."
    return "Notes written for this site, partly drafted with an AI assistant."


def _with_emphasis(text):
    """Escape the text, then turn *word* into italics. Safe: escaping happens first."""
    return _EMPHASIS.sub(r"<em>\1</em>", _e(text))


def song_url(song):
    return f"{config.BASE_PATH}/songs/{song['id']:04d}-{song['slug']}/"


def search_url(song):
    query = quote_plus(f"{song['title_cyr']} песна")
    return f"https://www.youtube.com/results?search_query={query}"


def render_player(song_id, video, search):
    """Embedded YouTube player, or a search link when the song has no video yet."""
    if not video:
        return (
            '<div class="player no-video">'
            "<p>No video for this song yet.</p>"
            f'<p><a href="{_e(search)}">Search YouTube for this song</a></p>'
            "<p>Know this song? Suggest a video in the box below.</p>"
            "</div>"
        )
    vid = video["id"]
    start = int(video.get("start", 0))
    watch = f"https://www.youtube.com/watch?v={_e(vid)}" + (f"&amp;t={start}s" if start > 0 else "")
    return (
        '<div class="player">'
        '<div class="player-frame">'
        f'<iframe src="https://www.youtube-nocookie.com/embed/{_e(vid)}?start={start}" '
        'title="YouTube video player" loading="lazy" '
        'allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen></iframe>'
        "</div>"
        f'<p class="player-links"><a href="{watch}">Watch on YouTube</a></p>'
        "</div>"
    )


def _stanza_table(stanza):
    rows = []
    for line in stanza["lines"]:
        en_class = "c-en mt-line" if line.get("en_mt") else "c-en"
        en_title = ' title="Machine translation written for this site"' if line.get("en_mt") else ""
        rows.append(
            "<tr>"
            f'<td class="c-cyr" lang="mk">{_e(line["cyr"])}</td>'
            f'<td class="c-lat" lang="mk-Latn">{_e(line["lat"])}</td>'
            f'<td class="{en_class}" lang="en"{en_title}>{_e(line["en"])}</td>'
            "</tr>"
        )
    return '<table class="lyrics"><tbody>\n' + "\n".join(rows) + "\n</tbody></table>"


def _version_section(index, version, song):
    hidden = " hidden" if index > 0 else ""
    source = version["en_source"]
    label = EN_LABELS.get(source, EN_LABELS["mt"])
    extra = ""
    if song.get("english_kind") == "pesna" and source in ("pesna", "mixed") and song.get("en_note"):
        extra += f'<p class="en-credit">{_e(song["en_note"].strip().strip("*").strip())}</p>\n'
    if source == "mixed":
        extra += f'<p class="en-legend">{_e(MIXED_LEGEND)}</p>\n'
    tables = "\n".join(_stanza_table(st) for st in version["stanzas"])
    return (
        f'<section class="version" data-version="{index}"{hidden}>\n'
        f'<p class="en-label">{_e(label)}</p>\n{extra}{tables}\n</section>'
    )


def _tabs(versions):
    buttons = []
    for i, v in enumerate(versions):
        name = v["label"] or f"Version {i + 1}"
        pressed = "true" if i == 0 else "false"
        buttons.append(f'<button type="button" data-tab="{i}" aria-pressed="{pressed}">{_e(name)}</button>')
    return '<div class="tabs" role="group" aria-label="Lyric versions">' + "".join(buttons) + "</div>"


def _toolbar(song):
    toggles = "".join(
        f'<button type="button" data-col="{key}" aria-pressed="true">{label}</button>' for key, label in COLUMNS
    )
    return (
        '<div class="toolbar">'
        f'<div class="col-toggles" role="group" aria-label="Show columns">{toggles}</div>'
        f'<button type="button" data-learned-button data-song-id="{song["id"]}" aria-pressed="false">'
        "Mark as learned</button>"
        "</div>"
    )


def _listen(song):
    parts = []
    if song.get("performers"):
        parts.append(f'<p class="performers">Performers on Pesna.org: {_e(", ".join(song["performers"]))}</p>')
    if song.get("audio"):
        links = "".join(
            f'<li><a href="{_e(a["url"])}">{_e(a["who"])}</a></li>' for a in song["audio"]
        )
        parts.append(f"<details><summary>Audio samples on Pesna.org</summary><ul>{links}</ul></details>")
    return "\n".join(parts)


def render_song_page(song, video):
    log.debug("render song %s video=%s", song["id"], bool(video))
    versions = song["versions"]
    multi = len(versions) > 1
    about = ""
    if song.get("background"):
        about = (
            '<section class="about"><h2>About this song</h2>'
            f'<p>{_with_emphasis(song["background"])}</p>'
            f'<p class="source-note">{_e(source_note(song.get("background_source", "")))} {_e(UNCHECKED_NOTE)}</p></section>'
        )
    notes = ""
    if song.get("translator_notes"):
        notes = (
            "<details class=\"translator-notes\"><summary>Translator's notes</summary>"
            f'<p>{_e(song["translator_notes"])}</p></details>'
        )
    sections = "\n".join(_version_section(i, v, song) for i, v in enumerate(versions))
    also = ""
    if song.get("aliases"):
        also = f'<p class="also-known">Also known as: {_e(", ".join(song["aliases"]))}</p>'
    body = f"""<article class="song" data-song-id="{song['id']}">
<p class="eyebrow">Песна {song['id']}</p>
<h1 lang="mk">{_e(song['title_cyr'])}</h1>
<p class="subtitle">{_e(song['title_latin'])} &middot; {_e(song['title_en'])}</p>
{also}
<div class="song-layout">
<aside class="song-side">
{render_player(song['id'], video, search_url(song))}
{render_feedback_form(song['id'], song['title_cyr'], config.FORM_KEY)}
</aside>
<div class="song-main">
{about}
{_toolbar(song)}
{_tabs(versions) if multi else ''}
{sections}
{notes}
<section class="listen"><h2>Listen</h2>
{_listen(song)}
</section>
</div>
</div>
<p class="attribution">{_e(config.ATTRIBUTION)} <a href="{_e(song['pesna_url'])}">View on Pesna.org</a></p>
</article>"""
    title = f"{song['title_cyr']} ({song['title_latin']}) - {config.SITE_TITLE}"
    return layout.page(title, body, active="songs")
