import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
import build_site
import songs


class BuildSkeletonTests(unittest.TestCase):
    def test_build_writes_home_and_static_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = build_site.main(["--out", tmp, "--only-skeleton"])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "index.html").exists())
            self.assertTrue((Path(tmp) / "static" / "style.css").exists())

    def test_load_songs_returns_all_songs_sorted(self):
        all_songs = songs.load_songs()
        self.assertEqual(len(all_songs), 1598)
        ids = [s["id"] for s in all_songs]
        self.assertEqual(ids, sorted(ids))

    def test_load_videos_returns_dict_keyed_by_int(self):
        videos = songs.load_videos()
        self.assertIsInstance(videos, dict)
        for key in videos:
            self.assertIsInstance(key, int)


if __name__ == "__main__":
    unittest.main()
