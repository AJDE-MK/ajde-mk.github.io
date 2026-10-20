import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

import support  # noqa: F401
import build_site
import config
import render_pages
from test_render_song import make_song
import render_song

EM, EN = "—", "–"


class RefCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if key in a and a[key]:
                self.refs.append(a[key])


def check_links(out_dir, base):
    """Return a list of broken internal references in every page under out_dir."""
    out = Path(out_dir)
    broken = []
    for page in out.rglob("*.html"):
        parser = RefCollector()
        parser.feed(page.read_text(encoding="utf-8"))
        for ref in parser.refs:
            if ref.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if ref.startswith("#"):
                if ref[1:] not in parser.ids:
                    broken.append((page.name, ref))
                continue
            if not ref.startswith("/"):
                broken.append((str(page.relative_to(out)), f"relative link {ref}"))
                continue
            path = ref.split("#")[0].split("?")[0]
            if base and not path.startswith(base + "/"):
                broken.append((str(page.relative_to(out)), f"missing base path {ref}"))
                continue
            rel = path[len(base):].lstrip("/")
            target = out / rel
            if path.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                broken.append((str(page.relative_to(out)), ref))
    return broken


class FullBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.code = build_site.main(["--out", cls.tmp.name])
        cls.out = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_build_succeeds(self):
        self.assertEqual(self.code, 0)

    def test_every_song_has_a_page(self):
        pages = list((self.out / "songs").glob("*/index.html"))
        self.assertEqual(len(pages), 1598)

    def test_top_level_pages_exist(self):
        for rel in ("index.html", "songs/index.html", "alphabet/index.html", "progress/index.html",
                    "about/index.html", "needs-video/index.html", "review/index.html", "static/review.js", "404.html", "search-index.json", ".nojekyll", "static/style.css", "static/app.js",
                    "static/progress.js", "static/feedback.js", "static/quiz.js", "static/search.js"):
            self.assertTrue((self.out / rel).exists(), rel)

    def test_search_index_has_every_song(self):
        idx = json.loads((self.out / "search-index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(idx), 1598)

    def test_all_internal_links_resolve_at_the_site_root(self):
        self.assertEqual(check_links(self.out, ""), [])

    def test_site_authored_pages_and_assets_have_no_long_dashes(self):
        texts = [
            render_pages.render_home([]),
            render_pages.render_alphabet(),
            render_pages.render_progress(),
            render_song.render_song_page(make_song(), None),
        ]
        for f in (self.out / "static").iterdir():
            texts.append(f.read_text(encoding="utf-8"))
        for t in texts:
            self.assertNotIn(EM, t)
            self.assertNotIn(EN, t)


class BasePathBuildTests(unittest.TestCase):
    def test_all_internal_links_resolve_under_a_sub_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "BASE_PATH", "/some-name"):
                self.assertEqual(build_site.main(["--out", tmp]), 0)
            self.assertEqual(check_links(tmp, "/some-name"), [])


class BadVideosFailTheBuildTests(unittest.TestCase):
    def test_bad_video_entry_fails_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "videos.json"
            bad.write_text(json.dumps({"450": {"id": "short"}}), encoding="utf-8")
            with mock.patch.object(config, "VIDEOS_FILE", bad):
                code = build_site.main(["--out", str(Path(tmp) / "out")])
            self.assertEqual(code, 1)

    def test_good_video_shows_up_in_its_song_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            vids = Path(tmp) / "videos.json"
            vids.write_text(json.dumps({"450": {"id": "dQw4w9WgXcQ", "start": 0}}), encoding="utf-8")
            with mock.patch.object(config, "VIDEOS_FILE", vids):
                self.assertEqual(build_site.main(["--out", str(Path(tmp) / "out")]), 0)
            page = next((Path(tmp) / "out" / "songs").glob("0450-*/index.html"))
            self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
