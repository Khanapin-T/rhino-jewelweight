import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "lib"))

from jewelweight import history, metals  # noqa: E402


class MetalsTests(unittest.TestCase):
    def test_default_densities(self):
        expected = {
            "585 красное": 13.17, "585 жёлтое": 13.49, "585 белое": 13.76,
            "750 красное": 15.07, "750 жёлтое": 15.49, "750 белое": 15.62,
            "999": 19.31, "Серебро 925": 10.36,
        }
        self.assertEqual({m.label: m.density for m in metals.DEFAULT_METALS}, expected)

    def test_ids_unique_and_in_range(self):
        ids = [m.id for m in metals.DEFAULT_METALS]
        self.assertEqual(len(ids), len(set(ids)))
        for metal in metals.DEFAULT_METALS:
            self.assertTrue(metals.DENSITY_MIN <= metal.density <= metals.DENSITY_MAX)

    def test_layout_references_existing_metals(self):
        layout_ids = [i for row in metals.GOLD_GRID for i in row]
        layout_ids += [metals.FINE_GOLD_ID, metals.SILVER_ID]
        self.assertEqual(sorted(layout_ids), sorted(m.id for m in metals.DEFAULT_METALS))
        self.assertEqual(metals.get_metal("au750_white").label, "750 белое")


def texts(output_history):
    return [entry["text"] for entry in output_history.entries]


class HistoryTests(unittest.TestCase):
    def test_newest_block_at_bottom_in_reading_order(self):
        h = history.History()
        h.add_block([(history.KIND_RESULT, "first")])
        h.add_block([(history.KIND_RESULT, "second"), (history.KIND_WARNING, "note")])
        self.assertEqual(texts(h), ["first", "second", "note"])

    def test_last_result_skips_messages(self):
        h = history.History()
        h.add_block([(history.KIND_RESULT, "585 красное: 4.37 г (2 объекта)")])
        h.add_block([(history.KIND_ERROR, "Расчёт невозможен")])
        self.assertEqual(h.last_result(), "585 красное: 4.37 г (2 объекта)")

    def test_limit_keeps_newest_and_clear(self):
        h = history.History(limit=3)
        for i in range(5):
            h.add_block([(history.KIND_RESULT, str(i))])
        self.assertEqual(texts(h), ["2", "3", "4"])
        h.clear()
        self.assertIsNone(h.last_result())
        self.assertEqual(h.entries, [])

    def test_from_list_skips_malformed(self):
        items = [{"kind": "result", "text": "ok"}, {"kind": "bogus", "text": "x"},
                 {"kind": "info"}, "junk", {"kind": "error", "text": 5}]
        self.assertEqual(texts(history.History.from_list(items)), ["ok"])

    def test_default_limit_is_50(self):
        h = history.History.from_list([{"kind": "info", "text": str(i)} for i in range(60)])
        self.assertEqual(len(h.entries), 50)
        self.assertEqual(texts(h)[0], "10")


if __name__ == "__main__":
    unittest.main()
