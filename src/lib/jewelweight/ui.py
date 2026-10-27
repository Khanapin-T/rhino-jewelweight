"""Modeless Eto window for JewelWeight (one instance per Rhino session)."""

import traceback

import Eto.Drawing as drawing
import Eto.Forms as forms
import Rhino
import Rhino.UI
import scriptcontext as sc

from . import calc
from . import history
from . import metals
from . import rhino_adapter

# scriptcontext.sticky lives for the whole Rhino session, so the open window
# is found again on the next command run even after modules are reloaded.
_STICKY_KEY = "JewelWeight.window"

_SPACING = 6
_BUTTON_HEIGHT = 30
_SELECT_BUTTON_HEIGHT = 36
_LEFT_WIDTH = 250


def focus_existing():
    """Bring the open window to front. Returns False if there is none."""
    window = sc.sticky.get(_STICKY_KEY)
    if window is None:
        return False
    if window.bring_to_front():
        return True
    sc.sticky.pop(_STICKY_KEY, None)
    return False


def open_window():
    window = JewelWeightWindow()
    sc.sticky[_STICKY_KEY] = window
    window.show()
    return window


# Layout helpers. Cells and rows are built explicitly because Eto's implicit
# Control -> TableCell conversions are not applied from Python.

def _cell(control, scale_width=True):
    return forms.TableCell(control, scale_width)


def _row(*items, scale_height=False):
    row = forms.TableRow()
    for item in items:
        row.Cells.Add(item if isinstance(item, forms.TableCell) else _cell(item))
    row.ScaleHeight = scale_height
    return row


def _table(rows, spacing=_SPACING):
    table = forms.TableLayout()
    table.Spacing = drawing.Size(spacing, spacing)
    for row in rows:
        table.Rows.Add(row)
    return table


def _button(text, on_click, height=_BUTTON_HEIGHT):
    button = forms.Button()
    button.Text = text
    button.Height = height
    button.Click += on_click
    return button


class JewelWeightWindow(object):
    def __init__(self):
        self._object_ids = []
        self._doc_serial = None
        self._warned_inverted = set()
        self._busy = False
        self._history = history.History()
        self._output = None
        self.form = self._build_form()

    # --- window -----------------------------------------------------------

    def _build_form(self):
        form = forms.Form()
        form.Title = "JewelWeight"
        form.Padding = drawing.Padding(10)
        form.Resizable = True
        form.ShowInTaskbar = False
        form.ClientSize = drawing.Size(580, 300)
        form.MinimumSize = drawing.Size(480, 280)
        form.Content = self._build_content()
        form.Closed += self._on_closed
        return form

    def _build_content(self):
        separator = forms.Panel()
        separator.Width = 1
        separator.BackgroundColor = drawing.Color.FromArgb(170, 170, 170, 255)
        row = _row(_cell(self._build_left(), False), _cell(separator, False),
                   _cell(self._build_right(), True), scale_height=True)
        return _table([row], spacing=10)

    def _build_left(self):
        select_button = _button("SELECT OBJECTS", self._on(self._select_objects),
                                height=_SELECT_BUTTON_HEIGHT)
        grid = _table([_row(*[self._metal_button(metal_id) for metal_id in row_ids])
                       for row_ids in metals.GOLD_GRID])
        left = _table([
            _row(select_button),
            _row(grid),
            _row(self._metal_button(metals.FINE_GOLD_ID)),
            _row(self._metal_button(metals.SILVER_ID)),
            _row(forms.Panel(), scale_height=True),  # keeps the buttons at the top
        ])
        left.Width = _LEFT_WIDTH
        return left

    def _build_right(self):
        self._output = forms.TextArea()
        self._output.ReadOnly = True
        self._output.Wrap = True
        buttons = _table([_row(_button("Копировать", self._on(self._copy_last)),
                               _button("Очистить", self._on(self._clear)))])
        return _table([_row(self._output, scale_height=True), _row(buttons)])

    def _metal_button(self, metal_id):
        return _button(metals.get_metal(metal_id).label, self._on(self._calculate, metal_id))

    def show(self):
        self.form.Owner = Rhino.UI.RhinoEtoApp.MainWindow  # stays above Rhino
        self.form.Show()

    def bring_to_front(self):
        """Return False if the form is already closed."""
        try:
            if not self.form.Visible:
                return False
            if self.form.WindowState == forms.WindowState.Minimized:
                self.form.WindowState = forms.WindowState.Normal
            self.form.BringToFront()
            self.form.Focus()
            return True
        except Exception:
            return False

    def _on_closed(self, sender, e):
        if sc.sticky.get(_STICKY_KEY) is self:
            sc.sticky.pop(_STICKY_KEY, None)

    # --- event plumbing ---------------------------------------------------

    def _on(self, action, *args):
        """Wrap an action as an Eto click handler with error reporting."""
        def handler(sender, e):
            self._run(action, *args)
        return handler

    def _run(self, action, *args):
        if self._busy:  # e.g. a metal button clicked while picking objects
            return
        self._busy = True
        try:
            action(*args)
        except calc.UserError as err:
            self._add([(history.KIND_ERROR, str(err))])
        except Exception as err:
            Rhino.RhinoApp.WriteLine("JewelWeight: внутренняя ошибка\n" + traceback.format_exc())
            self._add([(history.KIND_ERROR,
                        "Ошибка программы: {0}\n"
                        "Подробности — в командной строке Rhino (F2).".format(err))])
        finally:
            self._busy = False

    def _add(self, block):
        self._history.add_block(block)
        self._output.Text = self._history.render()

    # --- actions ----------------------------------------------------------

    def _select_objects(self):
        doc = rhino_adapter.active_doc()
        ids = rhino_adapter.pick_objects()
        if not ids:
            return  # cancelled: keep the previous selection
        self._object_ids = ids
        self._doc_serial = doc.RuntimeSerialNumber
        self._warned_inverted = set()

        evaluation = self._evaluate(doc)
        if evaluation.problems:
            self._report_problems(doc, evaluation)
            return
        block = [(history.KIND_INFO, calc.selection_message(
            len(evaluation.valid_ids), evaluation.volume_mm3))]
        block += self._inverted_notes(evaluation)
        if len(evaluation.valid_ids) > 1:
            block.append((history.KIND_WARNING, calc.OVERLAP_WARNING))
        self._add(block)

    def _calculate(self, metal_id):
        metal = metals.get_metal(metal_id)
        if not self._object_ids:
            raise calc.UserError(calc.NO_SELECTION)
        doc = rhino_adapter.active_doc()
        if doc.RuntimeSerialNumber != self._doc_serial:
            raise calc.UserError(calc.DOC_CHANGED)

        # Re-check by stored ids: objects may have been edited or deleted.
        evaluation = self._evaluate(doc)
        notes = []
        if evaluation.deleted_ids:
            self._forget(evaluation.deleted_ids)
            if not self._object_ids:
                raise calc.UserError(calc.ALL_DELETED)
            notes.append((history.KIND_WARNING, calc.deleted_message(len(evaluation.deleted_ids))))
        if evaluation.problems:
            self._report_problems(doc, evaluation, notes)
            return
        notes += self._inverted_notes(evaluation)

        weight = calc.weight_grams(evaluation.volume_mm3, metal.density)
        result = calc.format_result(metal.label, weight, len(evaluation.valid_ids))
        self._add([(history.KIND_RESULT, result)] + notes)
        Rhino.RhinoApp.WriteLine("JewelWeight: " + result)

    def _copy_last(self):
        text = self._history.last_result()
        if text is None:
            Rhino.RhinoApp.WriteLine("JewelWeight: нет результата для копирования.")
            return
        clipboard = forms.Clipboard()
        clipboard.Text = text
        Rhino.RhinoApp.WriteLine("JewelWeight: скопировано — " + text)

    def _clear(self):
        self._history.clear()
        self._output.Text = ""

    # --- helpers ----------------------------------------------------------

    def _evaluate(self, doc):
        factor = rhino_adapter.mm3_factor(doc)
        checks = [rhino_adapter.inspect_object(doc, object_id) for object_id in self._object_ids]
        return calc.evaluate(checks, factor)

    def _report_problems(self, doc, evaluation, notes=()):
        rhino_adapter.highlight(doc, evaluation.problem_ids)
        self._add([(history.KIND_ERROR, calc.problems_message(evaluation))] + list(notes))

    def _forget(self, object_ids):
        # Compare as strings: Guid equality through pythonnet is not guaranteed.
        gone = set(str(object_id) for object_id in object_ids)
        self._object_ids = [i for i in self._object_ids if str(i) not in gone]

    def _inverted_notes(self, evaluation):
        """Warn about inverted normals once per object and selection."""
        new = [i for i in evaluation.inverted_ids if str(i) not in self._warned_inverted]
        if not new:
            return []
        self._warned_inverted.update(str(i) for i in new)
        return [(history.KIND_WARNING, calc.inverted_message(len(evaluation.inverted_ids)))]
