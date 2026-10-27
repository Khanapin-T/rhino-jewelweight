import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_package  # noqa: E402


def load_installer():
    spec = importlib.util.spec_from_file_location(
        "jw_install", os.path.join(ROOT, "installer", "install.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder)

    def test_package_layout(self):
        path = make_package.build(self.folder)
        top = "JewelWeight-{0}/".format(make_package.read_version())
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
        for expected in ("README.txt", "install.py", "uninstall.py",
                         "app/commands/JewelWeight.py",
                         "app/lib/jewelweight/__init__.py", "app/lib/jewelweight/ui.py"):
            self.assertIn(top + expected, names)
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc")])

    def test_update_replaces_app_and_keeps_settings(self):
        installer = load_installer()
        base = os.path.join(self.folder, "JewelWeight")
        target = os.path.join(base, "app")
        os.makedirs(os.path.join(target, "old"))
        with open(os.path.join(base, "settings.json"), "w", encoding="utf-8") as stream:
            stream.write("{}")

        source = os.path.join(self.folder, "package", "app")
        os.makedirs(os.path.join(source, "commands"))
        with open(os.path.join(source, "commands", "JewelWeight.py"), "w") as stream:
            stream.write("# new")

        installer.copy_app(source, target)
        self.assertTrue(os.path.isfile(os.path.join(target, "commands", "JewelWeight.py")))
        self.assertFalse(os.path.exists(os.path.join(target, "old")))
        self.assertTrue(os.path.isfile(os.path.join(base, "settings.json")))

    def test_refuses_unexpected_target(self):
        installer = load_installer()
        with self.assertRaises(ValueError):
            installer.copy_app(self.folder, os.path.join(self.folder, "JewelWeight"))

    def test_alias_macro_runs_installed_command(self):
        installer = load_installer()
        macro = installer.command_macro(r"C:\Users\X\AppData\Roaming\JewelWeight\app")
        self.assertEqual(
            macro,
            '! _-ScriptEditor _Run "C:\\Users\\X\\AppData\\Roaming\\JewelWeight\\app'
            '\\commands\\JewelWeight.py"')


if __name__ == "__main__":
    unittest.main()
