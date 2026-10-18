import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support  # noqa: F401
import config
import render_song
import videos_tool

GOOD_ID = "dQw4w9WgXcQ"


class ParseTests(unittest.TestCase):
    def test_four_url_forms(self):
        for url in (
            f"https://youtu.be/{GOOD_ID}?t=5",
            f"https://www.youtube.com/watch?v={GOOD_ID}&list=abc",
            f"https://www.youtube.com/embed/{GOOD_ID}",
            f"https://www.youtube.com/shorts/{GOOD_ID}",
        ):
            self.assertEqual(videos_tool.parse_youtube_id(url), GOOD_ID, url)

    def test_non_youtube_url_gives_none(self):
        self.assertIsNone(videos_tool.parse_youtube_id("https://example.com/x"))
        self.assertIsNone(videos_tool.parse_youtube_id("hello"))


class ValidateTests(unittest.TestCase):
    def test_bad_id_is_reported(self):
        problems = videos_tool.validate_videos({"450": {"id": "short"}}, {450})
        self.assertEqual(len(problems), 1)
        self.assertIn("450", problems[0])

    def test_unknown_song_is_reported(self):
        problems = videos_tool.validate_videos({"9999": {"id": GOOD_ID}}, {450})
        self.assertEqual(len(problems), 1)
        self.assertIn("9999", problems[0])

    def test_duplicate_video_id_is_reported(self):
        problems = videos_tool.validate_videos(
            {"450": {"id": GOOD_ID}, "451": {"id": GOOD_ID}}, {450, 451}
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("used by more than one song", problems[0])

    def test_clean_list_has_no_problems(self):
        self.assertEqual(videos_tool.validate_videos({"450": {"id": GOOD_ID, "start": 3}}, {450}), [])

    def test_negative_start_is_reported(self):
        problems = videos_tool.validate_videos({"450": {"id": GOOD_ID, "start": -1}}, {450})
        self.assertEqual(len(problems), 1)


class SloppyFileTests(unittest.TestCase):
    def test_numeric_video_id_is_a_problem_not_a_crash(self):
        problems = videos_tool.validate_videos({"450": {"id": 12345678901}}, {450})
        self.assertEqual(len(problems), 1)

    def test_top_level_list_is_a_problem_not_a_crash(self):
        problems = videos_tool.validate_videos([], {450})
        self.assertEqual(len(problems), 1)
        self.assertIn("must be an object", problems[0])

    def test_entry_that_is_not_an_object_is_a_problem(self):
        self.assertEqual(len(videos_tool.validate_videos({"450": "dQw4w9WgXcQ"}, {450})), 1)


class AddVideoTests(unittest.TestCase):
    def test_add_video_writes_entry_with_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "videos.json"
            with mock.patch.object(config, "VIDEOS_FILE", target):
                videos_tool.add_video(450, f"https://youtu.be/{GOOD_ID}", start=12)
                videos_tool.add_video(451, f"https://youtu.be/AAAAAAAAAAA")
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data["450"], {"id": GOOD_ID, "start": 12})
            self.assertEqual(data["451"], {"id": "AAAAAAAAAAA", "start": 0})

    def test_add_video_rejects_bad_url_and_leaves_file_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "videos.json"
            with mock.patch.object(config, "VIDEOS_FILE", target):
                with self.assertRaises(ValueError):
                    videos_tool.add_video(450, "not a link")
            self.assertFalse(target.exists())


class PlayerTests(unittest.TestCase):
    def test_player_with_video(self):
        html = render_song.render_player(450, {"id": GOOD_ID, "start": 12}, "https://search")
        self.assertIn(f"youtube-nocookie.com/embed/{GOOD_ID}?start=12", html)
        self.assertIn('loading="lazy"', html)
        self.assertIn("Watch on YouTube", html)
        self.assertIn(f"https://www.youtube.com/watch?v={GOOD_ID}", html)

    def test_watch_link_keeps_the_start_time(self):
        with_start = render_song.render_player(450, {"id": GOOD_ID, "start": 12}, "u")
        self.assertIn(f"watch?v={GOOD_ID}&amp;t=12s", with_start)
        no_start = render_song.render_player(450, {"id": GOOD_ID, "start": 0}, "u")
        self.assertNotIn("t=0s", no_start)

    def test_player_without_video_has_no_iframe_and_keeps_search_link(self):
        html = render_song.render_player(450, None, "https://search")
        self.assertNotIn("<iframe", html)
        self.assertIn('href="https://search"', html)

    def test_song_page_includes_player_block(self):
        from test_render_song import make_song

        page = render_song.render_song_page(make_song(), {"id": GOOD_ID, "start": 0})
        self.assertIn("youtube-nocookie.com/embed/" + GOOD_ID, page)
        no_video = render_song.render_song_page(make_song(), None)
        self.assertNotIn("<iframe", no_video)


if __name__ == "__main__":
    unittest.main()
