#! python3
"""JewelWeight uninstaller. Run in Rhino 8: ScriptEditor -> File -> Open -> Run.

Removes the JewelWeight command alias and the program folder. Settings and
history (custom alloys, densities) are kept in %APPDATA%\\JewelWeight.
"""

import os
import shutil

ALIAS = "JewelWeight"
APP_FOLDER_NAME = "app"
_WINDOW_STICKY_KEY = "JewelWeight.window"


def main():
    import Eto.Forms as forms
    import Rhino
    import scriptcontext as sc

    window = sc.sticky.get(_WINDOW_STICKY_KEY)
    if window is not None:
        try:
            window.form.Close()
        except Exception:
            pass  # already closed

    aliases = Rhino.ApplicationSettings.CommandAliasList
    if aliases.IsAlias(ALIAS):
        aliases.Delete(ALIAS)

    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "JewelWeight")
    app = os.path.join(base, APP_FOLDER_NAME)
    if os.path.isdir(app):
        shutil.rmtree(app)

    text = ("JewelWeight удалён.\n\nСвои сплавы и настройки остались в {0}. "
            "Если они не нужны, удалите эту папку вручную.".format(base))
    Rhino.RhinoApp.WriteLine(text)
    forms.MessageBox.Show(text, "JewelWeight", forms.MessageBoxType.Information)


if __name__ == "__main__":
    main()
