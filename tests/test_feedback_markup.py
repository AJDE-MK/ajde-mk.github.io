import unittest
from unittest import mock

import support  # noqa: F401
import config
import feedback
import render_song
from test_render_song import make_song


class FeedbackMarkupTests(unittest.TestCase):
    def test_no_key_shows_coming_soon_and_no_form(self):
        html = feedback.render_feedback_form(450, "1762 лето", "")
        self.assertIn("Feedback form coming soon", html)
        self.assertNotIn("<form", html)

    def test_with_key_has_every_field(self):
        html = feedback.render_feedback_form(450, "1762 лето", "KEY123")
        self.assertIn('action="https://api.web3forms.com/submit"', html)
        self.assertIn('name="access_key" value="KEY123"', html)
        self.assertIn('name="subject" value="Feedback for song 450: 1762 лето"', html)
        self.assertIn('name="botcheck"', html)
        self.assertIn('name="url"', html)
        self.assertIn('name="note"', html)
        self.assertIn('name="song_id" value="450"', html)

    def test_form_lets_people_report_words_mistakes_too(self):
        html = feedback.render_feedback_form(450, "t", "KEY")
        self.assertIn('<select name="kind"', html)
        for value in ("video", "words", "other"):
            self.assertIn(f'<option value="{value}"', html)
        self.assertIn("mistake in the words", html)

    def test_steps_are_written_in_plain_words(self):
        html = feedback.render_feedback_form(450, "t", "KEY")
        self.assertIn("Open YouTube", html)
        self.assertIn("Copy the web address", html)
        self.assertIn("Paste it here", html)

    def test_title_is_escaped(self):
        html = feedback.render_feedback_form(450, 'a "b" <i>', "KEY")
        self.assertNotIn("<i>", html)
        self.assertIn("&quot;b&quot;", html)

    def test_honeypot_is_hidden_from_people(self):
        html = feedback.render_feedback_form(450, "t", "KEY")
        self.assertIn('class="botcheck"', html)
        self.assertIn('tabindex="-1"', html)
        self.assertIn('autocomplete="off"', html)

    def test_song_page_has_the_wrong_video_prompt(self):
        with mock.patch.object(config, "FORM_KEY", ""):
            page = render_song.render_song_page(make_song(), None)
        self.assertIn("Wrong or missing video? Tell us", page)
        self.assertIn("Feedback form coming soon", page)
        with mock.patch.object(config, "FORM_KEY", "KEY123"):
            page = render_song.render_song_page(make_song(), None)
        self.assertIn('name="access_key" value="KEY123"', page)


if __name__ == "__main__":
    unittest.main()
