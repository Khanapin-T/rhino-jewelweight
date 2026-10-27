#! python3
"""JewelWeight installer. Run once in Rhino 8: ScriptEditor -> File -> Open -> Run.

Copies the program to %APPDATA%\\JewelWeight\\app and adds the JewelWeight
command alias. Settings and history in %APPDATA%\\JewelWeight stay untouched,
so running a newer installer is also how the plugin is updated.
"""

import os
import shutil

ALIAS = "JewelWeight"
APP_FOLDER_NAME = "app"
_WINDOW_STICKY_KEY = "JewelWeight.window"


def app_folder():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "JewelWeight", APP_FOLDER_NAME)


def package_folder():
    return os.path.dirname(os.path.abspath(__file__))


def copy_app(source, target):
    """Replace the target app folder with a fresh copy of source."""
    if os.path.basename(os.path.normpath(target)) != APP_FOLDER_NAME:
        raise ValueError("Unexpected install folder: " + target)  # never wipe anything else
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def command_macro(target):
    script = os.path.join(target, "commands", "JewelWeight.py")
    return '! _-ScriptEditor _Run "{0}"'.format(script)


def close_open_window():
    """Close a running JewelWeight window so the new code is loaded next time."""
    import scriptcontext as sc

    window = sc.sticky.get(_WINDOW_STICKY_KEY)
    if window is not None:
        try:
            window.form.Close()
        except Exception:
            pass  # already closed


def report(text):
    import Eto.Forms as forms
    import Rhino

    Rhino.RhinoApp.WriteLine(text)
    forms.MessageBox.Show(text, "JewelWeight", forms.MessageBoxType.Information)


def main():
    import Rhino

    if Rhino.RhinoApp.Version.Major != 8:
        report("JewelWeight работает только в Rhino 8. Установка отменена.")
        return
    source = os.path.join(package_folder(), APP_FOLDER_NAME)
    if not os.path.isdir(source):
        report("Рядом с install.py нет папки app. Распакуйте архив целиком и запустите install.py снова.")
        return

    target = app_folder()
    close_open_window()
    copy_app(source, target)

    aliases = Rhino.ApplicationSettings.CommandAliasList
    macro = command_macro(target)
    if aliases.IsAlias(ALIAS):
        aliases.SetMacro(ALIAS, macro)
    else:
        aliases.Add(ALIAS, macro)

    report("JewelWeight установлен.\n\nВведите команду JewelWeight.\n"
           "Программа: {0}\nСвои сплавы и настройки сохранены.".format(target))


if __name__ == "__main__":
    main()
