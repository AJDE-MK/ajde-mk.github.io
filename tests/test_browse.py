import re
import unittest

import support  # noqa: F401
import render_pages
import render_song
import songs


def fake(song_id, cyr, lat="x", en="y"):
    return {"id": song_id, "slug": f"s{song_id}", "title_cyr": cyr, "title_latin": lat, "title_en": en}


class SearchIndexTests(unittest.TestCase):
    def test_index_entries_have_the_needed_fields(self):
        idx = render_pages.build_search_index([fake(5, "Билбил", "Bilbil", "Nightingale")])
        self.assertEqual(idx, [{"id": 5, "cyr": "Билбил", "lat": "Bilbil", "en": "Nightingale",
                                "url": render_song.song_url(fake(5, "Билбил"))}])


    def test_aliases_go_into_the_index_as_alt(self):
        song = dict(fake(473, "Сторил ниет зајко"), aliases=["Зајко", "Zajko"])
        idx = render_pages.build_search_index([song])
        self.assertEqual(idx[0]["alt"], "Зајко Zajko")

    def test_songs_without_aliases_have_no_alt_key(self):
        self.assertNotIn("alt", render_pages.build_search_index([fake(5, "Билбил")])[0])


class BrowseTests(unittest.TestCase):
    def test_every_real_song_is_listed_exactly_once(self):
        all_songs = songs.load_songs()
        html = render_pages.render_browse(all_songs)
        for s in all_songs:
            self.assertEqual(html.count(f'href="{render_song.song_url(s)}"'), 1, s["id"])

    def test_songs_are_grouped_by_first_cyrillic_letter(self):
        html = render_pages.render_browse(
            [fake(1, "Билбил"), fake(2, "Абер"), fake(3, "Вино"), fake(4, "1762 лето"), fake(5, "Ајде")]
        )
        self.assertIn('id="letter-А"', html)
        self.assertIn('id="letter-Б"', html)
        self.assertIn('id="letter-В"', html)
        self.assertIn('id="letter-0-9"', html)
        self.assertLess(html.index('id="letter-0-9"'), html.index('id="letter-А"'))
        self.assertLess(html.index('id="letter-А"'), html.index('id="letter-Б"'))

    def test_jump_bar_links_to_each_group_present(self):
        html = render_pages.render_browse([fake(1, "Билбил"), fake(2, "Абер")])
        self.assertIn('href="#letter-А"', html)
        self.assertIn('href="#letter-Б"', html)
        self.assertNotIn('href="#letter-В"', html)

    def test_search_box_and_index_location(self):
        html = render_pages.render_browse([fake(1, "Билбил")])
        self.assertIn("data-search", html)
        self.assertIn('data-search-index="/search-index.json"', html)

    def test_title_text_is_escaped(self):
        html = render_pages.render_browse([fake(1, "Ај <b> & ти", "Aj <b>", "x")])
        self.assertNotIn("<b>", html)

    def test_page_is_marked_active(self):
        self.assertIn('aria-current="page">Songs', render_pages.render_browse([fake(1, "Билбил")]))


class HomeTests(unittest.TestCase):
    def test_home_links_to_alphabet_and_songs_and_shows_count(self):
        html = render_pages.render_home([fake(i, "Билбил") for i in range(3)])
        self.assertIn('href="/alphabet/"', html)
        self.assertIn('href="/songs/"', html)
        self.assertIn("3 songs", html)

    def test_page_is_marked_active(self):
        self.assertIn('aria-current="page">Home', render_pages.render_home([fake(1, "Билбил")]))

    def test_home_page_title_is_the_site_name(self):
        self.assertIn("<title>Ајде", render_pages.render_home([fake(1, "Билбил")]))


if __name__ == "__main__":
    unittest.main()
