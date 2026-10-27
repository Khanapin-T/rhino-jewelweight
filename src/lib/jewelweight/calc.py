"""Pure calculation logic: object checks, units, weight and messages.

No Rhino imports here, so this module is testable with plain Python.
The Rhino adapter turns document objects into ObjectCheck records;
their volumes are signed and in document units cubed.
"""

import math
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, List, Optional


class UserError(Exception):
    """An expected problem; its message is shown to the user as is."""


# Object kinds produced by the Rhino adapter.
KIND_BREP = "brep"
KIND_MESH = "mesh"
KIND_UNSUPPORTED = "unsupported"
KIND_DELETED = "deleted"

# Validation problems that block the calculation.
PROBLEM_OPEN = "open"
PROBLEM_NON_MANIFOLD = "non_manifold"
PROBLEM_UNSUPPORTED = "unsupported"
PROBLEM_NO_VOLUME = "no_volume"

_PROBLEM_TEXT = {
    PROBLEM_OPEN: "открытый (не замкнутое тело)",
    PROBLEM_NON_MANIFOLD: "non-manifold",
    PROBLEM_UNSUPPORTED: "неподдерживаемый тип",
    PROBLEM_NO_VOLUME: "не удалось вычислить объём",
}

_PROBLEM_HINT = {
    PROBLEM_OPEN: "края покажет _ShowEdges; закройте через _Cap или _Join, меш — _FillMeshHoles",
    PROBLEM_NON_MANIFOLD: "меш исправьте через _MeshRepair, полиповерхность пересоберите",
    PROBLEM_UNSUPPORTED: "нужна полиповерхность, extrusion или меш",
    PROBLEM_NO_VOLUME: "проверьте объект командой _Check",
}

_SUBD_HINT = "преобразуйте через _ToNURBS"

# Rhino unit systems without a reliable millimetre scale.
UNSUPPORTED_UNITS = ("None", "CustomUnits")

_WEIGHT_STEP = Decimal("0.01")

OBJECT_FORMS = ("объект", "объекта", "объектов")

NO_SELECTION = "Сначала выберите объекты кнопкой SELECT OBJECTS."
DOC_CHANGED = "Активный документ сменился. Выберите объекты заново (SELECT OBJECTS)."
ALL_DELETED = ("Все выбранные объекты удалены из документа. "
               "Выберите объекты заново (SELECT OBJECTS).")
OVERLAP_WARNING = ("Внимание: выбрано несколько объектов, их объёмы суммируются. "
                   "Пересекающиеся тела считаются дважды — объедините их (_BooleanUnion). "
                   "Камни и вставки выделять не нужно.")


@dataclass
class ObjectCheck:
    """Plain facts about one selected object."""
    object_id: Any
    kind: str
    type_name: str = ""
    is_closed: bool = True
    is_manifold: bool = True
    volume: Optional[float] = None  # signed, document units cubed


@dataclass
class Evaluation:
    """Outcome of checking a selection."""
    valid_ids: List[Any] = field(default_factory=list)
    deleted_ids: List[Any] = field(default_factory=list)
    inverted_ids: List[Any] = field(default_factory=list)
    problems: List[tuple] = field(default_factory=list)  # (ObjectCheck, [problem, ...])
    volume_mm3: float = 0.0

    @property
    def problem_ids(self):
        return [check.object_id for check, _ in self.problems]

    @property
    def checked_count(self):
        """Objects still present in the document."""
        return len(self.valid_ids) + len(self.problems)


def _is_usable_volume(volume):
    return volume is not None and math.isfinite(volume) and volume != 0


def find_problems(check):
    """List the problems that make an object unusable for the calculation."""
    if check.kind not in (KIND_BREP, KIND_MESH):
        return [PROBLEM_UNSUPPORTED]
    problems = []
    if not check.is_closed:
        problems.append(PROBLEM_OPEN)
    if not check.is_manifold:
        problems.append(PROBLEM_NON_MANIFOLD)
    if not problems and not _is_usable_volume(check.volume):
        problems.append(PROBLEM_NO_VOLUME)
    return problems


def evaluate(checks, mm3_factor=1.0):
    """Validate objects and sum their volumes, converted to mm3.

    Negative volumes (inverted normals) are counted by absolute value and
    reported in inverted_ids. Deleted objects are listed separately.
    """
    result = Evaluation()
    total = 0.0
    for check in checks:
        if check.kind == KIND_DELETED:
            result.deleted_ids.append(check.object_id)
            continue
        problems = find_problems(check)
        if problems:
            result.problems.append((check, problems))
            continue
        volume = check.volume
        if volume < 0:
            result.inverted_ids.append(check.object_id)
            volume = -volume
        total += volume
        result.valid_ids.append(check.object_id)
    result.volume_mm3 = total * mm3_factor
    return result


def mm3_factor(unit_name, linear_scale):
    """Factor from document units cubed to mm3.

    unit_name is the Rhino UnitSystem name, linear_scale the length scale
    from document units to millimetres (RhinoMath.UnitScale).
    """
    if unit_name in UNSUPPORTED_UNITS or linear_scale is None:
        raise UserError(
            "Единицы документа не заданы или пользовательские ({0}). "
            "Установите миллиметры: File → Properties → Units.".format(unit_name))
    linear_scale = float(linear_scale)
    if not math.isfinite(linear_scale) or linear_scale <= 0:
        raise UserError("Не удалось определить масштаб единиц документа ({0}).".format(unit_name))
    return linear_scale ** 3


def weight_grams(volume_mm3, density_g_cm3):
    """Weight in grams, rounded half-up to 0.01 g (1 cm3 = 1000 mm3)."""
    raw = volume_mm3 * density_g_cm3 / 1000.0
    # repr() gives the shortest decimal form, so 4.365 rounds to 4.37, not 4.36.
    return Decimal(repr(raw)).quantize(_WEIGHT_STEP, rounding=ROUND_HALF_UP)


def plural_ru(count, forms=OBJECT_FORMS):
    """Russian noun form for a count: 1 объект, 2 объекта, 5 объектов."""
    n = abs(int(count)) % 100
    if 11 <= n <= 14:
        return forms[2]
    n %= 10
    if n == 1:
        return forms[0]
    if 2 <= n <= 4:
        return forms[1]
    return forms[2]


def count_objects(count):
    return "{0} {1}".format(count, plural_ru(count))


def format_volume(volume_mm3):
    return "{0:.2f}".format(volume_mm3)


def format_result(label, weight, count):
    """Output line, e.g. '585 красное: 4.37 г (2 объекта)'."""
    return "{0}: {1} г ({2})".format(label, weight, count_objects(count))


def selection_message(count, volume_mm3):
    return "Выбрано: {0}, объём {1} мм³.".format(count_objects(count), format_volume(volume_mm3))


def deleted_message(count):
    return "Не найдено в документе (удалено): {0}. Расчёт по оставшимся.".format(
        count_objects(count))


def inverted_message(count):
    return ("Внимание: вывернутые нормали (отрицательный объём) — {0}. "
            "Объём взят по модулю; исправьте нормали (_Dir, _UnifyMeshNormals).".format(
                count_objects(count)))


def _hint(problem, type_name):
    if problem == PROBLEM_UNSUPPORTED and type_name == "SubD":
        return _SUBD_HINT
    return _PROBLEM_HINT[problem]


def problems_message(evaluation):
    """Explain why the calculation is blocked, grouped by problem."""
    counts = {}
    for check, problems in evaluation.problems:
        for problem in problems:
            type_name = check.type_name if problem == PROBLEM_UNSUPPORTED else ""
            key = (problem, type_name)
            counts[key] = counts.get(key, 0) + 1

    lines = ["Расчёт невозможен. Проблемных объектов: {0} из {1} (выделены в Rhino):".format(
        len(evaluation.problems), evaluation.checked_count)]
    for (problem, type_name), count in counts.items():
        text = _PROBLEM_TEXT[problem]
        if type_name:
            text += " ({0})".format(type_name)
        lines.append("  • {0}: {1} — {2}".format(text, count, _hint(problem, type_name)))
    lines.append("Исправьте их и выберите объекты заново (SELECT OBJECTS).")
    return "\n".join(lines)
