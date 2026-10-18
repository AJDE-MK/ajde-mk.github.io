import unittest

import support  # noqa: F401
import render_pages

BOOK = "https://www.amazon.com/dp/B08N3PJH7K"


class AboutPageTests(unittest.TestCase):
    def setUp(self):
        self.html = render_pages.render_about()

    def test_credits_the_book_and_its_author(self):
        self.assertIn("Em Baba, Em Nevesta", self.html)
        self.assertIn("Dr. Kathy Dimitrievski", self.html)
        self.assertIn("The history and culture of Macedonia told through its folk songs", self.html)

    def test_says_it_is_inspired_by_the_book_and_a_separate_project(self):
        self.assertIn("inspired by", self.html)
        self.assertIn("separate project", self.html)
        self.assertNotIn("companion", self.html.lower())

    def test_names_the_maker_as_her_son(self):
        self.assertIn("Michael Dimitrievski", self.html)
        self.assertIn("her son", self.html)

    def test_buy_link_is_the_clean_amazon_address_without_tracking(self):
        self.assertIn(f'href="{BOOK}"', self.html)
        for junk in ("crid=", "dib=", "qid=", "sprefix=", "keywords="):
            self.assertNotIn(junk, self.html)
        self.assertIn('rel="noopener"', self.html)

    def test_title_meaning_is_given(self):
        self.assertIn("both a grandmother and a young bride", self.html)

    def test_explains_where_the_words_come_from_and_what_is_machine_made(self):
        self.assertIn("Pesna.org", self.html)
        self.assertIn("machine translation", self.html)
        self.assertIn("not checked by a native speaker", self.html)

    def test_page_is_marked_active_in_the_menu(self):
        self.assertIn('aria-current="page">About', self.html)

    def test_no_long_dashes_were_typed(self):
        self.assertNotIn("—", self.html)
        self.assertNotIn("–", self.html)


if __name__ == "__main__":
    unittest.main()
