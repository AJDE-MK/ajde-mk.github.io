import unittest
from unittest import mock

import support  # noqa: F401
import alphabet
import config
import render_pages

ORDER = "а б в г д ѓ е ж з ѕ и ј к л љ м н њ о п р с т ќ у ф х ц ч џ ш".split()
SPECIAL = set("ѓ ќ ѕ љ њ џ".split())


class AlphabetDataTests(unittest.TestCase):
    def setUp(self):
        self.letters = alphabet.load_letters()

    def test_there_are_31_letters_in_the_standard_order(self):
        self.assertEqual(len(self.letters), 31)
        self.assertEqual([l["lower"] for l in self.letters], ORDER)

    def test_upper_matches_lower(self):
        for l in self.letters:
            self.assertEqual(l["upper"].lower(), l["lower"])

    def test_special_letters_are_exactly_the_six(self):
        flagged = {l["lower"] for l in self.letters if l["special"]}
        self.assertEqual(flagged, SPECIAL)

    def test_every_letter_has_its_teaching_fields(self):
        for l in self.letters:
            for field in ("latin", "hint", "word_cyr", "word_lat", "word_en"):
                self.assertTrue(l[field].strip(), f"{l['lower']} missing {field}")

    def test_sample_word_starts_with_the_letter(self):
        for l in self.letters:
            self.assertTrue(l["word_cyr"].lower().startswith(l["lower"]), l["lower"])

    def test_latin_values_are_all_different(self):
        latin = [l["latin"] for l in self.letters]
        self.assertEqual(len(latin), len(set(latin)))

    def test_audio_slot_exists_and_is_empty_at_launch(self):
        for l in self.letters:
            self.assertIn("audio", l)
            self.assertIsNone(l["audio"])

    def test_each_sample_word_has_its_own_empty_audio_slot(self):
        for l in self.letters:
            self.assertIn("word_audio", l)
            self.assertIsNone(l["word_audio"])

    def test_latin_follows_the_songbook_romanization(self):
        by_lower = {l["lower"]: l["latin"] for l in self.letters}
        self.assertEqual(by_lower["ѓ"], "ǵ")
        self.assertEqual(by_lower["ќ"], "ḱ")
        self.assertEqual(by_lower["ѕ"], "dz")
        self.assertEqual(by_lower["љ"], "lj")
        self.assertEqual(by_lower["њ"], "nj")
        self.assertEqual(by_lower["џ"], "dž")


class AlphabetPageTests(unittest.TestCase):
    def test_page_has_review_label_and_every_letter(self):
        html = render_pages.render_alphabet()
        self.assertIn("Sound hints and sample words are not yet checked by a Macedonian speaker.", html)
        for l in alphabet.load_letters():
            self.assertIn(f'data-letter="{l["lower"]}"', html)
        self.assertIn("data-quiz", html)

    def test_no_audio_element_when_no_recording(self):
        self.assertNotIn("<audio", render_pages.render_alphabet())

    def test_audio_element_appears_only_for_letters_with_a_recording(self):
        letters = alphabet.load_letters()
        letters[0] = dict(letters[0], audio="/audio/a.mp3")
        with mock.patch.object(alphabet, "load_letters", return_value=letters):
            html = render_pages.render_alphabet()
        self.assertEqual(html.count("<audio"), 1)
        self.assertIn("/audio/a.mp3", html)

    def test_word_audio_and_base_path_are_applied(self):
        letters = alphabet.load_letters()
        letters[0] = dict(letters[0], audio="/audio/a.mp3", word_audio="/audio/ajde.mp3")
        with mock.patch.object(alphabet, "load_letters", return_value=letters):
            with mock.patch.object(config, "BASE_PATH", "/x"):
                html = render_pages.render_alphabet()
        self.assertEqual(html.count("<audio"), 2)
        self.assertIn('src="/x/audio/a.mp3"', html)
        self.assertIn('src="/x/audio/ajde.mp3"', html)

    def test_special_letters_get_a_notice(self):
        html = render_pages.render_alphabet()
        self.assertEqual(html.count('class="special-note"'), 6)

    def test_page_marked_active(self):
        self.assertIn('aria-current="page">Alphabet', render_pages.render_alphabet())


if __name__ == "__main__":
    unittest.main()
