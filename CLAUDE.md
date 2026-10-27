# JewelWeight — плагин Rhino 8 для расчёта веса ювелирных изделий

Полная постановка: [docs/SPEC.md](docs/SPEC.md). Текущий статус: [PROGRESS.md](PROGRESS.md).

## Стек
- Rhino 8 (Windows), Python 3 (CPython 3.9 из ScriptEditor), UI на Eto.Forms.
- Только RhinoCommon, rhinoscriptsyntax, Eto.Forms и стандартная библиотека Python. Без pip.
- .rhp/.yak собирает пользователь сам (ScriptEditor → Create Project / Publish). Установка только через .yak.

## Структура
- `src/commands/JewelWeight.py` — скрипт-команда: проверка версии Rhino, открытие окна.
- `src/lib/jewelweight/` — библиотека (пакет с `__init__.py`).
  - Чистый Python, без Rhino: `compat` (версия), `metals` (плотности), `calc` (проверки, единицы, вес, тексты), `history`.
  - С Rhino: `rhino_adapter` (выбор, геометрия → `calc.ObjectCheck`), `ui` (окно Eto).
- `tests/` — unittest для чистых модулей: `python -X utf8 -m unittest discover -s tests -v`.

## Правила
- Rhino я запустить не могу: пишу код, пользователь запускает его в ScriptEditor и присылает ошибки. Никогда не утверждать, что код проверен в Rhino.
- Если не уверен в методе API, сверяться с developer.rhino3d.com; методы не выдумывать.
- Логика отдельно от UI. В чистых модулях нельзя импортировать Rhino, Eto и scriptcontext.
- Код совместим с Python 3.9: без `match` и без `X | None`.
- Комментарии в коде на английском. Интерфейс на русском, кроме кнопки «SELECT OBJECTS».
- Настройки и история в UTF-8; в настройках `schema_version` с миграцией; битый или неизвестный файл → бэкап и сброс к стандартным.
- Работаем по фазам (см. SPEC). После каждой фазы остановиться и ждать «работает» или ошибку.
- Коммит только после «работает». Без Co-Authored-By и любых упоминаний AI.
- Субагентов не используем: проект маленький, всё делаю сам (inline).

## Pythonnet / Eto: заметки
- `TableCell`/`TableRow` создавать явно (неявные преобразования Control → TableCell из Python не работают).
- Методы с out-параметрами возвращают кортеж: `mesh.IsManifold(True)` → `(ok, oriented, boundary)`.
- Модули кешируются на весь сеанс Rhino; команда вызывает `jewelweight.reload_modules()` перед открытием нового окна.
- Открытое окно хранится в `scriptcontext.sticky["JewelWeight.window"]`.
