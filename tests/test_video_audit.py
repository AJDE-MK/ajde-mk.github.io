import unittest

import support  # noqa: F401
import video_audit as va


def song(song_id, cyr, lat):
    return {"id": song_id, "title_cyr": cyr, "title_latin": lat}


SONGS = [
    song(589, "Бог да бие Русе твојта мајка", "Bog da bie Ruse tvojta majka"),
    song(590, "Бог да бие мојта мајка", "Bog da bie mojta majka"),
    song(600, "Бор садила мома Евгенија", "Bor sadila moma Evgenija"),
]


class FitTests(unittest.TestCase):
    def test_a_video_fits_its_own_song_best(self):
        self.assertEqual(va.best_song(SONGS, "Bor Sadila Moma Evgenija - Macedonian Song").get("id"), 600)

    def test_the_twin_title_with_the_extra_word_wins(self):
        self.assertEqual(va.best_song(SONGS, "Bog da bie, Ruse, tvojta majka").get("id"), 589)

    def test_nothing_close_gives_none(self):
        self.assertIsNone(va.best_song(SONGS, "Totally unrelated words here"))


class ConflictTests(unittest.TestCase):
    def test_a_video_that_fits_another_song_better_is_a_conflict(self):
        entries = {"590": {"id": "AAAAAAAAAAA", "title": "Bog da bie, Ruse, tvojta majka"}}
        self.assertEqual(va.find_conflicts(entries, SONGS), [(590, 589)])

    def test_a_correct_match_is_not_a_conflict(self):
        entries = {"589": {"id": "AAAAAAAAAAA", "title": "Bog da bie, Ruse, tvojta majka"},
                   "600": {"id": "BBBBBBBBBBB", "title": "Bor Sadila Moma Evgenija - Macedonian Song"}}
        self.assertEqual(va.find_conflicts(entries, SONGS), [])

    def test_a_video_matching_no_song_better_is_left_alone(self):
        entries = {"600": {"id": "AAAAAAAAAAA", "title": "Vaska Ilieva - Neshto drugo"}}
        self.assertEqual(va.find_conflicts(entries, SONGS), [])

    def test_equal_fit_is_not_a_conflict(self):
        twins = [song(1, "Мила мајко", "Mila majko"), song(2, "Мила мајко", "Mila majko")]
        entries = {"2": {"id": "AAAAAAAAAAA", "title": "Mila majko"}}
        self.assertEqual(va.find_conflicts(entries, twins), [])


class MoveTests(unittest.TestCase):
    def test_conflicts_move_from_added_to_review(self):
        progress = {"done": [590], "added": {"590": {"id": "AAAAAAAAAAA", "title": "Bog da bie, Ruse, tvojta majka"}},
                    "review": {}, "none": [], "error": {}}
        moved = va.demote_conflicts(progress, SONGS)
        self.assertEqual(moved, [(590, 589)])
        self.assertEqual(progress["added"], {})
        self.assertIn("590", progress["review"])
        self.assertIn("also fits song 589", progress["review"]["590"]["note"])


if __name__ == "__main__":
    unittest.main()
