"""JewelWeight: jewelry weight calculator for Rhino 8.

Pure-Python modules (no Rhino imports, testable outside Rhino):
compat, metals, calc, history, settings, storage, theme.
Rhino-dependent modules: rhino_adapter, ui.
"""

# Keep equal to the Version in the ScriptEditor project (docs/BUILD.md).
__version__ = "1.0.0"

# Dependencies first, so reloaded modules see fresh versions of what they use.
_RELOAD_ORDER = ("compat", "metals", "calc", "history", "theme", "settings", "storage",
                 "rhino_adapter", "ui")


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
