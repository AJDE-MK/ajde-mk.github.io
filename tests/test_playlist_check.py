import unittest

import support  # noqa: F401
import channel_videos as cv
import playlist_check as pc


def song(song_id, cyr, lat):
    return {"id": song_id, "title_cyr": cyr, "title_latin": lat}


def video(vid, title, views=0, seconds=200):
    return {"id": vid, "title": title, "views": views, "seconds": seconds}


SONGS = [
    song(424, "Стани моме да заиграш", "Stani mome da zaigraš"),
    song(425, "Сношти минав покрај вази", "Snošti minav pokraj vazi"),
    song(500, "Зошто си ме мајко родила", "Zošto si me majko rodila"),
    song(900, "Мори девојче убаво", "Mori devojče ubavo"),
]


class UrlAndScoreTests(unittest.TestCase):
    def test_playlist_url(self):
        self.assertEqual(cv.playlist_url("PLabc"), "https://www.youtube.com/playlist?list=PLabc")

    def test_title_score_is_one_for_an_exact_title_and_low_for_a_different_one(self):
        s = SONGS[0]
        self.assertEqual(cv.title_score(s, "Stani Mome Da Zaigras - Macedonian Song"), 1.0)
        self.assertLess(cv.title_score(s, "Totally different song"), 0.2)

    def test_title_core_matches_still_uses_point_eight(self):
        s = SONGS[0]
        self.assertTrue(cv.title_core_matches(s, "Stani Mome Da Zaigras - Macedonian Song"))
        self.assertFalse(cv.title_core_matches(s, "Stani Mome - Macedonian Song"))


class FetchPlaylistTests(unittest.TestCase):
    def test_reads_the_first_page_and_follows_continuations(self):
        def item(vid, title):
            return {"lockupViewModel": {"contentId": vid, "metadata": {"lockupMetadataViewModel": {"title": {"content": title}}}}}

        first = {"a": [item("AAAAAAAAAAA", "One")], "c": {"continuationCommand": {"token": "T1"}}}
        second = {"a": [item("BBBBBBBBBBB", "Two")]}
        got = cv.fetch_playlist_videos("PLx", get_first=lambda url: first, post_next=lambda tok: second)
        self.assertEqual([v["id"] for v in got], ["AAAAAAAAAAA", "BBBBBBBBBBB"])


class ClassifyTests(unittest.TestCase):
    def test_a_song_with_no_video_can_be_added(self):
        rows = pc.classify([video("AAAAAAAAAAA", "Stani Mome Da Zaigras - Macedonian Song")], SONGS, {})
        self.assertEqual(rows[0]["status"], "can_add")
        self.assertEqual(rows[0]["song"]["id"], 424)

    def test_a_song_that_already_has_a_video_is_reported_as_covered(self):
        rows = pc.classify([video("AAAAAAAAAAA", "Stani Mome Da Zaigras")], SONGS, {424: {"id": "ZZZZZZZZZZZ"}})
        self.assertEqual(rows[0]["status"], "has_video")
        self.assertFalse(rows[0]["same_video"])

    def test_the_same_video_is_noticed(self):
        rows = pc.classify([video("AAAAAAAAAAA", "Stani Mome Da Zaigras")], SONGS, {424: {"id": "AAAAAAAAAAA"}})
        self.assertTrue(rows[0]["same_video"])

    def test_a_title_that_is_close_but_not_exact_is_offered_as_a_maybe(self):
        rows = pc.classify([video("BBBBBBBBBBB", "Sosti minav pokraj vazi - Macedonian Song")], SONGS, {})
        self.assertEqual(rows[0]["status"], "maybe")
        self.assertEqual(rows[0]["candidates"][0]["id"], 425)

    def test_a_song_that_is_not_in_the_songbook_is_reported_missing(self):
        rows = pc.classify([video("CCCCCCCCCCC", "Zlatna Kokoska Peese Na Planina")], SONGS, {})
        self.assertEqual(rows[0]["status"], "not_found")
        self.assertEqual(rows[0]["candidates"], [])

    def test_summary_counts_each_status(self):
        rows = pc.classify(
            [video("AAAAAAAAAAA", "Stani Mome Da Zaigras"), video("CCCCCCCCCCC", "Zlatna Kokoska Peese Na Planina")],
            SONGS, {},
        )
        self.assertEqual(pc.summarize(rows), {"can_add": 1, "has_video": 0, "maybe": 0, "not_found": 1})

    def test_instrumentals_and_non_songs_are_not_counted(self):
        rows = pc.classify([video("DDDDDDDDDDD", "Zajdi zajdi - Instrumental (Karaoke)")], SONGS, {})
        self.assertEqual(rows, [])

    def test_a_video_is_never_proposed_for_two_songs(self):
        rows = pc.classify(
            [video("AAAAAAAAAAA", "Stani Mome Da Zaigras"), video("EEEEEEEEEEE", "Stani Mome Da Zaigras (live)")],
            SONGS, {},
        )
        self.assertEqual([r["status"] for r in rows], ["can_add", "has_video"])


if __name__ == "__main__":
    unittest.main()
