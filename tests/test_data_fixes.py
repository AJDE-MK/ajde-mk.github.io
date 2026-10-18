"""Checks on hand-edited song data (data/songs). These guard fixes made after the songbook was imported."""
import json
import unittest

import support  # noqa: F401
import config


def load(song_id):
    return json.loads((config.SONGS_DIR / f"{song_id:04d}.json").read_text(encoding="utf-8"))


class Song473Tests(unittest.TestCase):
    def setUp(self):
        self.song = load(473)

    def test_video_version_is_first_and_the_old_versions_follow(self):
        versions = self.song["versions"]
        self.assertEqual(len(versions), 3)
        self.assertIn("video", versions[0]["label"].lower())
        self.assertEqual(versions[1]["label"], "Version 2")
        self.assertEqual(versions[2]["label"], "Version 3")

    def test_video_version_has_the_five_stanzas_from_the_video(self):
        stanzas = self.song["versions"][0]["stanzas"]
        self.assertEqual(len(stanzas), 5)
        lat = [l["lat"] for st in stanzas for l in st["lines"]]
        self.assertTrue(lat[0].startswith("Storil niet zajko, zajko da se ženi"))
        self.assertTrue(any("Solunsko pole" in x for x in lat))
        self.assertTrue(lat[-1].endswith("mladoženja!"))

    def test_every_line_has_all_three_columns_and_english_is_marked_machine_made(self):
        v = self.song["versions"][0]
        self.assertEqual(v["en_source"], "mt")
        for st in v["stanzas"]:
            for l in st["lines"]:
                self.assertTrue(l["cyr"].strip())
                self.assertTrue(l["lat"].strip())
                self.assertTrue(l["en"].strip())
                self.assertTrue(l["en_mt"])

    def test_cyrillic_and_latin_agree_in_line_count_per_stanza(self):
        for st in self.song["versions"][0]["stanzas"]:
            self.assertGreaterEqual(len(st["lines"]), 4)

    def test_no_long_dashes_were_typed_into_the_new_version(self):
        text = json.dumps(self.song["versions"][0], ensure_ascii=False)
        self.assertNotIn("—", text)
        self.assertNotIn("–", text)

    def test_short_name_is_an_alias(self):
        self.assertIn("Зајко", self.song["aliases"])
        self.assertIn("Zajko", self.song["aliases"])


class Song1600Tests(unittest.TestCase):
    def setUp(self):
        self.song = load(1600)
        self.lines = [l for st in self.song["versions"][0]["stanzas"] for l in st["lines"]]

    def test_flock_line_follows_jordan_mitevs_word_order(self):
        flock = [l for l in self.lines if "стадо" in l["cyr"].lower()]
        self.assertEqual(len(flock), 1)
        self.assertEqual(flock[0]["cyr"], "Стадо ти се, домаќине, објагнало,")
        self.assertEqual(flock[0]["lat"], "Stado ti se, domaḱine, objagnalo,")
        self.assertEqual(flock[0]["en"], "Your flock, host, has lambed,")

    def test_second_line_is_sung_as_obliznilo(self):
        line = [l for l in self.lines if "половина" in l["cyr"]]
        self.assertEqual(len(line), 1)
        self.assertEqual(line[0]["cyr"], "ах, половина облизнило.")
        self.assertEqual(line[0]["lat"], "ah, polovina obliznilo.")
        self.assertEqual(line[0]["en"], "ah, half of them are tweens.")

    def test_the_original_wording_is_recorded(self):
        edits = self.song["edits"]
        self.assertEqual(len(edits), 2)
        self.assertEqual(edits[0]["was_cyr"], "Домаќине, стадо ти се објагнало,")
        self.assertEqual(edits[1]["was_cyr"], "ах, половина облизнало.")
        for e in edits:
            self.assertIn("Jordan Mitev", e["reason"])

    def test_nothing_else_in_the_song_changed(self):
        self.assertEqual(len(self.lines), 11)
        self.assertEqual(self.lines[0]["cyr"], "Домаќине, добри гости ти дојдоа,")
        self.assertEqual(self.lines[-1]["cyr"], "ај, ако пиеш, развесели се.")
        self.assertEqual(self.song["versions"][0]["en_source"], "pesna")


if __name__ == "__main__":
    unittest.main()
