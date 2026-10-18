import unittest
from unittest import mock

import support  # noqa: F401
import config
import render_song

ATTRIBUTION = "Lyrics: Pesna.org (folk lyrics in the public domain; site content CC BY)."


def make_song(versions=None, background="", song_id=450):
    versions = versions or [
        {
            "label": "",
            "en_source": "pesna",
            "stanzas": [{"lines": [{"cyr": "Илјада", "lat": "Iljada", "en": "One thousand"}]}],
        }
    ]
    return {
        "id": song_id,
        "slug": "1762-leto",
        "title_cyr": "1762 лето",
        "title_latin": "1762 leto",
        "title_en": "Year 1762",
        "pesna_url": "https://pesna.org/song/450",
        "background": background,
        "background_source": "Source of these notes: Qwen's draft.",
        "english_kind": "pesna",
        "en_note": "",
        "translator_notes": "",
        "words_to_learn": [],
        "performers": ["Мизар"],
        "audio": [{"who": "Мизар", "url": "https://pesna.org/audio-download/27"}],
        "versions": versions,
        "pending_english": False,
    }


def one_line_version(cyr, lat, en, source="pesna", mt=False, label=""):
    line = {"cyr": cyr, "lat": lat, "en": en}
    if mt:
        line["en_mt"] = True
    return {"label": label, "en_source": source, "stanzas": [{"lines": [line]}]}


class VideoColumnTests(unittest.TestCase):
    VIDEO = {"id": "dQw4w9WgXcQ", "start": 0}

    def test_video_and_feedback_sit_in_a_side_column_before_the_lyrics(self):
        html = render_song.render_song_page(make_song(background="A ballad."), self.VIDEO)
        side, main = html.index('class="song-side"'), html.index('class="song-main"')
        self.assertLess(side, main)
        self.assertGreater(html.index("<iframe"), side)
        self.assertLess(html.index("<iframe"), main)
        self.assertGreater(html.index('<table class="lyrics">'), main)
        self.assertGreater(html.index("data-learned-button"), main)
        self.assertGreater(html.index("About this song"), main)

    def test_song_without_video_still_has_both_columns(self):
        html = render_song.render_song_page(make_song(), None)
        self.assertIn('class="song-side"', html)
        self.assertIn('class="song-main"', html)
        self.assertIn("No video for this song yet.", html)
        self.assertLess(html.index("No video for this song yet."), html.index('class="song-main"'))

    def test_css_puts_the_video_in_a_sticky_left_column_on_wide_screens(self):
        css = (support.SITE_TOOLS / "static" / "style.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"@media \(min-width: 900px\)\s*\{[^@]*\.song-layout\s*\{[^}]*grid-template-columns")
        self.assertRegex(css, r"\.song-side\s*\{[^}]*position:\s*sticky")
        self.assertNotRegex(css, r"\.player:not\(\.no-video\)\s*\{[^}]*position:\s*sticky")


class CssTests(unittest.TestCase):
    def test_base_font_size_respects_the_browser_setting(self):
        import re

        css = (support.SITE_TOOLS / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"html\s*\{[^}]*font-size:\s*\d+px", css))


class RenderSongTests(unittest.TestCase):
    def test_lyric_text_is_escaped(self):
        song = make_song([one_line_version("a & <b> 'q'", "a & <b> 'q'", "a & <b> 'q'")])
        html = render_song.render_song_page(song, None)
        self.assertIn("a &amp; &lt;b&gt; &#x27;q&#x27;", html)
        self.assertNotIn("<b>", html)

    def test_three_versions_get_three_tabs_with_own_labels(self):
        song = make_song(
            [
                one_line_version("а", "a", "a", source="pesna", label="Version 1"),
                one_line_version("б", "b", "b", source="mt", label="Version 2"),
                one_line_version("в", "v", "v", source="mixed", label="Version 3"),
            ]
        )
        html = render_song.render_song_page(song, None)
        for i in (0, 1, 2):
            self.assertIn(f'data-version="{i}"', html)
            self.assertIn(f'data-tab="{i}"', html)
        self.assertIn("English: from Pesna.org", html)
        self.assertIn("English: machine translation, not checked by a native speaker", html)
        self.assertIn("English: partly from Pesna.org, partly machine translation (marked)", html)

    def test_single_version_has_no_tabs(self):
        html = render_song.render_song_page(make_song(), None)
        self.assertNotIn("data-tab=", html)

    def test_attribution_once_and_pesna_link(self):
        html = render_song.render_song_page(make_song(), None)
        self.assertEqual(html.count(ATTRIBUTION), 1)
        self.assertIn('href="https://pesna.org/song/450"', html)

    def test_background_block_only_when_present(self):
        with_bg = render_song.render_song_page(make_song(background="A rare ballad."), None)
        without = render_song.render_song_page(make_song(), None)
        self.assertIn("About this song", with_bg)
        self.assertIn("A rare ballad.", with_bg)
        self.assertNotIn("About this song", without)

    def test_three_column_toggles_exist(self):
        html = render_song.render_song_page(make_song(), None)
        for col in ("cyr", "lat", "en"):
            self.assertIn(f'data-col="{col}"', html)

    def test_machine_written_line_is_marked(self):
        song = make_song([one_line_version("а", "a", "mine", source="mixed", mt=True)])
        html = render_song.render_song_page(song, None)
        self.assertIn("mt-line", html)

    def test_pesna_translator_credit_is_shown(self):
        song = make_song()
        song["en_note"] = "From Pesna.org (translation: Jutta Malzbender)"
        html = render_song.render_song_page(song, None)
        self.assertIn("translation: Jutta Malzbender", html)

    def test_credit_not_shown_for_machine_translated_songs(self):
        song = make_song([one_line_version("а", "a", "x", source="mt")])
        song["english_kind"] = "mt"
        song["en_note"] = "Machine translation by Claude (my reading), not on Pesna.org"
        html = render_song.render_song_page(song, None)
        self.assertEqual(html.count("Machine translation by Claude"), 0)

    def test_mixed_version_explains_the_marked_lines(self):
        song = make_song([one_line_version("а", "a", "x", source="mixed", mt=True)])
        html = render_song.render_song_page(song, None)
        self.assertIn("Lines with a blue bar on the left are machine translation.", html)
        plain = render_song.render_song_page(make_song(), None)
        self.assertNotIn("blue bar", plain)

    def test_markdown_emphasis_in_background_becomes_italics_and_stays_safe(self):
        html = render_song.render_song_page(
            make_song(background="*Чупи* is a word. <script>x</script> 2 * 3"), None
        )
        self.assertIn("<em>Чупи</em>", html)
        self.assertNotIn("<script>x", html)
        self.assertNotIn("*Чупи*", html)
        self.assertIn("2 * 3", html)

    def test_background_source_says_notes_are_unchecked(self):
        html = render_song.render_song_page(make_song(background="A ballad."), None)
        self.assertIn("not been checked by a native speaker", html)

    def test_aliases_are_shown_as_also_known_as(self):
        song = make_song()
        song["aliases"] = ["Зајко", "Zajko"]
        html = render_song.render_song_page(song, None)
        self.assertIn("Also known as: Зајко, Zajko", html)
        self.assertNotIn("Also known as", render_song.render_song_page(make_song(), None))

    def test_marker_rule_is_not_overridden_by_the_phone_reset(self):
        css = (support.SITE_TOOLS / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIn("table.lyrics td.mt-line", css)

    def test_song_url_uses_base_path_and_zero_padded_id(self):
        song = make_song(song_id=7)
        with mock.patch.object(config, "BASE_PATH", "/x"):
            self.assertEqual(render_song.song_url(song), "/x/songs/0007-1762-leto/")

    def test_mark_learned_button_carries_song_id(self):
        html = render_song.render_song_page(make_song(), None)
        self.assertIn('data-learned-button data-song-id="450"', html)


if __name__ == "__main__":
    unittest.main()
