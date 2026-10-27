import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "lib"))

from jewelweight import calc, history, settings, storage  # noqa: E402


class DensityParsingTests(unittest.TestCase):
    def test_dot_and_comma(self):
        self.assertEqual(settings.parse_density("13.5"), 13.5)
        self.assertEqual(settings.parse_density(" 13,5 "), 13.5)
        self.assertEqual(settings.parse_density("25"), 25.0)
        self.assertEqual(settings.parse_density("5"), 5.0)

    def test_rejected(self):
        for text in ("", "abc", "4.99", "25.01", "nan", "inf", "13,5,1", None):
            with self.subTest(text=text), self.assertRaises(calc.UserError):
                settings.parse_density(text)

    def test_format(self):
        self.assertEqual(settings.format_density(13.17), "13.17")
        self.assertEqual(settings.format_density(13.0), "13.00")
        self.assertEqual(settings.format_density(13.175), "13.175")


class SettingsTests(unittest.TestCase):
    def test_density_override_and_reset(self):
        s = settings.Settings()
        s.set_density("au585_red", 13.3)
        self.assertEqual(s.get_metal("au585_red").density, 13.3)
        s.set_density("au585_red", 13.17)  # back to default: no override stored
        self.assertEqual(s.to_dict()["density_overrides"], {})
        s.set_density("au999", 19.0)
        s.reset_standard()
        self.assertEqual(s.get_metal("au999").density, 19.31)

    def test_add_edit_remove_alloy(self):
        s = settings.Settings()
        alloy = s.add_alloy("  Розовое   Pd ", "585", "13,9")
        self.assertEqual(alloy.label, "Розовое Pd 585")
        self.assertEqual(alloy.density, 13.9)
        self.assertFalse(alloy.standard)
        no_fineness = s.add_alloy("Мой сплав", "", "14")
        self.assertEqual(no_fineness.label, "Мой сплав")

        updated = s.update_alloy(alloy.id, "Розовое Pd", "750", "15.1")
        self.assertEqual(s.get_metal(alloy.id).label, "Розовое Pd 750")
        self.assertEqual(updated.density, 15.1)

        s.remove_alloy(alloy.id)
        self.assertEqual([a.label for a in s.custom_alloys()], ["Мой сплав"])
        with self.assertRaises(calc.UserError):
            s.get_metal(alloy.id)

    def test_alloy_validation(self):
        s = settings.Settings()
        s.add_alloy("Мой", "585", "14")
        for name, fineness, density in (("", "585", "14"), ("Мой", "585", "15"),
                                        ("585 красное", "", "13"), ("x" * 41, "", "14"),
                                        ("Ок", "1" * 11, "14"), ("Ок", "", "30")):
            with self.subTest(name=name), self.assertRaises(calc.UserError):
                s.add_alloy(name, fineness, density)

    def test_editing_keeps_own_label(self):
        s = settings.Settings()
        alloy = s.add_alloy("Мой", "585", "14")
        s.update_alloy(alloy.id, "Мой", "585", "14.5")  # same label is not a duplicate
        self.assertEqual(s.get_metal(alloy.id).density, 14.5)

    def test_round_trip(self):
        s = settings.Settings()
        s.set_density("ag925", 10.4)
        s.add_alloy("Белое Pd", "500", "14.2")
        restored = settings.Settings.from_dict(json.loads(json.dumps(s.to_dict())))
        self.assertEqual(restored.to_dict(), s.to_dict())

    def test_from_dict_skips_invalid_entries(self):
        data = {
            "density_overrides": {"au999": 19.0, "unknown": 10.0, "ag925": 99, "au585_red": "x"},
            "custom_alloys": [
                {"id": "custom_1", "name": "Хороший", "fineness": "585", "density": 14.0},
                {"id": "custom_2", "name": "", "density": 14.0},
                {"id": "custom_3", "name": "Плотный", "density": 40},
                {"id": "custom_1", "name": "Дубль id", "density": 14.0},
                {"name": "Без id", "density": 14.0},
                "junk",
            ],
        }
        restored = settings.Settings.from_dict(data)
        self.assertEqual(restored.to_dict()["density_overrides"], {"au999": 19.0})
        self.assertEqual([a.label for a in restored.custom_alloys()], ["Хороший 585"])


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.store = storage.Storage(self.folder)

    def tearDown(self):
        shutil.rmtree(self.folder)

    def write_raw(self, path, text):
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)

    def test_missing_files_give_defaults(self):
        loaded, notice = self.store.load_settings()
        self.assertIsNone(notice)
        self.assertEqual(loaded.custom_alloys(), [])
        output_history, notice = self.store.load_history()
        self.assertIsNone(notice)
        self.assertEqual(output_history.entries, [])

    def test_settings_saved_as_utf8_with_schema_version(self):
        s = settings.Settings()
        s.add_alloy("Красное с палладием", "585", "13.8")
        self.store.save_settings(s)
        with open(self.store.settings_path, "rb") as stream:
            raw = stream.read()
        self.assertIn("Красное с палладием".encode("utf-8"), raw)
        data = json.loads(raw.decode("utf-8"))
        self.assertEqual(data["schema_version"], storage.SETTINGS_SCHEMA_VERSION)
        loaded, notice = self.store.load_settings()
        self.assertIsNone(notice)
        self.assertEqual(loaded.custom_alloys()[0].label, "Красное с палладием 585")

    def test_utf8_bom_is_accepted(self):
        data = {"schema_version": 1, "density_overrides": {"au999": 19.0}, "custom_alloys": []}
        with open(self.store.settings_path, "w", encoding="utf-8-sig") as stream:
            json.dump(data, stream, ensure_ascii=False)
        loaded, notice = self.store.load_settings()
        self.assertIsNone(notice)
        self.assertEqual(loaded.get_metal("au999").density, 19.0)

    def assert_reset_with_backup(self, content):
        self.write_raw(self.store.settings_path, content)
        loaded, notice = self.store.load_settings()
        self.assertIsNotNone(notice)
        self.assertEqual(loaded.to_dict(), settings.Settings().to_dict())
        backups = [n for n in os.listdir(self.folder) if n.startswith("settings.json.broken-")]
        self.assertEqual(len(backups), 1)
        with open(os.path.join(self.folder, backups[0]), encoding="utf-8") as stream:
            self.assertEqual(stream.read(), content)
        # Defaults were written back, so the next start is quiet.
        self.assertIsNone(self.store.load_settings()[1])

    def test_broken_json_is_backed_up_and_reset(self):
        self.assert_reset_with_backup("{not json")

    def test_unknown_version_is_backed_up_and_reset(self):
        self.assert_reset_with_backup(json.dumps({"schema_version": 99, "custom_alloys": []}))

    def test_missing_version_is_backed_up_and_reset(self):
        self.assert_reset_with_backup(json.dumps({"custom_alloys": []}))

    def test_migration_keeps_user_data(self):
        def v1_to_v2(data):
            data["density_overrides"] = data.pop("densities")
            return data

        old = {"schema_version": 1, "densities": {"au999": 19.1},
               "custom_alloys": [{"id": "custom_1", "name": "Мой", "density": 14.0}]}
        migrated = storage.migrate(old, 2, {1: v1_to_v2})
        self.assertEqual(migrated["schema_version"], 2)
        restored = settings.Settings.from_dict(migrated)
        self.assertEqual(restored.get_metal("au999").density, 19.1)
        self.assertEqual(restored.custom_alloys()[0].label, "Мой")

    def test_migration_gap_is_an_error(self):
        with self.assertRaises(storage.SchemaError):
            storage.migrate({"schema_version": 1}, 3, {1: lambda data: data})

    def test_history_round_trip(self):
        output_history = history.History()
        output_history.add_block([(history.KIND_RESULT, "585 красное: 4.37 г (2 объекта)")])
        self.store.save_history(output_history)
        loaded, notice = self.store.load_history()
        self.assertIsNone(notice)
        self.assertEqual(loaded.last_result(), "585 красное: 4.37 г (2 объекта)")

    def test_broken_history_is_reset(self):
        self.write_raw(self.store.history_path, "[1, 2")
        loaded, notice = self.store.load_history()
        self.assertIsNotNone(notice)
        self.assertEqual(loaded.entries, [])


if __name__ == "__main__":
    unittest.main()
