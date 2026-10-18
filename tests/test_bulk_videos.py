import json
import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
import bulk_videos as bv


def song(song_id, cyr, lat, performers=()):
    return {"id": song_id, "title_cyr": cyr, "title_latin": lat, "performers": list(performers), "audio": []}


def result(vid, title, views=1000, seconds=200, channel="Chan"):
    return {"id": vid, "title": title, "channel": channel, "views": views, "seconds": seconds}


LONG = song(10, "Зајди, зајди јасно сонце", "Zajdi, zajdi jasno sonce")
SHORT = song(20, "Македонија", "Makedonija")


class ProcessSongTests(unittest.TestCase):
    def run_process(self, s, results, used=(), embeddable=lambda vid: True):
        return bv.process_song(s, search=lambda q: results, embeddable=embeddable, used_ids=set(used))

    def test_exact_long_title_is_added_with_the_most_viewed_match(self):
        res = [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce - Macedonian Song", 500),
               result("BBBBBBBBBBB", "Zajdi zajdi jasno sonce - live", 9000),
               result("CCCCCCCCCCC", "Another song", 99999)]
        out = self.run_process(LONG, res)
        self.assertEqual(out["status"], "added")
        self.assertEqual(out["video"]["id"], "BBBBBBBBBBB")

    def test_short_titles_are_held_for_review_not_added(self):
        out = self.run_process(SHORT, [result("AAAAAAAAAAA", "Makedonija - Some Singer", 5000)])
        self.assertEqual(out["status"], "review")
        self.assertEqual(out["video"]["id"], "AAAAAAAAAAA")

    def test_no_match_gives_none(self):
        out = self.run_process(LONG, [result("AAAAAAAAAAA", "Something else entirely")])
        self.assertEqual(out["status"], "none")
        self.assertIsNone(out["video"])

    def test_used_video_ids_are_skipped(self):
        res = [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce", 900), result("BBBBBBBBBBB", "Zajdi zajdi jasno sonce", 5)]
        out = self.run_process(LONG, res, used={"AAAAAAAAAAA"})
        self.assertEqual(out["video"]["id"], "BBBBBBBBBBB")

    def test_videos_that_cannot_be_embedded_are_skipped(self):
        res = [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce", 900), result("BBBBBBBBBBB", "Zajdi zajdi jasno sonce", 5)]
        out = self.run_process(LONG, res, embeddable=lambda vid: vid != "AAAAAAAAAAA")
        self.assertEqual(out["video"]["id"], "BBBBBBBBBBB")

    def test_instrumentals_and_long_videos_are_skipped(self):
        res = [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce - Instrumental (Karaoke)", 900),
               result("BBBBBBBBBBB", "Zajdi zajdi jasno sonce - 2 hour mix", 900, seconds=7200)]
        self.assertEqual(self.run_process(LONG, res)["status"], "none")

    def test_videos_with_fewer_than_300_views_are_held_for_review(self):
        out = self.run_process(LONG, [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce", views=52)])
        self.assertEqual(out["status"], "review")
        out = self.run_process(LONG, [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce", views=300)])
        self.assertEqual(out["status"], "added")

    def test_instrument_only_titles_are_skipped(self):
        res = [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce (for piano)", 9000),
               result("BBBBBBBBBBB", "Zajdi zajdi jasno sonce - guitar tutorial", 9000)]
        self.assertEqual(self.run_process(LONG, res)["status"], "none")

    def test_a_failing_search_is_reported_as_error_not_a_crash(self):
        def boom(q):
            raise OSError("network down")

        out = bv.process_song(LONG, search=boom, embeddable=lambda v: True, used_ids=set())
        self.assertEqual(out["status"], "error")
        self.assertIn("network down", out["error"])

    def test_two_queries_are_tried_and_results_are_merged(self):
        seen = []

        def search(q):
            seen.append(q)
            return [result("AAAAAAAAAAA", "Zajdi zajdi jasno sonce")] if "Zajdi" in q else []

        out = bv.process_song(LONG, search=search, embeddable=lambda v: True, used_ids=set())
        self.assertEqual(out["status"], "added")
        self.assertEqual(len(seen), 2)


class ShortTitleTests(unittest.TestCase):
    def test_two_word_titles_or_fewer_need_review(self):
        self.assertTrue(bv.is_short_title(SHORT))
        self.assertTrue(bv.is_short_title(song(1, "Невесто лична", "Nevesto lična")))
        self.assertFalse(bv.is_short_title(LONG))


class ProgressTests(unittest.TestCase):
    def test_progress_round_trips_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.json"
            self.assertEqual(bv.load_progress(path), {"done": [], "added": {}, "review": {}, "none": [], "error": {}})
            p = bv.load_progress(path)
            bv.record(p, {"status": "added", "song_id": 10, "video": result("AAAAAAAAAAA", "T", 5)})
            bv.record(p, {"status": "review", "song_id": 20, "video": result("BBBBBBBBBBB", "T2", 7)})
            bv.record(p, {"status": "none", "song_id": 30, "video": None})
            bv.record(p, {"status": "error", "song_id": 40, "video": None, "error": "boom"})
            bv.save_progress(path, p)
            again = bv.load_progress(path)
            self.assertEqual(sorted(again["done"]), [10, 20, 30, 40])
            self.assertEqual(again["added"]["10"]["id"], "AAAAAAAAAAA")
            self.assertEqual(again["review"]["20"]["id"], "BBBBBBBBBBB")
            self.assertEqual(again["none"], [30])
            self.assertEqual(again["error"]["40"], "boom")

    def test_errors_are_retried_on_the_next_run_but_other_results_are_not(self):
        p = {"done": [10, 20, 40], "added": {"10": {}}, "review": {}, "none": [], "error": {"40": "boom"}}
        todo = bv.songs_to_search([song(10, "a", "a"), song(20, "b", "b"), song(40, "c", "c"), song(50, "d", "d")], p, {})
        self.assertEqual([s["id"] for s in todo], [40, 50])

    def test_songs_that_already_have_a_video_are_not_searched(self):
        p = {"done": [], "added": {}, "review": {}, "none": [], "error": {}}
        todo = bv.songs_to_search([song(10, "a", "a"), song(20, "b", "b")], p, {10: {"id": "AAAAAAAAAAA"}})
        self.assertEqual([s["id"] for s in todo], [20])


if __name__ == "__main__":
    unittest.main()
