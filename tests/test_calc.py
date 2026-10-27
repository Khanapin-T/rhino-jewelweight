import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "lib"))

from jewelweight import calc  # noqa: E402


def brep(object_id, volume=100.0, closed=True, manifold=True):
    return calc.ObjectCheck(object_id, calc.KIND_BREP, is_closed=closed,
                            is_manifold=manifold, volume=volume)


def mesh(object_id, volume=100.0, closed=True, manifold=True):
    return calc.ObjectCheck(object_id, calc.KIND_MESH, is_closed=closed,
                            is_manifold=manifold, volume=volume)


class PluralTests(unittest.TestCase):
    def test_forms(self):
        cases = {0: "объектов", 1: "объект", 2: "объекта", 4: "объекта", 5: "объектов",
                 11: "объектов", 12: "объектов", 14: "объектов", 21: "объект",
                 22: "объекта", 25: "объектов", 101: "объект", 111: "объектов"}
        for count, expected in cases.items():
            with self.subTest(count=count):
                self.assertEqual(calc.plural_ru(count), expected)


class WeightTests(unittest.TestCase):
    def test_formula(self):
        # 1 cm3 of a 13.17 g/cm3 alloy weighs 13.17 g.
        self.assertEqual(calc.weight_grams(1000.0, 13.17), Decimal("13.17"))

    def test_rounds_half_up(self):
        self.assertEqual(calc.weight_grams(1000.0, 13.165), Decimal("13.17"))
        self.assertEqual(calc.weight_grams(1000.0, 13.164), Decimal("13.16"))
        self.assertEqual(calc.weight_grams(1000.0, 13.155), Decimal("13.16"))

    def test_zero(self):
        self.assertEqual(calc.weight_grams(0.0, 19.31), Decimal("0.00"))

    def test_result_line(self):
        weight = calc.weight_grams(331.85, 13.17)  # 4.3704645 g
        self.assertEqual(calc.format_result("585 красное", weight, 2),
                         "585 красное: 4.37 г (2 объекта)")
        self.assertEqual(calc.format_result("999", Decimal("1.00"), 1), "999: 1.00 г (1 объект)")


class UnitsTests(unittest.TestCase):
    def test_millimeters(self):
        self.assertEqual(calc.mm3_factor("Millimeters", 1.0), 1.0)

    def test_centimeters(self):
        self.assertAlmostEqual(calc.mm3_factor("Centimeters", 10.0), 1000.0)

    def test_inches(self):
        self.assertAlmostEqual(calc.mm3_factor("Inches", 25.4), 16387.064)

    def test_unknown_units_rejected(self):
        for name in ("None", "CustomUnits"):
            with self.subTest(name=name), self.assertRaises(calc.UserError):
                calc.mm3_factor(name, 1.0)

    def test_bad_scale_rejected(self):
        for scale in (None, 0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(scale=scale), self.assertRaises(calc.UserError):
                calc.mm3_factor("Millimeters", scale)

    def test_volume_in_centimeters_converted(self):
        result = calc.evaluate([brep("a", 1.0)], calc.mm3_factor("Centimeters", 10.0))
        self.assertAlmostEqual(result.volume_mm3, 1000.0)


class EvaluateTests(unittest.TestCase):
    def test_sums_valid_objects(self):
        result = calc.evaluate([brep("a", 100.0), mesh("b", 50.5)])
        self.assertEqual(result.valid_ids, ["a", "b"])
        self.assertAlmostEqual(result.volume_mm3, 150.5)
        self.assertEqual(result.problems, [])

    def test_negative_volume_counted_by_absolute_value(self):
        result = calc.evaluate([mesh("a", -40.0), brep("b", 10.0)])
        self.assertAlmostEqual(result.volume_mm3, 50.0)
        self.assertEqual(result.inverted_ids, ["a"])

    def test_repaired_mesh_is_counted_and_reported(self):
        repaired = calc.ObjectCheck("a", calc.KIND_MESH, volume=30.0, repaired_faces=4)
        result = calc.evaluate([repaired, brep("b", 10.0)])
        self.assertEqual(result.valid_ids, ["a", "b"])
        self.assertEqual(result.repaired_ids, ["a"])
        self.assertIn("1 объект", calc.repaired_message(1))

    def test_open_brep_blocks(self):
        result = calc.evaluate([brep("a"), brep("b", volume=None, closed=False)])
        self.assertEqual(result.problem_ids, ["b"])
        self.assertEqual(result.problems[0][1], [calc.PROBLEM_OPEN])

    def test_mesh_open_and_non_manifold(self):
        result = calc.evaluate([mesh("a", volume=None, closed=False, manifold=False)])
        self.assertEqual(result.problems[0][1], [calc.PROBLEM_OPEN, calc.PROBLEM_NON_MANIFOLD])

    def test_unsupported_type(self):
        check = calc.ObjectCheck("a", calc.KIND_UNSUPPORTED, type_name="SubD")
        result = calc.evaluate([check])
        self.assertEqual(result.problems[0][1], [calc.PROBLEM_UNSUPPORTED])

    def test_missing_or_zero_volume(self):
        for volume in (None, 0.0, float("nan")):
            with self.subTest(volume=volume):
                result = calc.evaluate([brep("a", volume)])
                self.assertEqual(result.problems[0][1], [calc.PROBLEM_NO_VOLUME])

    def test_deleted_listed_separately(self):
        deleted = calc.ObjectCheck("x", calc.KIND_DELETED)
        result = calc.evaluate([brep("a", 10.0), deleted])
        self.assertEqual(result.deleted_ids, ["x"])
        self.assertEqual(result.checked_count, 1)
        self.assertAlmostEqual(result.volume_mm3, 10.0)

    def test_problems_message(self):
        result = calc.evaluate([
            brep("a"),
            brep("b", volume=None, closed=False),
            calc.ObjectCheck("c", calc.KIND_UNSUPPORTED, type_name="SubD"),
        ])
        message = calc.problems_message(result)
        self.assertIn("Проблемных объектов: 2 из 3", message)
        self.assertIn("открытый (не замкнутое тело): 1", message)
        self.assertIn("неподдерживаемый тип (SubD): 1", message)
        self.assertIn("_ToNURBS", message)


class MessageTests(unittest.TestCase):
    def test_selection_message(self):
        self.assertEqual(calc.selection_message(2, 331.854),
                         "Выбрано: 2 объекта, объём 331.85 мм³.")

    def test_deleted_message(self):
        self.assertIn("1 объект", calc.deleted_message(1))


if __name__ == "__main__":
    unittest.main()
