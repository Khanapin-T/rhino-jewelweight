"""JewelWeight: jewelry weight calculator for Rhino 8.

Pure-Python modules (no Rhino imports, testable outside Rhino):
compat, metals, calc, history.
Rhino-dependent modules: rhino_adapter, ui.
"""

__version__ = "0.1.0"

# Dependencies first, so reloaded modules see fresh versions of what they use.
_RELOAD_ORDER = ("compat", "metals", "calc", "history", "rhino_adapter", "ui")


def reload_modules():
    """Reload already imported submodules.

    ScriptEditor keeps imported modules cached for the whole Rhino session,
    so without this, edits to library files are ignored until Rhino restarts.
    """
    import importlib
    import sys

    for name in _RELOAD_ORDER:
        module = sys.modules.get(__name__ + "." + name)
        if module is not None:
            importlib.reload(module)
