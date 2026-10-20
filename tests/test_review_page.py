import unittest

import support  # noqa: F401
import render_pages


def row(song_id, cyr="Белите манастири", lat="Belite manastiri", en="The white monasteries", vid="5UB7oS7JMqE",
        title="GLORIA - BELITE MANASTIRI", channel="PlanetaOfficial", views=10672804, note=None):
    video = {"id": vid, "title": title, "channel": channel, "views": views, "seconds": 200}
    if note:
        video["note"] = note
    song = {
        "id": song_id, "slug": f"s{song_id}", "title_cyr": cyr, "title_latin": lat, "title_en": en,
        "versions": [{"stanzas": [{"lines": [{"cyr": "Прва линија", "lat": "a", "en": "b"},
                                             {"cyr": "Втора линија", "lat": "a", "en": "b"},
                                             {"cyr": "Трета линија", "lat": "a", "en": "b"},
                                             {"cyr": "Четврта линија", "lat": "a", "en": "b"},
                                             {"cyr": "Петта линија", "lat": "a", "en": "b"}]}]}],
    }
    return {"song_id": song_id, "song": song, "video": video}


class ReviewPageTests(unittest.TestCase):
    def setUp(self):
        self.html = render_pages.render_review([row(917)], "KEY123")

    def test_explains_the_task_in_plain_words(self):
        self.assertIn("Please help by reviewing these", self.html)
        self.assertIn("Listen to the video", self.html)
        self.assertIn("same song", self.html)

    def test_each_row_shows_song_lyric_peek_and_video_link(self):
        self.assertIn("Белите манастири", self.html)
        self.assertIn("The white monasteries", self.html)
        self.assertIn("Прва линија", self.html)
        self.assertIn("Четврта линија", self.html)
        self.assertNotIn("Петта линија", self.html)
        self.assertIn('href="https://www.youtube.com/watch?v=5UB7oS7JMqE"', self.html)
        self.assertIn("GLORIA - BELITE MANASTIRI", self.html)
        self.assertIn('href="/songs/0917-s917/"', self.html)

    def test_each_row_has_yes_no_and_not_sure_choices_defaulting_to_not_sure(self):
        for value in ("yes", "no", "skip"):
            self.assertIn(f'name="vote-917" value="{value}"', self.html)
        self.assertRegex(self.html, r'value="skip"[^>]*checked')

    def test_rows_carry_ids_for_the_script(self):
        self.assertIn('data-song-id="917"', self.html)
        self.assertIn('data-video-id="5UB7oS7JMqE"', self.html)

    def test_send_button_and_key_are_present_with_a_key(self):
        self.assertIn("data-review-send", self.html)
        self.assertIn('data-access-key="KEY123"', self.html)
        self.assertIn("review.js", self.html)

    def test_without_a_key_it_says_sending_is_coming_soon(self):
        html = render_pages.render_review([row(917)], "")
        self.assertIn("coming soon", html)
        self.assertNotIn("data-review-send", html)

    def test_a_note_is_shown_when_the_video_may_fit_another_song(self):
        html = render_pages.render_review([row(590, note="also fits song 589 better")], "K")
        self.assertIn("also fits song 589 better", html)

    def test_count_is_shown(self):
        html = render_pages.render_review([row(1), row(2), row(3)], "K")
        self.assertIn("3 videos", html)
        self.assertIn("1 video ", render_pages.render_review([row(1)], "K"))

    def test_empty_list_says_thanks(self):
        html = render_pages.render_review([], "K")
        self.assertIn("Nothing is waiting for review", html)
        self.assertNotIn("data-review-send", html)

    def test_text_is_escaped(self):
        html = render_pages.render_review([row(5, cyr="Ај <b>", title="Evil <script>x</script>", channel="A&B")], "K")
        self.assertNotIn("<script>x", html)
        self.assertNotIn("<b>", html)
        self.assertIn("A&amp;B", html)

    def test_no_long_dashes_in_the_page_text(self):
        self.assertNotIn("—", self.html)
        self.assertNotIn("–", self.html)

    def test_page_is_marked_active_in_the_menu(self):
        self.assertIn('aria-current="page">Review videos', self.html)
        self.assertIn('aria-current="page">Review videos', render_pages.render_review([], "K"))


class HelpLinksTests(unittest.TestCase):
    def test_home_and_needs_video_pages_point_to_the_review_page_when_there_is_something_to_review(self):
        songs = [{"id": 1, "slug": "s1", "title_cyr": "А", "title_latin": "A", "title_en": "A"}]
        home = render_pages.render_home(songs, {}, review_count=5)
        self.assertIn('href="/review/"', home)
        self.assertIn("5 videos", home)
        needs = render_pages.render_needs_video(songs, {}, review_count=5)
        self.assertIn('href="/review/"', needs)

    def test_no_link_when_nothing_to_review(self):
        songs = [{"id": 1, "slug": "s1", "title_cyr": "А", "title_latin": "A", "title_en": "A"}]
        self.assertNotIn("Help by reviewing", render_pages.render_home(songs, {}, review_count=0))
        self.assertNotIn("Help by reviewing", render_pages.render_needs_video(songs, {}, review_count=0))


if __name__ == "__main__":
    unittest.main()
