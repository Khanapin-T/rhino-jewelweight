# PROGRESS

## Goal
Плагин JewelWeight для Rhino 8: вес ювелирных изделий по объёму. Три фазы (docs/SPEC.md, раздел «Изменения» в конце).

## Done
- Фаза 1 (7b111b7): окно, выбор, проверки, объём, единицы, вес.
- Фаза 2 (406b7df): тёмная тема, вкладки, настройки и свои сплавы, JSON в %APPDATA%\JewelWeight, история, очистка копии STL. Пользователь подтвердил «работает», STL считается.
- Фаза 3 (ждёт сборки пользователем): SVG-иконки light/dark, `src/shared/README.txt` для .yak, инструкция docs/BUILD.md, `__version__` 1.0.0.

## Next steps
1. Пользователь проверяет zip-установщик: `dist\JewelWeight-1.0.0.zip` → распаковать → `install.py` в ScriptEditor → команда `JewelWeight`.
2. После «работает»: коммит фазы 3 (installer, tools, icons, docs, `JewelWeight.rhproj`), push, затем `gh release create v1.0.0 dist/JewelWeight-1.0.0.zip` (github.com/Khanapin-T/rhino-jewelweight, private).
3. .yak через ScriptEditor отложен: сборке нужен Rhino с доступом к api.nuget.org, на ПК пользователя его нет.
3. Возможные доработки: SubD → расчёт через ToBrep; кнопка на панели через .rui.

## Key decisions
- `MIN_RHINO_VERSION = (8, 0, 0)` = любой Rhino 8; Build Target — самый ранний 8.x.
- Хранятся только изменённые плотности стандартных металлов.
- README для пакета кладётся через Shared/ (в .yak попадает в `shared/`).
- Версия 1.0.0 для первого выпуска; `__version__` синхронизировать с Version проекта вручную.

## Gotchas
- Не проверено: сборка через ScriptEditor, импорт библиотеки в собранном .rhp, иконки в Package Manager.
- Модули кешируются: закрыть окно → снова Run, чтобы подхватить код.
- Enum со значением `None`: только `ui._enum_member` (через getattr не работает).
