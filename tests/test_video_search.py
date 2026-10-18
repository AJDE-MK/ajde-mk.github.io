import json
import unittest

import support  # noqa: F401
import video_search as vs

SONG = {"id": 567, "title_cyr": "Јовано, Јованке", "title_latin": "Jovano, Jovanke", "title_en": "Jovano, Jovanke"}
LONG_SONG = {
    "id": 418,
    "title_cyr": "Ајде слушај, слушај калеш бре Анѓо",
    "title_latin": "Ajde slušaj, slušaj kaleš bre Anǵo",
    "title_en": "Come on, listen",
}


def result(video_id, title, views, seconds=240, channel="Chan"):
    return {"id": video_id, "title": title, "channel": channel, "views": views, "seconds": seconds}


class ParseTests(unittest.TestCase):
    def test_parse_views(self):
        self.assertEqual(vs.parse_views("1,234,567 views"), 1234567)
        self.assertEqual(vs.parse_views("1 view"), 1)
        self.assertEqual(vs.parse_views("No views"), 0)
        self.assertEqual(vs.parse_views("1.2M views"), 1200000)
        self.assertEqual(vs.parse_views("532K views"), 532000)
        self.assertEqual(vs.parse_views(None), 0)

    def test_parse_duration(self):
        self.assertEqual(vs.parse_duration("4:05"), 245)
        self.assertEqual(vs.parse_duration("1:02:03"), 3723)
        self.assertIsNone(vs.parse_duration(None))

    def test_extract_results_reads_the_page_data(self):
        data = {
            "contents": {
                "a": [
                    {
                        "videoRenderer": {
                            "videoId": "AAAAAAAAAAA",
                            "title": {"runs": [{"text": "Јовано Јованке"}]},
                            "ownerText": {"runs": [{"text": "Folk Channel"}]},
                            "viewCountText": {"simpleText": "2,500,000 views"},
                            "lengthText": {"simpleText": "3:30"},
                        }
                    },
                    {"somethingElse": {}},
                ]
            }
        }
        page = f"<html><script>var ytInitialData = {json.dumps(data)};</script></html>"
        got = vs.extract_results(page)
        self.assertEqual(got, [{"id": "AAAAAAAAAAA", "title": "Јовано Јованке", "channel": "Folk Channel",
                                "views": 2500000, "seconds": 210}])

    def test_extract_results_with_no_data_gives_empty_list(self):
        self.assertEqual(vs.extract_results("<html>nothing</html>"), [])


class MatchTests(unittest.TestCase):
    def test_exact_cyrillic_and_latin_titles_match(self):
        self.assertTrue(vs.title_matches(SONG, "Јовано, Јованке - македонска песна"))
        self.assertTrue(vs.title_matches(SONG, "JOVANO JOVANKE (Official)"))

    def test_unrelated_titles_do_not_match(self):
        self.assertFalse(vs.title_matches(SONG, "Македонски песни миx 2024"))
        self.assertFalse(vs.title_matches(SONG, "Jovan Jovanovic live"))

    def test_long_titles_may_be_shortened_a_little(self):
        self.assertTrue(vs.title_matches(LONG_SONG, "Ајде слушај калеш бре Анѓо"))
        self.assertFalse(vs.title_matches(LONG_SONG, "Ајде да се земиме"))

    def test_diacritics_and_case_are_ignored(self):
        self.assertTrue(vs.title_matches(LONG_SONG, "ajde slusaj kales bre angjo"))


class ChooseTests(unittest.TestCase):
    def test_highest_views_wins_over_newer_upload(self):
        results = [
            result("BBBBBBBBBBB", "Јовано Јованке", 900_000),
            result("CCCCCCCCCCC", "Јовано Јованке NEW 2025", 50_000),
            result("DDDDDDDDDDD", "Јовано Јованке live", 4_000_000),
        ]
        self.assertEqual(vs.choose_best(SONG, results)["id"], "DDDDDDDDDDD")

    def test_non_matching_videos_are_ignored_even_with_more_views(self):
        results = [result("EEEEEEEEEEE", "Totally different song", 99_000_000),
                   result("FFFFFFFFFFF", "Јовано Јованке", 1_000)]
        self.assertEqual(vs.choose_best(SONG, results)["id"], "FFFFFFFFFFF")

    def test_long_compilations_are_skipped(self):
        results = [result("GGGGGGGGGGG", "Јовано Јованке - 2 hour mix", 90_000_000, seconds=7200),
                   result("HHHHHHHHHHH", "Јовано Јованке", 10_000, seconds=200)]
        self.assertEqual(vs.choose_best(SONG, results)["id"], "HHHHHHHHHHH")

    def test_live_streams_with_no_duration_are_skipped(self):
        results = [result("IIIIIIIIIII", "Јовано Јованке", 5_000_000, seconds=None)]
        self.assertIsNone(vs.choose_best(SONG, results))

    def test_nothing_matches_gives_none(self):
        self.assertIsNone(vs.choose_best(SONG, [result("JJJJJJJJJJJ", "Other", 5)]))
        self.assertIsNone(vs.choose_best(SONG, []))

    def test_embeddable_check_is_used_to_pass_over_blocked_videos(self):
        results = [result("KKKKKKKKKKK", "Јовано Јованке", 9_000_000),
                   result("LLLLLLLLLLL", "Јовано Јованке", 100)]
        best = vs.choose_best(SONG, results, embeddable=lambda vid: vid != "KKKKKKKKKKK")
        self.assertEqual(best["id"], "LLLLLLLLLLL")


class EmbeddableTests(unittest.TestCase):
    def test_ok_response_means_embeddable(self):
        self.assertTrue(vs.is_embeddable("AAAAAAAAAAA", opener=lambda url: 200))

    def test_unauthorized_means_not_embeddable(self):
        self.assertFalse(vs.is_embeddable("AAAAAAAAAAA", opener=lambda url: 401))

    def test_network_error_means_not_confirmed(self):
        def boom(url):
            raise OSError("down")

        self.assertFalse(vs.is_embeddable("AAAAAAAAAAA", opener=boom))


class PopularTests(unittest.TestCase):
    def test_popular_songs_sorted_by_performer_count(self):
        songs = [
            {"id": 1, "performers": ["a"], "audio": []},
            {"id": 2, "performers": ["a", "b", "c"], "audio": []},
            {"id": 3, "performers": ["a", "b"], "audio": [1, 2, 3]},
        ]
        self.assertEqual([s["id"] for s in vs.popular_songs(songs, 2)], [2, 3])


if __name__ == "__main__":
    unittest.main()
