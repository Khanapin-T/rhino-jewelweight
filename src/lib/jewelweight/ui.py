"""Modeless Eto window for JewelWeight (one instance per Rhino session).

Dark theme colors come from theme.py. Buttons are drawn on Eto Drawables:
native WPF buttons replace custom colors with their own on hover.
"""

import traceback

import clr
import System
import Eto.Drawing as drawing
import Eto.Forms as forms
import Rhino
import Rhino.UI
import scriptcontext as sc

from . import __version__
from . import calc
from . import history
from . import metals
from . import rhino_adapter
from . import settings as settings_mod
from . import storage
from . import theme

# scriptcontext.sticky lives for the whole Rhino session, so the open window
# is found again on the next command run even after modules are reloaded.
_STICKY_KEY = "JewelWeight.window"

_SPACING = 6
_BUTTON_HEIGHT = 30
_SMALL_BUTTON_HEIGHT = 26
_SELECT_BUTTON_HEIGHT = 38
_LEFT_WIDTH = 250
_CAPTION_WIDTH = 90
_RADIUS = 4.0
_SCROLLBAR_ALLOWANCE = 18
_FONT_FAMILY = "Segoe UI"

_PAGE_CALC = "calc"
_PAGE_SETTINGS = "settings"
_STANDARD_NOTE = "среднее значение, уточните для своего сплава"


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


# --- small builders ---------------------------------------------------------
# Cells and rows are built explicitly because Eto's implicit
# Control -> TableCell conversions are not applied from Python.

def _color(rgb):
    return drawing.Color.FromArgb(rgb[0], rgb[1], rgb[2], 255)


def _enum_member(enum_type, name):
    """Enum member by name. Members named like Python keywords ("None") are
    not reachable as attributes from Python, not even with getattr."""
    return System.Enum.Parse(clr.GetClrType(enum_type), name)


def _font(size, bold=False):
    if bold:
        return drawing.Font(_FONT_FAMILY, size, drawing.FontStyle.Bold)
    return drawing.Font(_FONT_FAMILY, size)


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


def _hbox(*cells):
    """One horizontal line of cells, independent of the parent's columns."""
    return _table([_row(*cells)])


def _label(text, color=theme.TEXT, font=None, width=None):
    label = forms.Label()
    label.Text = text
    label.TextColor = _color(color)
    label.VerticalAlignment = forms.VerticalAlignment.Center
    if font is not None:
        label.Font = font
    if width:
        label.Width = width
    return label


def _text_box(text="", width=None, placeholder=None):
    box = forms.TextBox()
    box.Text = text
    box.BackgroundColor = _color(theme.INPUT)
    box.TextColor = _color(theme.TEXT)
    if width:
        box.Width = width
    if placeholder:
        box.PlaceholderText = placeholder
    return box


def _scrollable(background):
    scroll = forms.Scrollable()
    scroll.Border = _enum_member(forms.BorderType, "None")
    scroll.ExpandContentWidth = True
    scroll.ExpandContentHeight = True
    scroll.BackgroundColor = _color(background)
    return scroll


def _separator(vertical):
    line = forms.Panel()
    line.BackgroundColor = _color(theme.SEPARATOR)
    if vertical:
        line.Width = 1
    else:
        line.Height = 1
    return line


def _spacer():
    return forms.Panel()


class _ColorButton(object):
    """Rounded flat (or gradient) button drawn on a Drawable."""

    def __init__(self, text, style, on_click, height=_BUTTON_HEIGHT, width=None, font=None):
        self._text = text
        self._style = style
        self._on_click = on_click
        self._font = font or _font(9, bold=True)
        self._hover = False
        self._pressed = False
        self._flash_text = None
        self._timer = None
        self._size = (0.0, 0.0)
        control = forms.Drawable()
        control.Height = height
        if width:
            control.Width = width
        control.Cursor = forms.Cursors.Pointer
        control.Paint += self._on_paint
        control.MouseEnter += self._on_mouse_enter
        control.MouseLeave += self._on_mouse_leave
        control.MouseDown += self._on_mouse_down
        control.MouseUp += self._on_mouse_up
        self.control = control

    def set_text(self, text):
        self._text = text
        self.control.Invalidate()

    def set_style(self, style):
        self._style = style
        self.control.Invalidate()

    def flash(self, text, seconds=1.5):
        """Show text for a moment instead of the caption."""
        self._flash_text = text
        self.control.Invalidate()
        if self._timer is None:
            self._timer = forms.UITimer()
            self._timer.Elapsed += self._on_flash_end
        self._timer.Stop()
        self._timer.Interval = seconds
        self._timer.Start()

    def _on_flash_end(self, sender, e):
        self._timer.Stop()
        self._flash_text = None
        self.control.Invalidate()

    def _on_mouse_enter(self, sender, e):
        self._hover = True
        self.control.Invalidate()

    def _on_mouse_leave(self, sender, e):
        self._hover = False
        self._pressed = False
        self.control.Invalidate()

    def _on_mouse_down(self, sender, e):
        if e.Buttons == forms.MouseButtons.Primary:
            self._pressed = True
            self.control.Invalidate()

    def _on_mouse_up(self, sender, e):
        width, height = self._size
        point = e.Location
        clicked = self._pressed and 0 <= point.X <= width and 0 <= point.Y <= height
        self._pressed = False
        self.control.Invalidate()
        if clicked:
            # Run after Eto finishes this mouse event and releases mouse
            # capture; otherwise picking in the viewport would not get clicks.
            forms.Application.Instance.AsyncInvoke(System.Action(self._on_click))

    def _on_paint(self, sender, e):
        g = e.Graphics
        size = self.control.Size
        width, height = float(size.Width), float(size.Height)
        if width <= 0 or height <= 0:
            clip = e.ClipRectangle
            width, height = float(clip.Width), float(clip.Height)
        self._size = (width, height)
        if width < 2 or height < 2:
            return
        g.AntiAlias = True

        amount = theme.state_shade(self._style, self._hover, self._pressed)
        top = _color(theme.shade(self._style.top, amount))
        bottom = _color(theme.shade(self._style.bottom, amount))
        path = drawing.GraphicsPath.GetRoundRect(
            drawing.RectangleF(0.5, 0.5, width - 1.0, height - 1.0), _RADIUS)
        if self._style.top == self._style.bottom:
            brush = drawing.SolidBrush(top)
        else:
            brush = drawing.LinearGradientBrush(
                top, bottom, drawing.PointF(0.0, 0.0), drawing.PointF(0.0, height))
        try:
            g.FillPath(brush, path)
        finally:
            brush.Dispose()
        if self._style.border is not None:
            pen = drawing.Pen(_color(self._style.border), 1.0)
            try:
                g.DrawPath(pen, path)
            finally:
                pen.Dispose()

        text = self._fit(g, self._flash_text or self._text, width - 12.0)
        text_size = g.MeasureString(self._font, text)
        g.DrawText(self._font, _color(self._style.text),
                   (width - text_size.Width) / 2.0, (height - text_size.Height) / 2.0, text)

    def _fit(self, g, text, max_width):
        """Cut long captions with an ellipsis."""
        if g.MeasureString(self._font, text).Width <= max_width:
            return text
        while len(text) > 1 and g.MeasureString(self._font, text + "…").Width > max_width:
            text = text[:-1]
        return text.rstrip() + "…"


class JewelWeightWindow(object):
    def __init__(self):
        self._object_ids = []
        self._doc_serial = None
        self._warned = set()  # (kind, object id) notes already shown for this selection
        self._busy = False
        self._editing_id = None
        self._feed_width = -1
        self._font_small = _font(8)
        self._font_bold = _font(9, bold=True)
        self._font_title = _font(10, bold=True)

        self._storage = storage.Storage()
        self._settings, settings_notice = self._storage.load_settings()
        self._history, history_notice = self._storage.load_history()
        self.form = self._build_form()

        notices = [text for text in (settings_notice, history_notice) if text]
        if notices:
            self._add([(history.KIND_WARNING, text) for text in notices])
        else:
            self._render_feed()

    # --- window -----------------------------------------------------------

    def _build_form(self):
        form = forms.Form()
        form.Title = "JewelWeight " + __version__
        form.Padding = drawing.Padding(10)
        form.Resizable = True
        form.ShowInTaskbar = False
        form.BackgroundColor = _color(theme.BACKGROUND)
        form.ClientSize = drawing.Size(660, 500)
        form.MinimumSize = drawing.Size(580, 440)

        self._calc_page = self._build_calc_page()
        self._settings_page = self._build_settings_page()
        self._page_host = forms.Panel()
        self._tab_calc = _ColorButton("Расчёт", theme.TAB_ACTIVE,
                                      self._on(self._show_page, _PAGE_CALC), height=28, width=120)
        self._tab_settings = _ColorButton("Настройки", theme.TAB_INACTIVE,
                                          self._on(self._show_page, _PAGE_SETTINGS),
                                          height=28, width=120)
        header = _hbox(_cell(self._tab_calc.control, False),
                       _cell(self._tab_settings.control, False), _cell(_spacer(), True))
        form.Content = _table([
            _row(header),
            _row(_separator(vertical=False)),
            _row(self._page_host, scale_height=True),
        ], spacing=8)
        self._show_page(_PAGE_CALC)
        form.Closed += self._on_closed
        return form

    def _show_page(self, page):
        is_calc = page == _PAGE_CALC
        self._page_host.Content = self._calc_page if is_calc else self._settings_page
        self._tab_calc.set_style(theme.TAB_ACTIVE if is_calc else theme.TAB_INACTIVE)
        self._tab_settings.set_style(theme.TAB_INACTIVE if is_calc else theme.TAB_ACTIVE)

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

    # --- calculation page -------------------------------------------------

    def _build_calc_page(self):
        row = _row(_cell(self._build_left(), False), _cell(_separator(vertical=True), False),
                   _cell(self._build_right(), True), scale_height=True)
        return _table([row], spacing=10)

    def _build_left(self):
        select_button = _ColorButton("SELECT OBJECTS", theme.SELECT, self._on(self._select_objects),
                                     height=_SELECT_BUTTON_HEIGHT, font=_font(10, bold=True))
        grid = _table([_row(*[self._metal_button(metal_id) for metal_id in row_ids])
                       for row_ids in metals.GOLD_GRID])
        self._custom_scroll = _scrollable(theme.BACKGROUND)
        self._render_custom_buttons()
        left = _table([
            _row(select_button.control),
            _row(grid),
            _row(self._metal_button(metals.FINE_GOLD_ID)),
            _row(self._metal_button(metals.SILVER_ID)),
            _row(_label("Свой металл:", theme.TEXT_DIM, self._font_small)),
            _row(self._custom_scroll, scale_height=True),  # scrolls instead of growing the window
        ])
        left.Width = _LEFT_WIDTH
        return left

    def _metal_button(self, metal_id):
        metal = self._settings.get_metal(metal_id)
        return _ColorButton(metal.label, theme.METALS[metal_id],
                            self._on(self._calculate, metal_id)).control

    def _render_custom_buttons(self):
        alloys = self._settings.custom_alloys()
        rows = [_row(_ColorButton(alloy.label, theme.CUSTOM_ALLOY,
                                  self._on(self._calculate, alloy.id)).control)
                for alloy in alloys]
        if not alloys:
            rows.append(_row(_label("Пока нет — добавьте в «Настройках».",
                                    theme.TEXT_DIM, self._font_small)))
        rows.append(_row(_spacer(), scale_height=True))
        self._custom_scroll.Content = _table(rows)

    def _build_right(self):
        self._feed = _scrollable(theme.PANEL)
        self._feed.SizeChanged += self._on_feed_resized
        self._copy_button = _ColorButton("Копировать", theme.NEUTRAL, self._on(self._copy_last))
        clear_button = _ColorButton("Очистить", theme.NEUTRAL, self._on(self._clear))
        buttons = _table([_row(self._copy_button.control, clear_button.control)])
        return _table([_row(self._feed, scale_height=True), _row(buttons)])

    # --- message feed (chat-like: newest at the bottom) ---------------------

    def _render_feed(self):
        rows = [_row(_spacer(), scale_height=True)]  # pushes messages down to the buttons
        entries = self._history.entries
        if not entries:
            rows.append(_row(_label("Выберите объекты и нажмите кнопку металла.",
                                    theme.TEXT_DIM, self._font_small)))
        rows += [_row(self._message_card(entry)) for entry in entries]
        table = _table(rows)
        table.Padding = drawing.Padding(8, 8, 2, 8)
        if self._feed_width > 0:
            table.Width = self._feed_width  # makes long messages wrap
        table.SizeChanged += self._on_feed_content_resized
        self._feed.Content = table
        self._scroll_feed_to_end()

    def _message_card(self, entry):
        style = theme.MESSAGES.get(entry["kind"], theme.MESSAGES[history.KIND_INFO])
        label = _label(entry["text"], style.text)
        label.Wrap = forms.WrapMode.Word
        if entry["kind"] == history.KIND_RESULT:
            label.Font = _font(10, bold=True)
        card = forms.Panel()
        card.Padding = drawing.Padding(8, 6)
        card.BackgroundColor = _color(style.background)
        card.Content = label
        return card

    def _scroll_feed_to_end(self):
        # Larger than any content: the scroll offset is clamped to the end.
        self._feed.ScrollPosition = drawing.Point(0, 10000000)

    def _on_feed_content_resized(self, sender, e):
        self._scroll_feed_to_end()

    def _on_feed_resized(self, sender, e):
        width = self._feed.Width - _SCROLLBAR_ALLOWANCE
        if width > 50 and width != self._feed_width:
            self._feed_width = width
            if self._feed.Content is not None:
                self._feed.Content.Width = width

    def _add(self, block):
        self._history.add_block(block)
        self._render_feed()
        self._save_history()

    def _save_history(self):
        try:
            self._storage.save_history(self._history)
        except calc.UserError as err:
            Rhino.RhinoApp.WriteLine("JewelWeight: " + str(err))

    # --- settings page ----------------------------------------------------

    def _build_settings_page(self):
        self._standard_host = forms.Panel()
        self._custom_host = forms.Panel()
        self._render_standard_section()
        self._render_custom_section()
        content = _table([
            _row(self._standard_host),
            _row(self._custom_host),
            _row(self._build_editor()),
            _row(_spacer(), scale_height=True),
        ], spacing=16)
        content.Padding = drawing.Padding(2, 2, _SCROLLBAR_ALLOWANCE, 2)
        page = _scrollable(theme.BACKGROUND)
        page.Content = content
        return page

    def _render_standard_section(self):
        reset = _ColorButton("Сбросить стандартные", theme.NEUTRAL, self._on(self._reset_standard),
                             height=_SMALL_BUTTON_HEIGHT, width=170, font=_font(8.5))
        rows = [_row(_hbox(_cell(_label("Стандартные металлы", font=self._font_title), True),
                           _cell(reset.control, False)))]
        rows += [_row(self._standard_metal_row(metal)) for metal in self._settings.standard_metals()]
        self._standard_host.Content = _table(rows, spacing=8)

    def _standard_metal_row(self, metal):
        box = _text_box(settings_mod.format_density(metal.density), width=70)
        box.TextChanged += self._density_handler(metal.id, box)
        line = _hbox(
            _cell(_label(metal.label, font=self._font_bold, width=110), False),
            _cell(_label("{0}, проба {1}".format(metal.name, metal.fineness), theme.TEXT_DIM), True),
            _cell(box, False),
            _cell(_label("г/см³", theme.TEXT_DIM), False))
        note = _label(_STANDARD_NOTE, theme.TEXT_DIM, self._font_small)
        return _table([_row(line), _row(note)], spacing=1)

    def _render_custom_section(self):
        rows = [_row(_label("Свои сплавы", font=self._font_title))]
        alloys = self._settings.custom_alloys()
        for alloy in alloys:
            edit = _ColorButton("Изменить", theme.NEUTRAL, self._on(self._start_edit, alloy.id),
                                height=_SMALL_BUTTON_HEIGHT, width=90, font=_font(8.5))
            delete = _ColorButton("Удалить", theme.DANGER, self._on(self._delete_alloy, alloy.id),
                                  height=_SMALL_BUTTON_HEIGHT, width=80, font=_font(8.5))
            density = "{0} г/см³".format(settings_mod.format_density(alloy.density))
            rows.append(_row(_hbox(
                _cell(_label(alloy.label, font=self._font_bold), True),
                _cell(_label(density, theme.TEXT_DIM, width=90), False),
                _cell(edit.control, False),
                _cell(delete.control, False))))
        if not alloys:
            rows.append(_row(_label("Пока нет своих сплавов — добавьте ниже.", theme.TEXT_DIM)))
        self._custom_host.Content = _table(rows, spacing=6)

    def _build_editor(self):
        self._editor_title = _label("Добавить свой сплав", font=self._font_title)
        self._name_box = _text_box()
        self._fineness_box = _text_box(width=90)
        self._density_box = _text_box(width=90, placeholder="13.5")
        self._save_button = _ColorButton("Добавить", theme.SELECT, self._on(self._save_alloy),
                                         height=28, width=130)
        self._cancel_button = _ColorButton("Отмена", theme.NEUTRAL, self._on(self._reset_editor),
                                           height=28, width=90)
        self._cancel_button.control.Visible = False
        self._editor_status = _label("", theme.TEXT_DIM)

        def field(caption, box, suffix=None):
            cells = [_cell(_label(caption, theme.TEXT_DIM, width=_CAPTION_WIDTH), False)]
            if suffix is None:
                cells.append(_cell(box, True))
            else:
                cells += [_cell(box, False), _cell(_label(suffix, theme.TEXT_DIM), False),
                          _cell(_spacer(), True)]
            return _row(_hbox(*cells))

        return _table([
            _row(self._editor_title),
            field("Название", self._name_box),
            field("Проба", self._fineness_box, "необязательно"),
            field("Плотность", self._density_box, "г/см³"),
            _row(_hbox(_cell(self._save_button.control, False),
                       _cell(self._cancel_button.control, False), _cell(_spacer(), True))),
            _row(self._editor_status),
        ], spacing=6)

    def _density_handler(self, metal_id, box):
        """Live validation and autosave of a standard metal density."""
        def handler(sender, e):
            try:
                self._apply_density(metal_id, box)
            except Exception:
                self._report_internal_error()
        return handler

    def _apply_density(self, metal_id, box):
        try:
            density = settings_mod.parse_density(box.Text)
        except calc.UserError as err:
            box.BackgroundColor = _color(theme.INPUT_ERROR)
            box.ToolTip = str(err)
            return
        box.BackgroundColor = _color(theme.INPUT)
        box.ToolTip = ""
        self._settings.set_density(metal_id, density)
        self._persist_settings()

    def _save_alloy(self):
        values = (self._name_box.Text, self._fineness_box.Text, self._density_box.Text)
        try:
            if self._editing_id:
                alloy = self._settings.update_alloy(self._editing_id, *values)
                message = "Сохранено: «{0}».".format(alloy.label)
            else:
                alloy = self._settings.add_alloy(*values)
                message = "Добавлено: «{0}» — кнопка есть на вкладке «Расчёт».".format(alloy.label)
        except calc.UserError as err:
            self._set_status(str(err), error=True)
            return
        self._reset_editor()
        if self._persist_settings():
            self._set_status(message)
        self._refresh_alloys()

    def _start_edit(self, alloy_id):
        alloy = self._settings.get_metal(alloy_id)
        self._editing_id = alloy_id
        self._name_box.Text = alloy.name
        self._fineness_box.Text = alloy.fineness
        self._density_box.Text = settings_mod.format_density(alloy.density)
        self._editor_title.Text = "Изменить сплав «{0}»".format(alloy.label)
        self._save_button.set_text("Сохранить")
        self._cancel_button.control.Visible = True
        self._set_status("")
        self._name_box.Focus()

    def _reset_editor(self):
        self._editing_id = None
        self._name_box.Text = ""
        self._fineness_box.Text = ""
        self._density_box.Text = ""
        self._editor_title.Text = "Добавить свой сплав"
        self._save_button.set_text("Добавить")
        self._cancel_button.control.Visible = False
        self._set_status("")

    def _delete_alloy(self, alloy_id):
        alloy = self._settings.get_metal(alloy_id)
        if not self._confirm("Удалить сплав «{0}»?".format(alloy.label)):
            return
        self._settings.remove_alloy(alloy_id)
        if self._editing_id == alloy_id:
            self._reset_editor()
        if self._persist_settings():
            self._set_status("Удалено: «{0}».".format(alloy.label))
        self._refresh_alloys()

    def _reset_standard(self):
        if not self._confirm("Вернуть стандартные плотности для всех стандартных металлов?"):
            return
        self._settings.reset_standard()
        if self._persist_settings():
            self._set_status("Стандартные плотности восстановлены.")
        self._render_standard_section()

    def _refresh_alloys(self):
        self._render_custom_section()
        self._render_custom_buttons()

    def _persist_settings(self):
        try:
            self._storage.save_settings(self._settings)
            return True
        except calc.UserError as err:
            self._set_status(str(err), error=True)
            return False

    def _set_status(self, text, error=False):
        self._editor_status.Text = text
        self._editor_status.TextColor = _color(theme.TEXT_ERROR if error else theme.TEXT_OK)

    def _confirm(self, text):
        answer = forms.MessageBox.Show(self.form, text, "JewelWeight",
                                       forms.MessageBoxButtons.YesNo, forms.MessageBoxType.Question)
        return answer == forms.DialogResult.Yes

    # --- event plumbing ---------------------------------------------------

    def _on(self, action, *args):
        """Wrap an action as a button callback with error reporting."""
        return lambda: self._run(action, *args)

    def _run(self, action, *args):
        if self._busy:  # e.g. a metal button clicked while picking objects
            return
        self._busy = True
        try:
            action(*args)
        except calc.UserError as err:
            self._add([(history.KIND_ERROR, str(err))])
        except Exception:
            self._report_internal_error()
        finally:
            self._busy = False

    def _report_internal_error(self):
        details = traceback.format_exc()
        Rhino.RhinoApp.WriteLine("JewelWeight: внутренняя ошибка\n" + details)
        text = "Ошибка программы: {0}\nПодробности — в командной строке Rhino (F2).".format(
            details.strip().splitlines()[-1])
        self._add([(history.KIND_ERROR, text)])
        self._set_status("Ошибка программы — подробности в командной строке Rhino (F2).",
                         error=True)

    # --- calculation actions ----------------------------------------------

    def _select_objects(self):
        doc = rhino_adapter.active_doc()
        ids = rhino_adapter.pick_objects()
        if not ids:
            return  # cancelled: keep the previous selection
        self._object_ids = ids
        self._doc_serial = doc.RuntimeSerialNumber
        self._warned = set()

        evaluation = self._evaluate(doc)
        if evaluation.problems:
            self._report_problems(doc, evaluation)
            return
        block = [(history.KIND_INFO, calc.selection_message(
            len(evaluation.valid_ids), evaluation.volume_mm3))]
        block += self._object_notes(evaluation)
        if len(evaluation.valid_ids) > 1:
            block.append((history.KIND_WARNING, calc.OVERLAP_WARNING))
        self._add(block)

    def _calculate(self, metal_id):
        metal = self._settings.get_metal(metal_id)
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
        notes += self._object_notes(evaluation)

        weight = calc.weight_grams(evaluation.volume_mm3, metal.density)
        result = calc.format_result(metal.label, weight, len(evaluation.valid_ids))
        self._add([(history.KIND_RESULT, result)] + notes)
        Rhino.RhinoApp.WriteLine("JewelWeight: " + result)

    def _copy_last(self):
        text = self._history.last_result()
        if text is None:
            self._copy_button.flash("Нет результата")
            return
        clipboard = forms.Clipboard()
        clipboard.Text = text
        self._copy_button.flash("Скопировано ✓")

    def _clear(self):
        self._history.clear()
        self._render_feed()
        self._save_history()

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

    def _object_notes(self, evaluation):
        """Per-object warnings, each shown once per selection."""
        notes = []
        for kind, ids, make_message in (
                ("inverted", evaluation.inverted_ids, calc.inverted_message),
                ("repaired", evaluation.repaired_ids, calc.repaired_message)):
            new = [(kind, str(i)) for i in ids if (kind, str(i)) not in self._warned]
            if new:
                self._warned.update(new)
                notes.append((history.KIND_WARNING, make_message(len(ids))))
        return notes
