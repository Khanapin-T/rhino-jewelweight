"""User settings: density overrides and custom alloys (pure Python).

Only densities the user changed are stored, so improved defaults in a new
plugin version still reach users who never edited them.
"""

import dataclasses
import math
import uuid

from . import calc
from . import metals

NAME_MAX = 40
FINENESS_MAX = 10

DENSITY_ERROR = ("Плотность — число от {0:g} до {1:g} г/см³, например 13.17 или 13,17."
                 .format(metals.DENSITY_MIN, metals.DENSITY_MAX))

_STANDARD_IDS = frozenset(metal.id for metal in metals.DEFAULT_METALS)


def parse_density(text):
    """Parse a density typed by the user; accepts a dot or a comma."""
    value_text = (text or "").strip().replace(",", ".")
    try:
        value = float(value_text)
    except ValueError:
        raise calc.UserError(DENSITY_ERROR)
    if not _is_valid_density(value):
        raise calc.UserError(DENSITY_ERROR)
    return value


def format_density(value):
    """At least two decimals, no trailing zeros beyond that: 13.17, 13.00, 13.175."""
    text = "{0:.4f}".format(value).rstrip("0")
    whole, _, fraction = text.partition(".")
    return "{0}.{1}".format(whole, fraction.ljust(2, "0"))


def alloy_label(name, fineness):
    return "{0} {1}".format(name, fineness) if fineness else name


def _is_valid_density(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and metals.DENSITY_MIN <= value <= metals.DENSITY_MAX)


class Settings(object):
    def __init__(self, density_overrides=None, custom_alloys=None):
        self._overrides = dict(density_overrides or {})
        self._custom = list(custom_alloys or [])

    # --- queries ------------------------------------------------------------

    def standard_metals(self):
        return [self._with_density(metal) for metal in metals.DEFAULT_METALS]

    def custom_alloys(self):
        return list(self._custom)

    def all_metals(self):
        return self.standard_metals() + self.custom_alloys()

    def get_metal(self, metal_id):
        for metal in self.all_metals():
            if metal.id == metal_id:
                return metal
        raise calc.UserError("Металл не найден — возможно, сплав удалён.")

    def _with_density(self, metal):
        density = self._overrides.get(metal.id)
        return metal if density is None else dataclasses.replace(metal, density=density)

    # --- standard metals ----------------------------------------------------

    def set_density(self, metal_id, density):
        default = metals.get_metal(metal_id).density
        if not _is_valid_density(density):
            raise calc.UserError(DENSITY_ERROR)
        if abs(density - default) < 1e-9:
            self._overrides.pop(metal_id, None)
        else:
            self._overrides[metal_id] = float(density)

    def reset_standard(self):
        self._overrides.clear()

    # --- custom alloys ------------------------------------------------------

    def add_alloy(self, name, fineness, density_text):
        alloy = self._make_alloy("custom_" + uuid.uuid4().hex[:8], name, fineness, density_text)
        self._custom.append(alloy)
        return alloy

    def update_alloy(self, alloy_id, name, fineness, density_text):
        index = self._custom_index(alloy_id)
        alloy = self._make_alloy(alloy_id, name, fineness, density_text)
        self._custom[index] = alloy
        return alloy

    def remove_alloy(self, alloy_id):
        del self._custom[self._custom_index(alloy_id)]

    def _custom_index(self, alloy_id):
        for index, alloy in enumerate(self._custom):
            if alloy.id == alloy_id:
                return index
        raise calc.UserError("Сплав не найден — возможно, он уже удалён.")

    def _make_alloy(self, alloy_id, name, fineness, density_text):
        name = " ".join((name or "").split())
        fineness = (fineness or "").strip()
        if not name:
            raise calc.UserError("Введите название сплава.")
        if len(name) > NAME_MAX:
            raise calc.UserError("Название длиннее {0} символов.".format(NAME_MAX))
        if len(fineness) > FINENESS_MAX:
            raise calc.UserError("Проба длиннее {0} символов.".format(FINENESS_MAX))
        density = parse_density(density_text)
        label = alloy_label(name, fineness)
        for metal in self.all_metals():
            if metal.id != alloy_id and metal.label.lower() == label.lower():
                raise calc.UserError("Металл «{0}» уже есть.".format(label))
        return metals.Metal(alloy_id, label, name, fineness, density, standard=False)

    # --- serialization ------------------------------------------------------

    def to_dict(self):
        return {
            "density_overrides": dict(self._overrides),
            "custom_alloys": [
                {"id": a.id, "name": a.name, "fineness": a.fineness, "density": a.density}
                for a in self._custom
            ],
        }

    @classmethod
    def from_dict(cls, data):
        """Build settings from stored data, skipping entries that are invalid."""
        overrides = {}
        raw_overrides = data.get("density_overrides")
        if isinstance(raw_overrides, dict):
            for metal_id, value in raw_overrides.items():
                if metal_id in _STANDARD_IDS and _is_valid_density(value):
                    overrides[metal_id] = float(value)
        result = cls(overrides)

        raw_alloys = data.get("custom_alloys")
        for item in raw_alloys if isinstance(raw_alloys, list) else []:
            try:
                alloy_id = item["id"]
                if not isinstance(alloy_id, str) or not alloy_id or alloy_id in _STANDARD_IDS:
                    continue
                if not _is_valid_density(item["density"]):
                    continue
                alloy = result._make_alloy(alloy_id, item["name"], item.get("fineness", ""),
                                           repr(float(item["density"])))
            except (calc.UserError, AttributeError, KeyError, TypeError, ValueError):
                continue
            if all(existing.id != alloy.id for existing in result._custom):
                result._custom.append(alloy)
        return result
