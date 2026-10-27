# PROGRESS

## Goal
Плагин JewelWeight для Rhino 8: вес ювелирных изделий по объёму. Три фазы (docs/SPEC.md, раздел «Изменения» в конце).

## Done
- Фаза 1 (7b111b7): окно, выбор, проверки, объём, единицы, вес.
- Фаза 2 (406b7df): тёмная тема, вкладки, настройки и свои сплавы, JSON в %APPDATA%\JewelWeight, история, очистка копии STL.
- Фаза 3 (c820625, 279a853): zip-установщик (install.py / uninstall.py, псевдоним `JewelWeight`), tools/make_package.py, SVG-иконки в пакете для кнопки на панели. Пользователь подтвердил «работает».
- Релиз v1.0.0 с `JewelWeight-1.0.0.zip` в GitHub Releases (github.com/Khanapin-T/rhino-jewelweight, private).
- 65 тестов логики проходят.

## Next steps
- Проект завершён (кнопка на панели проверена пользователем). Возможные доработки: SubD → расчёт через ToBrep; автоматическое создание кнопки (.rui); сборка .yak на ПК с Rhino с интернетом.
- Новая версия: поднять `__version__` → тесты → `python tools/make_package.py` → коммит, push → `gh release create v<версия> dist/...zip`.

## Key decisions
- `MIN_RHINO_VERSION = (8, 0, 0)` = любой Rhino 8.
- Установка: zip + install.py, а не .yak. Сборке .yak нужен Rhino с доступом к api.nuget.org, на ПК пользователя его нет. Проект ScriptEditor (`JewelWeight.rhproj`, ID ee22e9dc-…) сохранён на будущее.
- Хранятся только изменённые плотности стандартных металлов.
- Псевдоним: `! _-ScriptEditor _Run "%APPDATA%\JewelWeight\app\commands\JewelWeight.py"`; макрос кнопки: `! JewelWeight`.

## Gotchas
- Модули кешируются на сеанс Rhino: после обновления закрыть окно или перезапустить Rhino.
- Enum со значением `None`: только `ui._enum_member` (через getattr не работает).
- Конвертер иконок ScriptEditor не масштабирует polyline: SVG рисовать сразу 48×48 с fill-dark / stroke-dark.
- Если ставить .yak, сначала uninstall.py: псевдоним перекроет команду плагина.
