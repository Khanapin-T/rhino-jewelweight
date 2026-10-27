"""Dark color theme close to Rhino 8 dark mode (pure Python, RGB tuples)."""

from collections import namedtuple

# Buttons may have a vertical gradient (top -> bottom); flat buttons use the
# same color twice. border is None for buttons without an outline.
ButtonStyle = namedtuple("ButtonStyle", "top bottom text border")
MessageStyle = namedtuple("MessageStyle", "background text")


def _flat(color, text, border=None):
    return ButtonStyle(color, color, text, border)


BACKGROUND = (43, 43, 43)
PANEL = (32, 32, 32)
INPUT = (30, 30, 30)
INPUT_ERROR = (92, 40, 40)
SEPARATOR = (72, 72, 72)
TEXT = (230, 230, 230)
TEXT_DIM = (150, 150, 150)
TEXT_OK = (130, 210, 140)
TEXT_ERROR = (240, 140, 140)

_DARK_TEXT = (32, 26, 16)
_WHITE = (255, 255, 255)

SELECT = _flat((35, 134, 54), _WHITE)
NEUTRAL = _flat((62, 62, 62), TEXT, border=(84, 84, 84))
DANGER = _flat((122, 42, 42), _WHITE)
TAB_ACTIVE = _flat((66, 66, 66), _WHITE)
TAB_INACTIVE = _flat(BACKGROUND, (165, 165, 165), border=(66, 66, 66))
CUSTOM_ALLOY = _flat((60, 92, 124), _WHITE)

# 585 uses a light tint of the alloy color, 750 a stronger one.
METALS = {
    "au585_red": _flat((236, 172, 158), _DARK_TEXT),
    "au750_red": _flat((192, 64, 52), _WHITE),
    "au585_yellow": _flat((245, 225, 152), _DARK_TEXT),
    "au750_yellow": _flat((240, 190, 40), _DARK_TEXT),
    "au585_white": _flat((212, 212, 204), _DARK_TEXT),
    "au750_white": _flat((250, 250, 250), _DARK_TEXT),
    "au999": ButtonStyle((255, 228, 125), (212, 175, 55), _DARK_TEXT, None),
    "ag925": ButtonStyle((238, 238, 238), (166, 166, 166), (24, 24, 24), None),
}

# Keys match history.KIND_* values.
MESSAGES = {
    "result": MessageStyle((36, 58, 42), (214, 245, 220)),
    "info": MessageStyle((50, 50, 50), (210, 210, 210)),
    "warning": MessageStyle((66, 55, 28), (245, 214, 138)),
    "error": MessageStyle((72, 36, 36), (250, 188, 188)),
}


def shade(rgb, amount):
    """Lighten toward white (amount > 0) or darken toward black (amount < 0)."""
    if amount >= 0:
        return tuple(int(round(c + (255 - c) * amount)) for c in rgb)
    return tuple(int(round(c * (1.0 + amount))) for c in rgb)


def luminance(rgb):
    """WCAG relative luminance, 0..1."""
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG contrast ratio between two colors, 1..21."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def state_shade(style, hover, pressed):
    """Shade amount for hover / pressed: light buttons darken, dark ones lighten."""
    light = luminance(style.top) > 0.4
    if pressed:
        return -0.18 if light else -0.15
    if hover:
        return -0.08 if light else 0.10
    return 0.0
