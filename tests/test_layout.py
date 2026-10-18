import unittest
from unittest import mock

import support  # noqa: F401
import config
import layout


class LayoutTests(unittest.TestCase):
    def test_title_is_escaped_and_border_appears_twice(self):
        html = layout.page("A & B", "<p>x</p>")
        self.assertIn("<title>A &amp; B", html)
        self.assertEqual(html.count('class="border"'), 2)

    def test_nav_links_use_base_path(self):
        with mock.patch.object(config, "BASE_PATH", "/x"):
            html = layout.page("T", "<p>x</p>")
        self.assertIn('href="/x/songs/"', html)
        self.assertIn('href="/x/alphabet/"', html)
        self.assertIn('href="/x/progress/"', html)
        self.assertIn('href="/x/about/"', html)
        self.assertIn('href="/x/static/style.css"', html)

    def test_site_is_called_ajde(self):
        self.assertEqual(config.SITE_TITLE, "Ајде")
        self.assertEqual(config.SITE_TAGLINE, "Ajde: learn Macedonian through its songs")

    def test_header_shows_the_name_and_tagline(self):
        html = layout.page("T", "<p>x</p>")
        self.assertIn('<a class="site-title" href="/" lang="mk">Ајде</a>', html)
        self.assertIn("Ajde: learn Macedonian through its songs", html)

    def test_there_is_no_footer(self):
        html = layout.page("T", "<p>x</p>")
        self.assertNotIn("<footer", html)
        self.assertNotIn("site-footer", html)
        self.assertNotIn("relearning Macedonian", html)
        self.assertNotIn("made with love", html)

    def test_page_still_ends_with_the_closing_border_and_scripts(self):
        html = layout.page("T", "<p>x</p>")
        self.assertEqual(html.count('class="border"'), 2)
        self.assertIn("</main>", html)
        self.assertLess(html.index("</main>"), html.rindex('class="border"'))
        self.assertIn("static/app.js", html)

    def test_active_nav_item_is_marked(self):
        html = layout.page("T", "<p>x</p>", active="songs")
        self.assertIn('aria-current="page"', html)

    def test_body_is_not_escaped(self):
        html = layout.page("T", "<p>hello</p>")
        self.assertIn("<p>hello</p>", html)


if __name__ == "__main__":
    unittest.main()
