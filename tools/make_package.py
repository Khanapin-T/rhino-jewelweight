"""Build dist/JewelWeight-<version>.zip, the local installer package.

Usage: python tools/make_package.py
"""

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.path.join(ROOT, "src", "lib", "jewelweight")


def read_version():
    with open(os.path.join(LIBRARY, "__init__.py"), encoding="utf-8") as stream:
        match = re.search(r'^__version__ = "([^"]+)"', stream.read(), re.MULTILINE)
    if not match:
        raise RuntimeError("__version__ not found in jewelweight/__init__.py")
    return match.group(1)


def package_files():
    """(source path, path inside the package) pairs."""
    installer = os.path.join(ROOT, "installer")
    yield os.path.join(installer, "README.txt"), "README.txt"
    yield os.path.join(installer, "install.py"), "install.py"
    yield os.path.join(installer, "uninstall.py"), "uninstall.py"
    yield os.path.join(ROOT, "src", "commands", "JewelWeight.py"), "app/commands/JewelWeight.py"
    for name in sorted(os.listdir(LIBRARY)):
        if name.endswith(".py"):
            yield os.path.join(LIBRARY, name), "app/lib/jewelweight/" + name


def build(out_dir=os.path.join(ROOT, "dist")):
    version = read_version()
    top = "JewelWeight-{0}".format(version)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, top + ".zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, name in package_files():
            archive.write(source, top + "/" + name)
    return path


if __name__ == "__main__":
    built = build(*sys.argv[1:2])
    print(built)
