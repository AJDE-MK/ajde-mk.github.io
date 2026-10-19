import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
import bulk_videos2 as b2


def song(song_id, cyr, lat, performers=(), first_line="Прва линија"):
    return {
        "id": song_id, "title_cyr": cyr, "title_latin": lat, "performers": list(performers), "audio": [],
        "versions": [{"stanzas": [{"lines": [{"cyr": first_line, "lat": "Prva linija", "en": "x"}]}]}],
    }


def result(vid, title, views=5000, seconds=200, channel="Chan"):
    return {"id": vid, "title": title, "channel": channel, "views": views, "seconds": seconds}


class FoldTests(unittest.TestCase):
    def test_latin_spellings_fold_together(self):
        self.assertEqual(b2.fold("Šuma"), b2.fold("shuma"))
        self.assertEqual(b2.fold("Žena"), b2.fold("zhena"))
        self.assertEqual(b2.fold("Čupi"), b2.fold("chupi"))
        self.assertEqual(b2.fold("Ǵorǵi"), b2.fold("Gjorgji"))
        self.assertEqual(b2.fold("Ḱerka"), b2.fold("kjerka"))

    def test_cyrillic_names_become_latin_for_comparison(self):
        self.assertEqual(b2.fold(b2.translit("Виолета Томовска")), b2.fold("Violeta Tomovska"))
        self.assertEqual(b2.fold(b2.translit("Наум Петрески")), b2.fold("Naum Petreski"))
        self.assertEqual(b2.fold(b2.translit("Љубојна")), b2.fold("Ljubojna"))


class PerformerTests(unittest.TestCase):
    def test_performer_in_title_or_channel_counts(self):
        s = song(1, "Т", "T", ["Виолета Томовска"])
        self.assertTrue(b2.performer_evidence(s, result("AAAAAAAAAAA", "Violeta Tomovska - Neka pesna")))
        self.assertTrue(b2.performer_evidence(s, result("AAAAAAAAAAA", "Neka pesna", channel="Violeta Tomovska - Topic")))
        self.assertTrue(b2.performer_evidence(s, result("AAAAAAAAAAA", "Виолета Томовска - Некоја песна")))

    def test_other_performers_do_not_count(self):
        s = song(1, "Т", "T", ["Виолета Томовска"])
        self.assertFalse(b2.performer_evidence(s, result("AAAAAAAAAAA", "Naum Petreski - Neka pesna")))

    def test_generic_group_words_alone_do_not_count(self):
        s = song(1, "Т", "T", ["Ансамбл Билјана"])
        self.assertFalse(b2.performer_evidence(s, result("AAAAAAAAAAA", "Ansambl Tanec - Neka pesna")))
        self.assertTrue(b2.performer_evidence(s, result("AAAAAAAAAAA", "Ansambl Biljana - Neka pesna")))

    def test_song_with_no_performers_has_no_evidence(self):
        self.assertFalse(b2.performer_evidence(song(1, "Т", "T", []), result("AAAAAAAAAAA", "Anything")))


class RecallTests(unittest.TestCase):
    S = song(1, "Мила мајко што ме роди", "Mila majko što me rodi")

    def test_recall_is_the_share_of_song_title_words_found(self):
        self.assertEqual(b2.title_recall(self.S, "Violeta Tomovska - Mila majko sto me rodi"), 1.0)
        self.assertAlmostEqual(b2.title_recall(self.S, "Mila majko"), 2 / 5)

    def test_works_in_cyrillic_too(self):
        self.assertEqual(b2.title_recall(self.S, "Виолета Томовска - Мила мајко што ме роди"), 1.0)


class ProcessPass2Tests(unittest.TestCase):
    S = song(30, "Мила мајко што ме роди", "Mila majko što me rodi", ["Виолета Томовска"])

    def go(self, s, results, used=(), embeddable=lambda v: True):
        return b2.process_song(s, search=lambda q: results, embeddable=embeddable, used_ids=set(used))

    def test_title_and_performer_together_are_added(self):
        out = self.go(self.S, [result("AAAAAAAAAAA", "Violeta Tomovska - Mila majko sto me rodi tolku siromav")])
        self.assertEqual(out["status"], "added")

    def test_title_without_performer_goes_to_review(self):
        out = self.go(self.S, [result("AAAAAAAAAAA", "Mila majko sto me rodi tolku siromav - Neko Drugo")])
        self.assertEqual(out["status"], "review")

    def test_performer_with_half_the_title_goes_to_review(self):
        out = self.go(self.S, [result("AAAAAAAAAAA", "Violeta Tomovska - Mila majko sto")])
        self.assertEqual(out["status"], "review")
        weak = self.go(self.S, [result("AAAAAAAAAAA", "Violeta Tomovska - Mila majko")])
        self.assertEqual(weak["status"], "none")

    def test_short_titles_need_the_performer(self):
        short = song(31, "Невесто", "Nevesto", ["Виолета Томовска"])
        self.assertEqual(self.go(short, [result("AAAAAAAAAAA", "Nevesto - Some Band")])["status"], "none")
        self.assertEqual(self.go(short, [result("AAAAAAAAAAA", "Violeta Tomovska - Nevesto")])["status"], "added")

    def test_performer_and_title_beat_a_more_viewed_title_only_match(self):
        res = [result("AAAAAAAAAAA", "Mila majko sto me rodi - Other", 900000),
               result("BBBBBBBBBBB", "Violeta Tomovska - Mila majko sto me rodi", 100)]
        out = self.go(self.S, res)
        self.assertEqual(out["video"]["id"], "BBBBBBBBBBB")

    def test_unrelated_results_give_none(self):
        self.assertEqual(self.go(self.S, [result("AAAAAAAAAAA", "Totally different")])["status"], "none")

    def test_instrumentals_used_ids_and_unembeddable_are_skipped(self):
        res = [result("AAAAAAAAAAA", "Violeta Tomovska - Mila majko sto me rodi (piano)"),
               result("BBBBBBBBBBB", "Violeta Tomovska - Mila majko sto me rodi"),
               result("CCCCCCCCCCC", "Violeta Tomovska - Mila majko sto me rodi live")]
        out = self.go(self.S, res, used={"BBBBBBBBBBB"}, embeddable=lambda v: v != "AAAAAAAAAAA")
        self.assertEqual(out["video"]["id"], "CCCCCCCCCCC")

    def test_queries_include_the_performer_and_the_first_lyric_line(self):
        seen = []

        def search(q):
            seen.append(q)
            return []

        s = song(32, "Мила мајко", "Mila majko", ["Виолета Томовска", "Наум Петрески"], first_line="Мила мајко што ме роди")
        b2.process_song(s, search=search, embeddable=lambda v: True, used_ids=set())
        joined = " | ".join(seen)
        self.assertIn("Виолета Томовска", joined)
        self.assertIn("Наум Петрески", joined)
        self.assertIn("Мила мајко што ме роди", joined)

    def test_a_search_failure_is_an_error_result(self):
        def boom(q):
            raise OSError("down")

        self.assertEqual(b2.process_song(self.S, search=boom, embeddable=lambda v: True, used_ids=set())["status"], "error")


class SelectionTests(unittest.TestCase):
    def test_only_songs_that_pass_one_found_nothing_are_searched(self):
        songs = [song(1, "a", "a"), song(2, "b", "b"), song(3, "c", "c"), song(4, "d", "d")]
        pass1 = {"none": [1, 2], "review": {"3": {}}, "added": {}}
        pass2 = {"done": [2], "added": {}, "review": {}, "none": [2], "error": {}}
        todo = b2.songs_to_search(songs, pass1, pass2, existing_videos={})
        self.assertEqual([s["id"] for s in todo], [1])

    def test_songs_with_a_video_are_skipped(self):
        songs = [song(1, "a", "a")]
        pass1 = {"none": [1], "review": {}, "added": {}}
        pass2 = {"done": [], "added": {}, "review": {}, "none": [], "error": {}}
        self.assertEqual(b2.songs_to_search(songs, pass1, pass2, existing_videos={1: {"id": "AAAAAAAAAAA"}}), [])

    def test_errors_are_retried(self):
        songs = [song(1, "a", "a")]
        pass1 = {"none": [1], "review": {}, "added": {}}
        pass2 = {"done": [1], "added": {}, "review": {}, "none": [], "error": {"1": "boom"}}
        self.assertEqual([s["id"] for s in b2.songs_to_search(songs, pass1, pass2, existing_videos={})], [1])


if __name__ == "__main__":
    unittest.main()
