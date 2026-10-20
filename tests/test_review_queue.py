import unittest

import support  # noqa: F401
import review_queue as rq


def song(song_id, cyr="Т", lat="T", en="E"):
    return {"id": song_id, "title_cyr": cyr, "title_latin": lat, "title_en": en}


def vid(vid_id, title="Video", views=100, channel="Chan"):
    return {"id": vid_id, "title": title, "views": views, "channel": channel, "seconds": 200}


SONGS = {i: song(i) for i in (1, 2, 3, 4)}
EMPTY = {"accepted": [], "rejected": []}


class QueueTests(unittest.TestCase):
    def test_rows_from_both_passes_are_sorted_by_views(self):
        p1 = {"review": {"1": vid("AAAAAAAAAAA", views=50), "2": vid("BBBBBBBBBBB", views=900)}}
        p2 = {"review": {"3": vid("CCCCCCCCCCC", views=300)}}
        q = rq.build_queue(p1, p2, SONGS, {}, EMPTY)
        self.assertEqual([r["song_id"] for r in q], [2, 3, 1])

    def test_a_song_in_both_passes_uses_the_second_pass_video(self):
        p1 = {"review": {"1": vid("AAAAAAAAAAA", views=50)}}
        p2 = {"review": {"1": vid("BBBBBBBBBBB", views=10)}}
        q = rq.build_queue(p1, p2, SONGS, {}, EMPTY)
        self.assertEqual(len(q), 1)
        self.assertEqual(q[0]["video"]["id"], "BBBBBBBBBBB")

    def test_songs_with_a_video_or_a_decision_are_left_out(self):
        p1 = {"review": {"1": vid("AAAAAAAAAAA"), "2": vid("BBBBBBBBBBB"), "3": vid("CCCCCCCCCCC"), "4": vid("DDDDDDDDDDD")}}
        q = rq.build_queue(p1, {"review": {}}, SONGS, {1: {"id": "ZZZZZZZZZZZ"}},
                           {"accepted": [2], "rejected": [3]})
        self.assertEqual([r["song_id"] for r in q], [4])

    def test_next_batch_takes_the_first_n(self):
        q = [{"song_id": i} for i in range(10)]
        self.assertEqual([r["song_id"] for r in rq.next_batch(q, 3)], [0, 1, 2])
        self.assertEqual(rq.next_batch([], 3), [])


class PageOrderTests(unittest.TestCase):
    def test_rows_carry_which_pass_found_them(self):
        p1 = {"review": {"1": vid("AAAAAAAAAAA")}}
        p2 = {"review": {"2": vid("BBBBBBBBBBB")}}
        q = rq.build_queue(p1, p2, SONGS, {}, EMPTY)
        self.assertEqual({r["song_id"]: r["source"] for r in q}, {1: "pass1", 2: "pass2"})

    def test_second_pass_rows_come_first_on_the_page_then_by_views(self):
        p1 = {"review": {"1": vid("AAAAAAAAAAA", views=9_000_000), "2": vid("BBBBBBBBBBB", views=100)}}
        p2 = {"review": {"3": vid("CCCCCCCCCCC", views=50), "4": vid("DDDDDDDDDDD", views=700)}}
        q = rq.build_queue(p1, p2, SONGS, {}, EMPTY)
        self.assertEqual([r["song_id"] for r in rq.page_order(q)], [4, 3, 1, 2])


class FormatTests(unittest.TestCase):
    def test_a_row_shows_song_video_channel_views_note_and_link(self):
        row = {"song_id": 590, "song": song(590, "Бог да бие мојта мајка", "Bog da bie mojta majka", "Hit my mother"),
               "video": dict(vid("AAAAAAAAAAA", "Bog da bie, Ruse, tvojta majka", 1063, "Biljana"),
                             note="also fits song 589 better")}
        text = rq.format_row(row)
        for part in ("590", "Бог да бие мојта мајка", "Bog da bie mojta majka", "Hit my mother",
                     "Bog da bie, Ruse, tvojta majka", "Biljana", "1,063", "also fits song 589 better",
                     "https://www.youtube.com/watch?v=AAAAAAAAAAA"):
            self.assertIn(part, text)


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.p1 = {"review": {"1": vid("AAAAAAAAAAA"), "2": vid("BBBBBBBBBBB"), "3": vid("BBBBBBBBBBB")}}
        self.queue = rq.build_queue(self.p1, {"review": {}}, SONGS, {}, EMPTY)
        self.added = []

    def add(self, song_id, url):
        self.added.append((song_id, url))

    def test_accepted_rows_are_added_and_recorded(self):
        d = {"accepted": [], "rejected": []}
        res = rq.apply_decisions(self.queue, [1], [], d, {}, self.add)
        self.assertEqual(self.added, [(1, "https://www.youtube.com/watch?v=AAAAAAAAAAA")])
        self.assertEqual(d["accepted"], [1])
        self.assertEqual(res["added"], [1])

    def test_rejected_rows_are_recorded_and_not_added(self):
        d = {"accepted": [], "rejected": []}
        rq.apply_decisions(self.queue, [], [2], d, {}, self.add)
        self.assertEqual(self.added, [])
        self.assertEqual(d["rejected"], [2])

    def test_a_video_already_used_by_another_song_is_not_added_twice(self):
        d = {"accepted": [], "rejected": []}
        res = rq.apply_decisions(self.queue, [2, 3], [], d, {}, self.add)
        self.assertEqual(len(self.added), 1)
        self.assertEqual(len(res["skipped"]), 1)
        self.assertIn("already used", res["skipped"][0][1])

    def test_unknown_ids_are_reported_not_applied(self):
        d = {"accepted": [], "rejected": []}
        res = rq.apply_decisions(self.queue, [999], [], d, {}, self.add)
        self.assertEqual(self.added, [])
        self.assertEqual(res["unknown"], [999])

    def test_a_song_that_already_has_a_video_is_skipped(self):
        d = {"accepted": [], "rejected": []}
        res = rq.apply_decisions(self.queue, [1], [], d, {1: {"id": "ZZZZZZZZZZZ"}}, self.add)
        self.assertEqual(self.added, [])
        self.assertIn("already has a video", res["skipped"][0][1])

    def test_an_id_in_both_lists_is_an_error(self):
        d = {"accepted": [], "rejected": []}
        with self.assertRaises(ValueError):
            rq.apply_decisions(self.queue, [1], [1], d, {}, self.add)


if __name__ == "__main__":
    unittest.main()
