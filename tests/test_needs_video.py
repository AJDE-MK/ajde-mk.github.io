import unittest

import support  # noqa: F401
import render_pages


def fake(song_id, cyr, lat="x", en="y"):
    return {"id": song_id, "slug": f"s{song_id}", "title_cyr": cyr, "title_latin": lat, "title_en": en}


SONGS = [fake(1, "Билбил", "Bilbil", "Nightingale"), fake(2, "Абер", "Aber", "News"), fake(3, "Вино", "Vino", "Wine")]
VIDEOS = {2: {"id": "AAAAAAAAAAA", "start": 0}}


class NeedsVideoPageTests(unittest.TestCase):
    def setUp(self):
        self.html = render_pages.render_needs_video(SONGS, VIDEOS)

    def test_lists_only_songs_without_a_video(self):
        self.assertIn("Билбил", self.html)
        self.assertIn("Вино", self.html)
        self.assertNotIn("Абер", self.html)

    def test_shows_the_count_and_how_to_help(self):
        self.assertIn("2 songs", self.html)
        self.assertIn("Wrong or missing video? Tell us", self.html)
        self.assertIn("link to the YouTube video", self.html)

    def test_each_row_links_to_its_song_page_and_to_a_youtube_search(self):
        self.assertIn('href="/songs/0001-s1/"', self.html)
        self.assertIn("https://www.youtube.com/results?search_query=", self.html)

    def test_rows_are_grouped_by_first_cyrillic_letter_with_a_jump_bar(self):
        self.assertIn('id="letter-Б"', self.html)
        self.assertIn('id="letter-В"', self.html)
        self.assertIn('href="#letter-Б"', self.html)
        self.assertLess(self.html.index('id="letter-Б"'), self.html.index('id="letter-В"'))

    def test_when_every_song_has_a_video_it_says_so(self):
        html = render_pages.render_needs_video(SONGS, {1: {}, 2: {}, 3: {}})
        self.assertIn("Every song has a video", html)
        self.assertNotIn("<li>", html)

    def test_titles_are_escaped(self):
        html = render_pages.render_needs_video([fake(9, "Ај <b> & ти", "Aj <b>")], {})
        self.assertNotIn("<b>", html)

    def test_page_text_has_no_long_dashes(self):
        self.assertNotIn("—", self.html)
        self.assertNotIn("–", self.html)

    def test_singular_count(self):
        self.assertIn("1 song ", render_pages.render_needs_video(SONGS, {1: {}, 2: {}}))


class HomeHelpLineTests(unittest.TestCase):
    def test_home_page_invites_visitors_to_help_when_counts_are_known(self):
        html = render_pages.render_home(SONGS, VIDEOS)
        self.assertIn('href="/needs-video/"', html)
        self.assertIn("2 songs still have no video", html)

    def test_home_page_without_video_data_has_no_help_line(self):
        self.assertNotIn("needs-video", render_pages.render_home(SONGS))


class NoVideoBoxTests(unittest.TestCase):
    def test_the_empty_player_box_invites_a_suggestion(self):
        import render_song
        from test_render_song import make_song

        html = render_song.render_song_page(make_song(), None)
        self.assertIn("Know this song? Suggest a video in the box below.", html)


if __name__ == "__main__":
    unittest.main()
