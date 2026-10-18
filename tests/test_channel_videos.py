import unittest

import support  # noqa: F401
import channel_videos as cv


def lockup(video_id, title, views_text="26K", duration="3:30"):
    return {
        "lockupViewModel": {
            "contentId": video_id,
            "contentImage": {
                "thumbnailViewModel": {
                    "overlays": [
                        {"thumbnailBottomOverlayViewModel": {"badges": [{"thumbnailBadgeViewModel": {"text": duration}}]}}
                    ]
                }
            },
            "metadata": {
                "lockupMetadataViewModel": {
                    "title": {"content": title},
                    "metadata": {
                        "contentMetadataViewModel": {
                            "metadataRows": [
                                {"metadataParts": [{"text": {"content": views_text}}, {"text": {"content": "5y ago"}}]}
                            ]
                        }
                    },
                }
            },
        }
    }


class CompactViewsTests(unittest.TestCase):
    def test_compact_view_counts(self):
        self.assertEqual(cv.parse_compact_views("26K"), 26000)
        self.assertEqual(cv.parse_compact_views("9.1K"), 9100)
        self.assertEqual(cv.parse_compact_views("1.2M"), 1200000)
        self.assertEqual(cv.parse_compact_views("850"), 850)
        self.assertEqual(cv.parse_compact_views("1,234"), 1234)
        self.assertEqual(cv.parse_compact_views("1.2M views"), 1200000)
        self.assertEqual(cv.parse_compact_views("No views"), 0)
        self.assertEqual(cv.parse_compact_views(None), 0)


class ExtractTests(unittest.TestCase):
    def test_reads_id_title_views_and_length(self):
        data = {"a": [lockup("AAAAAAAAAAA", "Zajdi Zajdi - Macedonian Traditional Song", "60K", "4:05"), {"x": 1}]}
        self.assertEqual(
            cv.extract_lockups(data),
            [{"id": "AAAAAAAAAAA", "title": "Zajdi Zajdi - Macedonian Traditional Song", "views": 60000, "seconds": 245}],
        )

    def test_skips_lockups_that_are_not_videos(self):
        broken = {"lockupViewModel": {"contentId": "PLxxxxxxxxxxxxxxxx"}}
        self.assertEqual(cv.extract_lockups({"a": [broken]}), [])

    def test_length_is_none_when_there_is_no_badge(self):
        item = lockup("BBBBBBBBBBB", "T")
        item["lockupViewModel"]["contentImage"] = {}
        self.assertIsNone(cv.extract_lockups({"a": [item]})[0]["seconds"])


class ContinuationTests(unittest.TestCase):
    def test_finds_the_continuation_token(self):
        data = {"x": {"continuationItemRenderer": {"continuationEndpoint": {"continuationCommand": {"token": "TOK1"}}}}}
        self.assertEqual(cv.find_continuation(data), "TOK1")

    def test_no_token_gives_none(self):
        self.assertIsNone(cv.find_continuation({"x": []}))


class FetchChannelTests(unittest.TestCase):
    def test_follows_continuations_until_they_run_out(self):
        first = {"items": [lockup("AAAAAAAAAAA", "One")], "c": {"continuationCommand": {"token": "T1"}}}
        second = {"items": [lockup("BBBBBBBBBBB", "Two")], "c": {"continuationCommand": {"token": "T2"}}}
        third = {"items": [lockup("CCCCCCCCCCC", "Three"), lockup("AAAAAAAAAAA", "One again")]}
        pages = {"T1": second, "T2": third}
        calls = []

        def post(token):
            calls.append(token)
            return pages[token]

        got = cv.fetch_channel_videos("UCx", get_first=lambda cid: first, post_next=post)
        self.assertEqual([v["id"] for v in got], ["AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"])
        self.assertEqual(calls, ["T1", "T2"])

    def test_stops_at_the_page_limit(self):
        page = {"items": [lockup("AAAAAAAAAAA", "One")], "c": {"continuationCommand": {"token": "T"}}}
        calls = []

        def post(token):
            calls.append(token)
            return page

        cv.fetch_channel_videos("UCx", get_first=lambda cid: page, post_next=post, max_pages=3)
        self.assertEqual(len(calls), 3)


def song(song_id, cyr, lat):
    return {"id": song_id, "title_cyr": cyr, "title_latin": lat}


class StrictTitleTests(unittest.TestCase):
    def test_exact_titles_with_channel_decoration_match(self):
        zajdi = song(452, "Зајди, зајди јасно сонце", "Zajdi, zajdi jasno sonce")
        self.assertTrue(cv.title_core_matches(zajdi, "Zajdi Zajdi Jasno Sonce - Macedonian Song"))
        self.assertTrue(cv.title_core_matches(zajdi, "Zajdi zajdi jasno sonce - live"))
        done = song(543, "Не стој Доне, Донке", "Ne stoj Done, Donke")
        self.assertTrue(cv.title_core_matches(done, "Oktet Makedonija - Ne Stoj Done, Donke - Macedonian Traditional Song"))
        svadba = song(1051, "Свадба голема", "Svadba golema")
        self.assertTrue(cv.title_core_matches(svadba, "Vojo Stojanovski - Svadba Golema"))

    def test_short_titles_do_not_match_longer_different_songs(self):
        short = song(71, "Ој девојче, девојче", "Oj devojče, devojče")
        self.assertFalse(cv.title_core_matches(short, "Oj Devojce, Belo i Crveno - Macedonian Traditional Song"))
        self.assertFalse(cv.title_core_matches(song(361, "Мој роден крај", "Moj roden kraj"),
                                               "MITAN Project - Macedonian Roses - Bitola, Moj Roden Kraj"))
        self.assertFalse(cv.title_core_matches(song(679, "Македонија", "Makedonija"),
                                               "Tose Proeski - Makedonija Naviva Za Vas"))
        self.assertFalse(cv.title_core_matches(song(972, "Струмица, Струмица", "Strumica, Strumica"),
                                               "Pod Kulite na Strumica - Macedonian Traditional Music"))
        self.assertFalse(cv.title_core_matches(song(778, "Девојче, девојче", "Devojče, devojče"),
                                               "MITAN Project - Macedonian Roses - Makedonsko Devojce"))

    def test_parenthesised_notes_are_ignored(self):
        turkish = song(598, "Чифте, чифте пајтонлари", "Čifte, čifte pajtonlari")
        self.assertTrue(cv.title_core_matches(turkish, "Cifte Cifte Pajtonlari - Macedonian Traditional Song (In Turkish)"))


class MatchChannelTests(unittest.TestCase):
    SONG = {"id": 452, "title_cyr": "Зајди, зајди јасно сонце", "title_latin": "Zajdi, zajdi jasno sonce"}

    def test_instrumentals_karaoke_and_dances_are_skipped(self):
        self.assertFalse(cv.is_sung_song("Zajdi, Zajdi, Jasno Sonce - Instrumental (Karaoke)"))
        self.assertFalse(cv.is_sung_song("Berance Oro - Macedonian Traditional Dance"))
        self.assertFalse(cv.is_sung_song("Which countries enjoy Macedonian Music the most?"))
        self.assertTrue(cv.is_sung_song("Oktet Makedonija - Ne Stoj Done, Donke - Macedonian Traditional Song"))

    def test_best_for_song_takes_the_most_viewed_sung_match(self):
        videos = [
            {"id": "AAAAAAAAAAA", "title": "Zajdi, Zajdi, Jasno Sonce - Instrumental (Karaoke)", "views": 60000, "seconds": 200},
            {"id": "BBBBBBBBBBB", "title": "Zajdi zajdi jasno sonce - Macedonian Traditional Song", "views": 5000, "seconds": 200},
            {"id": "CCCCCCCCCCC", "title": "Zajdi zajdi jasno sonce - live", "views": 9000, "seconds": 220},
            {"id": "DDDDDDDDDDD", "title": "Something else entirely", "views": 900000, "seconds": 200},
        ]
        self.assertEqual(cv.best_for_song(self.SONG, videos)["id"], "CCCCCCCCCCC")

    def test_plan_skips_videos_that_cannot_be_embedded_and_takes_the_next_best(self):
        s = self.SONG
        videos = [
            {"id": "AAAAAAAAAAA", "title": "Zajdi zajdi jasno sonce - Macedonian Song", "views": 900, "seconds": 200},
            {"id": "BBBBBBBBBBB", "title": "Zajdi zajdi jasno sonce - live", "views": 100, "seconds": 200},
        ]
        plan = cv.plan_additions([s], videos, set(), set(), embeddable=lambda vid: vid != "AAAAAAAAAAA")
        self.assertEqual([(p[0]["id"], p[1]["id"]) for p in plan], [(452, "BBBBBBBBBBB")])

    def test_plan_gives_one_video_to_at_most_one_song(self):
        a = {"id": 1, "title_cyr": "Зајди", "title_latin": "Zajdi"}
        b = {"id": 2, "title_cyr": "Зајди", "title_latin": "Zajdi"}
        videos = [{"id": "AAAAAAAAAAA", "title": "Zajdi - Macedonian Song", "views": 9, "seconds": 100}]
        plan = cv.plan_additions([a, b], videos, set(), set())
        self.assertEqual(len(plan), 1)

    def test_plan_leaves_songs_that_already_have_a_video(self):
        videos = [{"id": "AAAAAAAAAAA", "title": "Zajdi zajdi jasno sonce - Macedonian Song", "views": 9, "seconds": 100}]
        self.assertEqual(cv.plan_additions([self.SONG], videos, set(), {452}), [])

    def test_best_for_song_skips_ids_already_used(self):
        videos = [{"id": "CCCCCCCCCCC", "title": "Zajdi zajdi jasno sonce", "views": 9000, "seconds": 220}]
        self.assertIsNone(cv.best_for_song(self.SONG, videos, used_ids={"CCCCCCCCCCC"}))


if __name__ == "__main__":
    unittest.main()
