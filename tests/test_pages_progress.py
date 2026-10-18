import unittest

import support  # noqa: F401
import render_pages


class ProgressPageTests(unittest.TestCase):
    def test_has_export_import_and_status_hooks(self):
        html = render_pages.render_progress()
        for hook in ("data-progress-page", "data-export", "data-import", "data-progress-status", "data-progress-summary"):
            self.assertIn(hook, html)
        self.assertIn('type="file"', html)

    def test_explains_where_progress_lives_in_plain_words(self):
        html = render_pages.render_progress()
        self.assertIn("saved in this browser", html)
        self.assertIn("clear your browser", html.lower())
        self.assertIn("Export", html)
        self.assertIn("Import", html)

    def test_import_file_input_is_visible_so_keyboard_users_can_reach_it(self):
        html = render_pages.render_progress()
        tag = html[html.index("<input type=\"file\""):]
        tag = tag[: tag.index(">") + 1]
        self.assertNotIn("hidden", tag)

    def test_page_is_marked_active(self):
        html = render_pages.render_progress()
        self.assertIn('aria-current="page">My progress', html)


if __name__ == "__main__":
    unittest.main()
