import unittest

import support  # noqa: F401
import apply_votes as av

EMAIL_ONE = """Video review answers: 2 yes, 1 no
song=917 video=5UB7oS7JMqE vote=yes
song=948 video=QHpvlr_kG6U vote=no
song=253 video=4honlU4aL1k vote=yes
"""
EMAIL_TWO = """Video review answers: 1 yes, 0 no
song=917 video=5UB7oS7JMqE vote=yes
"""


class ParseTests(unittest.TestCase):
    def test_lines_are_counted_per_song_and_video(self):
        tally = av.parse_votes(EMAIL_ONE + "\n" + EMAIL_TWO)
        self.assertEqual(tally[(917, "5UB7oS7JMqE")], {"yes": 2, "no": 0})
        self.assertEqual(tally[(948, "QHpvlr_kG6U")], {"yes": 0, "no": 1})
        self.assertEqual(tally[(253, "4honlU4aL1k")], {"yes": 1, "no": 0})

    def test_junk_lines_are_ignored(self):
        tally = av.parse_votes("hello\nsong=abc video=x vote=yes\nsong=1 video=AAAAAAAAAAA vote=maybe\n")
        self.assertEqual(tally, {})

    def test_html_or_quoted_email_text_still_parses(self):
        tally = av.parse_votes("> song=917 video=5UB7oS7JMqE vote=yes\n<p>song=948 video=QHpvlr_kG6U vote=no</p>")
        self.assertEqual(len(tally), 2)


class DecideTests(unittest.TestCase):
    def test_enough_yes_votes_accepts(self):
        self.assertEqual(av.decide({"yes": 2, "no": 0}, min_yes=2), "accept")

    def test_one_yes_is_not_enough_when_two_are_required(self):
        self.assertEqual(av.decide({"yes": 1, "no": 0}, min_yes=2), "wait")

    def test_a_single_no_does_not_reject_but_two_do(self):
        self.assertEqual(av.decide({"yes": 0, "no": 1}, min_no=2), "wait")
        self.assertEqual(av.decide({"yes": 0, "no": 2}, min_no=2), "reject")

    def test_mixed_votes_wait_for_a_clear_majority(self):
        self.assertEqual(av.decide({"yes": 2, "no": 2}), "wait")
        self.assertEqual(av.decide({"yes": 3, "no": 1}, min_yes=2), "accept")
        self.assertEqual(av.decide({"yes": 1, "no": 3}, min_no=2), "reject")


class PlanTests(unittest.TestCase):
    def test_plan_ignores_votes_for_a_different_video_than_the_queued_one(self):
        queue = [{"song_id": 917, "video": {"id": "5UB7oS7JMqE"}}]
        tally = {(917, "5UB7oS7JMqE"): {"yes": 2, "no": 0}, (917, "OTHEROTHER1"): {"yes": 5, "no": 0},
                 (999, "AAAAAAAAAAA"): {"yes": 5, "no": 0}}
        accept, reject, waiting = av.plan(tally, queue, min_yes=2, min_no=2)
        self.assertEqual(accept, [917])
        self.assertEqual(reject, [])
        self.assertEqual(waiting, [])

    def test_plan_lists_rows_that_are_waiting_for_more_votes(self):
        queue = [{"song_id": 1, "video": {"id": "AAAAAAAAAAA"}}, {"song_id": 2, "video": {"id": "BBBBBBBBBBB"}}]
        tally = {(1, "AAAAAAAAAAA"): {"yes": 1, "no": 0}}
        accept, reject, waiting = av.plan(tally, queue)
        self.assertEqual((accept, reject, waiting), ([], [], [1]))


if __name__ == "__main__":
    unittest.main()
