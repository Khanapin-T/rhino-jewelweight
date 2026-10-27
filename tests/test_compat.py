import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "lib"))

from jewelweight import compat  # noqa: E402

MINIMUM = (8, 12, 24282)


class VersionCheckTests(unittest.TestCase):
    def test_supported(self):
        self.assertIsNone(compat.check_rhino_version((8, 12, 24282), MINIMUM))
        self.assertIsNone(compat.check_rhino_version((8, 20, 25100, 1), MINIMUM))

    def test_older_service_release(self):
        message = compat.check_rhino_version((8, 5, 24100), MINIMUM)
        self.assertIn("Rhino 8 SR12 (8.12.24282)", message)
        self.assertIn("Rhino 8 SR5 (8.5.24100)", message)
        self.assertIn("Help → Check for Updates", message)

    def test_rhino_7(self):
        message = compat.check_rhino_version((7, 37, 24107), MINIMUM)
        self.assertIn("только в Rhino 8", message)
        self.assertIn("Rhino 7 SR37", message)

    def test_rhino_9(self):
        message = compat.check_rhino_version((9, 0, 25300), MINIMUM)
        self.assertIn("только в Rhino 8", message)

    def test_default_minimum_is_rhino_8(self):
        self.assertEqual(compat.MIN_RHINO_VERSION[0], 8)
        self.assertIsNone(compat.check_rhino_version(compat.MIN_RHINO_VERSION))

    def test_describe_version(self):
        self.assertEqual(compat.describe_version((8, 0, 0)), "Rhino 8")
        self.assertEqual(compat.describe_version((8, 12, 24282, 7002)), "Rhino 8 SR12 (8.12.24282)")


if __name__ == "__main__":
    unittest.main()
