#! python3
"""JewelWeight command: opens the jewelry weight calculator window."""

import os
import sys

import Rhino


def _add_dev_library_path():
    """When run from the repository in ScriptEditor, use ../lib next to this file.

    In a built plugin the library is already importable and this is a no-op.
    """
    script = globals().get("__file__")
    if not script:
        return
    lib = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(script)), "..", "lib"))
    if os.path.isdir(os.path.join(lib, "jewelweight")) and lib not in sys.path:
        sys.path.insert(0, lib)


def _show_message(text):
    import Eto.Forms as forms

    Rhino.RhinoApp.WriteLine(text)
    forms.MessageBox.Show(text, "JewelWeight", forms.MessageBoxType.Warning)


def main():
    _add_dev_library_path()
    import jewelweight
    from jewelweight import compat

    version = Rhino.RhinoApp.Version
    error = compat.check_rhino_version((version.Major, version.Minor, version.Build))
    if error:
        _show_message(error)
        return

    from jewelweight import ui

    if ui.focus_existing():
        return
    jewelweight.reload_modules()  # pick up edited library files (development)
    ui.open_window()


main()
