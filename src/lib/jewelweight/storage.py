"""Settings and history files in %APPDATA%\\JewelWeight (pure Python).

Why JSON in AppData and not Rhino PersistentSettings: PersistentSettings
belong to a plugin instance, which a script run from ScriptEditor does not
have, and they are tied to the plugin id. A plain UTF-8 JSON file works the
same in development and in the built plugin, survives plugin updates and
reinstalls (the .yak package folder is replaced, AppData is not), is easy
to migrate by schema_version, and can be copied to another computer as is.
"""

import collections
import datetime
import json
import os
import shutil

from . import calc
from . import history
from . import settings as settings_mod

FOLDER_NAME = "JewelWeight"
SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"

SETTINGS_SCHEMA_VERSION = 1
HISTORY_SCHEMA_VERSION = 1

# {from_version: function(data) -> data in the format of from_version + 1}.
# When the format changes: add a step here and bump the schema version.
SETTINGS_MIGRATIONS = {}
HISTORY_MIGRATIONS = {}

ReadResult = collections.namedtuple("ReadResult", "data notice reset")


class SchemaError(ValueError):
    """The file has no usable schema_version or cannot be migrated."""


def default_folder():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, FOLDER_NAME)


def migrate(data, current_version, migrations):
    """Bring data up to current_version, one migration step at a time."""
    if not isinstance(data, dict):
        raise SchemaError("root is not an object")
    version = data.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise SchemaError("missing schema_version")
    if version > current_version:
        raise SchemaError("unknown schema_version {0}".format(version))
    while version < current_version:
        step = migrations.get(version)
        if step is None:
            raise SchemaError("no migration from schema_version {0}".format(version))
        data = step(dict(data))
        version += 1
        data["schema_version"] = version
    return data


def write_json(path, data):
    """Write UTF-8 JSON atomically (a crash never leaves a half-written file)."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.replace(temp_path, path)


def backup_file(path):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = "{0}.broken-{1}".format(path, stamp)
    shutil.copy2(path, backup_path)
    return backup_path


def read_versioned(path, current_version, migrations, what):
    """Read and migrate a JSON file with schema_version.

    Missing file: no data, no notice. Broken file or unknown version: a
    backup copy is made and reset is True, so the caller starts from defaults.
    """
    if not os.path.exists(path):
        return ReadResult(None, None, False)
    try:
        with open(path, "r", encoding="utf-8-sig") as stream:  # tolerate a BOM from Notepad
            data = json.load(stream)
        return ReadResult(migrate(data, current_version, migrations), None, False)
    except OSError as err:
        return ReadResult(None, "Не удалось прочитать {0}: {1}".format(path, err), False)
    except (ValueError, KeyError, TypeError, AttributeError):
        # ValueError covers bad JSON, bad UTF-8 and SchemaError.
        try:
            backup = backup_file(path)
            where = "Копия старого файла: {0}".format(backup)
        except OSError:
            where = "Сделать копию старого файла не удалось."
        notice = "{0} повреждён(а) или неизвестной версии — сброшено к стандартным. {1}".format(
            what, where)
        return ReadResult(None, notice, True)


class Storage(object):
    def __init__(self, folder=None):
        self.folder = folder or default_folder()
        self.settings_path = os.path.join(self.folder, SETTINGS_FILE)
        self.history_path = os.path.join(self.folder, HISTORY_FILE)

    def load_settings(self):
        """Return (Settings, notice or None)."""
        result = read_versioned(self.settings_path, SETTINGS_SCHEMA_VERSION,
                                SETTINGS_MIGRATIONS, "Файл настроек")
        if result.data is None:
            loaded = settings_mod.Settings()
        else:
            loaded = settings_mod.Settings.from_dict(result.data)
        if result.reset:
            self._try_save(self.save_settings, loaded)
        return loaded, result.notice

    def save_settings(self, settings):
        data = {"schema_version": SETTINGS_SCHEMA_VERSION}
        data.update(settings.to_dict())
        self._write(self.settings_path, data, "настройки")

    def load_history(self):
        """Return (History, notice or None)."""
        result = read_versioned(self.history_path, HISTORY_SCHEMA_VERSION,
                                HISTORY_MIGRATIONS, "Файл истории")
        entries = result.data.get("entries") if result.data is not None else None
        loaded = history.History.from_list(entries if isinstance(entries, list) else [])
        if result.reset:
            self._try_save(self.save_history, loaded)
        return loaded, result.notice

    def save_history(self, output_history):
        data = {"schema_version": HISTORY_SCHEMA_VERSION, "entries": output_history.to_list()}
        self._write(self.history_path, data, "историю")

    @staticmethod
    def _write(path, data, what):
        try:
            write_json(path, data)
        except OSError as err:
            raise calc.UserError("Не удалось сохранить {0}: {1}".format(what, err))

    @staticmethod
    def _try_save(save, value):
        try:
            save(value)
        except calc.UserError:
            pass  # the load notice already tells the user what happened
