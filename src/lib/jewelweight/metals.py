"""Built-in metals and their default densities (pure Python).

Default densities (g/cm3) are the midpoint between the alloy variants of
GOST 30649-99 and typical international values, so the error stays small
in both directions. This is the single place to change them.
"""

from dataclasses import dataclass

# Accepted density range for user edits, g/cm3.
DENSITY_MIN = 5.0
DENSITY_MAX = 25.0


@dataclass(frozen=True)
class Metal:
    id: str
    label: str      # text on the button and in the output
    name: str
    fineness: str   # assay mark ("проба"), may be empty for custom alloys
    density: float  # g/cm3
    standard: bool = True


DEFAULT_METALS = (
    Metal("au585_red", "585 красное", "Красное золото", "585", 13.17),
    Metal("au585_yellow", "585 жёлтое", "Жёлтое золото", "585", 13.49),
    Metal("au585_white", "585 белое", "Белое золото", "585", 13.76),
    Metal("au750_red", "750 красное", "Красное золото", "750", 15.07),
    Metal("au750_yellow", "750 жёлтое", "Жёлтое золото", "750", 15.49),
    Metal("au750_white", "750 белое", "Белое золото", "750", 15.62),
    Metal("au999", "999", "Золото", "999", 19.31),
    Metal("ag925", "Серебро 925", "Серебро", "925", 10.36),
)

# Calculation tab layout: rows red / yellow / white, columns 585 / 750.
GOLD_GRID = (
    ("au585_red", "au750_red"),
    ("au585_yellow", "au750_yellow"),
    ("au585_white", "au750_white"),
)
FINE_GOLD_ID = "au999"
SILVER_ID = "ag925"

_BY_ID = {metal.id: metal for metal in DEFAULT_METALS}


def get_metal(metal_id):
    return _BY_ID[metal_id]
