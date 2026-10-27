import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "lib"))

from jewelweight import history, metals, theme  # noqa: E402

# WCAG AA for normal text.
MIN_CONTRAST = 4.5


class ThemeTests(unittest.TestCase):
    def all_button_styles(self):
        styles = dict(theme.METALS)
        styles.update(select=theme.SELECT, neutral=theme.NEUTRAL, danger=theme.DANGER,
                      tab_active=theme.TAB_ACTIVE, tab_inactive=theme.TAB_INACTIVE,
                      custom=theme.CUSTOM_ALLOY)
        return styles

    def test_button_text_is_readable(self):
        for name, style in self.all_button_styles().items():
            for background in (style.top, style.bottom):
                with self.subTest(button=name, background=background):
                    self.assertGreaterEqual(theme.contrast(style.text, background), MIN_CONTRAST)

    def test_message_text_is_readable(self):
        for kind, style in theme.MESSAGES.items():
            with self.subTest(kind=kind):
                self.assertGreaterEqual(theme.contrast(style.text, style.background), MIN_CONTRAST)

    def test_dim_and_status_text_readable_on_backgrounds(self):
        for color in (theme.TEXT, theme.TEXT_DIM, theme.TEXT_OK, theme.TEXT_ERROR):
            for background in (theme.BACKGROUND, theme.PANEL):
                with self.subTest(color=color, background=background):
                    self.assertGreaterEqual(theme.contrast(color, background), MIN_CONTRAST)

    def test_every_metal_and_message_kind_has_a_style(self):
        self.assertEqual(set(theme.METALS), {m.id for m in metals.DEFAULT_METALS})
        self.assertEqual(set(theme.MESSAGES), set(history.KINDS))

    def test_750_is_stronger_than_585(self):
        # 585 is a light tint, 750 a more saturated or brighter one.
        for color in ("red", "yellow"):
            light = theme.METALS["au585_" + color].top
            strong = theme.METALS["au750_" + color].top
            self.assertGreater(max(strong) - min(strong), max(light) - min(light))
        self.assertGreater(theme.luminance(theme.METALS["au750_white"].top),
                           theme.luminance(theme.METALS["au585_white"].top))

    def test_shade(self):
        self.assertEqual(theme.shade((100, 100, 100), 0.0), (100, 100, 100))
        self.assertEqual(theme.shade((0, 0, 0), 1.0), (255, 255, 255))
        self.assertEqual(theme.shade((200, 100, 50), -1.0), (0, 0, 0))
        self.assertEqual(theme.shade((100, 100, 100), 0.5), (178, 178, 178))


if __name__ == "__main__":
    unittest.main()
