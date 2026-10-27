"""Rhino version check (pure Python)."""

REQUIRED_MAJOR = 8

# Minimum supported Rhino build as (major, service release, build date code),
# e.g. Rhino 8 SR12 "8.12.24282.07002" -> (8, 12, 24282).
# Any Rhino 8: everything used here (CPython 3, Eto, rhinoscriptsyntax,
# VolumeMassProperties) ships with 8.0. Keep it equal to the Build Target
# chosen in ScriptEditor -> Publish Project; raise it only if an older
# service release turns out to break the plugin.
MIN_RHINO_VERSION = (8, 0, 0)

_UPDATE_HINT = "Обновите Rhino: Help → Check for Updates, затем перезапустите Rhino."


def _normalize(version):
    parts = tuple(int(part) for part in version)
    return (parts + (0, 0, 0))[:3]


def describe_version(version):
    """Human-readable version, e.g. 'Rhino 8 SR12 (8.12.24282)'."""
    major, minor, build = _normalize(version)
    text = "Rhino {0}".format(major)
    if minor:
        text += " SR{0}".format(minor)
    if build:
        text += " ({0}.{1}.{2})".format(major, minor, build)
    return text


def check_rhino_version(installed, minimum=MIN_RHINO_VERSION, required_major=REQUIRED_MAJOR):
    """Return None if the installed Rhino is supported, else a message in Russian."""
    installed = _normalize(installed)
    minimum = _normalize(minimum)
    if installed[0] == required_major and installed >= minimum:
        return None

    need = "Нужна версия: {0} или новее.".format(describe_version(minimum))
    have = "Установлена: {0}.".format(describe_version(installed))
    if installed[0] == required_major:
        title = "JewelWeight требует более новую версию Rhino {0}.".format(required_major)
        advice = _UPDATE_HINT
    elif installed[0] < required_major:
        title = "JewelWeight работает только в Rhino {0}.".format(required_major)
        advice = ("Установите Rhino {0} и обновите его до последней версии: "
                  "Help → Check for Updates.".format(required_major))
    else:
        title = "Эта версия JewelWeight работает только в Rhino {0}.".format(required_major)
        advice = ("Запустите плагин в Rhino {0} (последнюю версию даёт "
                  "Help → Check for Updates).".format(required_major))
    return "\n".join((title, need, have, advice))
