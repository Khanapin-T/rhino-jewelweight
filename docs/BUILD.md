# Сборка и установка JewelWeight

Пути ниже даны для репозитория `C:\Users\Tair\Desktop\Rhino-plugin`.

## Основной способ: zip-установщик
Интернет и ScriptEditor → Publish не нужны.

1. Поднимите `__version__` в `src\lib\jewelweight\__init__.py`, например `1.0.0` → `1.1.0`.
2. Прогоните тесты: `python -X utf8 -m unittest discover -s tests`.
3. Соберите архив: `python tools/make_package.py` → получится `dist\JewelWeight-<версия>.zip`.
4. Закоммитьте изменения и выложите архив в Releases на GitHub:
   ```
   git push
   gh release create v<версия> dist/JewelWeight-<версия>.zip --title "JewelWeight <версия>" --notes "Что изменилось"
   ```
5. На каждом компьютере: скачать zip из Releases (войдя в GitHub — репозиторий приватный), распаковать и запустить `install.py` в ScriptEditor. Порядок для пользователя описан в `installer\README.txt`, он же лежит в архиве.

Как это устроено: `install.py` копирует `app\` в `%APPDATA%\JewelWeight\app` (только эту папку, настройки рядом не трогает) и создаёт псевдоним `JewelWeight` → `! _-ScriptEditor _Run "...\app\commands\JewelWeight.py"`. Скрипт команды сам добавляет `app\lib` в `sys.path`.

Если когда-нибудь поставите собранный `.yak` (способ ниже), сначала запустите `uninstall.py`: псевдоним `JewelWeight` перекроет команду плагина.

## Другой способ: .rhp / .yak через ScriptEditor
Нужен Rhino 8 с доступом в интернет: при сборке Rhino скачивает пакеты с `api.nuget.org`.

## Что входит в проект
| В ScriptEditor | Файл в репозитории |
|---|---|
| Commands/ | `src\commands\JewelWeight.py` |
| Libraries/ (Python 3) | папка `src\lib\jewelweight` (с `__init__.py`) |
| Shared/ | `src\shared\README.txt` — короткий README на русском, внутри .yak лежит в `shared/` |
| Иконки (светлая / тёмная тема) | `src\icons\jewelweight-light.svg`, `src\icons\jewelweight-dark.svg` |

## 1. Создать проект (один раз)
1. В Rhino 8 выполните `_ScriptEditor`.
2. File → **Create Project**. Сохраните как `C:\Users\Tair\Desktop\Rhino-plugin\JewelWeight.rhproj` — в корне репозитория.
3. В окне **Edit Project** (Rhino 8.32; в других версиях набор полей может отличаться):
   - **Name:** `JewelWeight`;
   - **Version:** `1.0` (должна совпадать с `__version__` в `src\lib\jewelweight\__init__.py`, сейчас `1.0.0`);
   - **Author:** кнопка Edit → добавьте себя (обязательное поле, без него сборка выдаёт «No Author»);
   - **Copyright:** кнопка Copyright заполнит автоматически;
   - **License:** оставьте пустым — тогда все права у автора;
   - **URL:** оставьте пустым — приватный репозиторий у других всё равно не откроется;
   - **Icon:** если в окне есть место под картинку, выберите там `src\icons\jewelweight-light.svg` (светлая) и `src\icons\jewelweight-dark.svg` (тёмная). Если его нет, пропустите: иконка видна только в Package Manager и на панели, на работу плагина она не влияет.
   - **Id** в окне может не показываться: он создаётся сам и хранится в `JewelWeight.rhproj` (`"id": "ee22e9dc-…"`). Это ID плагина, менять его нельзя.
4. **Save Changes**.

## 2. Добавить файлы в проект
1. Кнопка **+** в панели проекта → **Add Commands/** → `src\commands\JewelWeight.py`. Команда получит имя `JewelWeight` по имени файла.
2. Щёлкните по команде `JewelWeight` под `Commands/` → станет активным карандаш (**Edit**) справа от **+** в панели проекта → в **Edit Command** добавьте те же две SVG-иконки (светлую и тёмную). Если поля для иконки нет, пропустите этот шаг.
3. **+** → **Add Python 3 Library** → папка `src\lib\jewelweight`. В `Libraries/` должна появиться `jewelweight` с `__init__.py` внутри: скрипт команды импортирует её как `jewelweight`. Проект хранит ссылку на эту папку (`"base": "src/lib/jewelweight/"`), а не копию, поэтому правки кода попадают в сборку сами.
4. **+** → **Add Shared/** → `src\shared\README.txt`.
5. **Save Project**.
6. Закоммитьте `JewelWeight.rhproj` в git. В нём хранится ID плагина, и все следующие версии собираются только из этого файла.

## 3. Собрать .rhp и .yak
1. Перед сборкой прогоните тесты: `python -X utf8 -m unittest discover -s tests`.
2. File → **Publish Project**.
3. **Build Target:** самая ранняя доступная версия Rhino 8 для Windows. Так плагин встанет на любой Rhino 8; в коде минимальная версия тоже «любая 8.x» (`MIN_RHINO_VERSION` в `compat.py`).
4. **Build Path:** `C:\Users\Tair\Desktop\Rhino-plugin\build` — папка `build\` уже в `.gitignore`.
5. **Build Package**. Об успехе сообщит зелёная надпись внизу. Не нажимайте публикацию на сервер (Publish Target «McNeel Yak Server»): она выложит плагин в открытый каталог Rhino для всех.
6. Результат лежит в `build\rh8\`: файлы `.rhp` и `.yak`. Раздавать нужно только `.yak`.

## 4. Установить на чистом ПК
1. Должен быть установлен Rhino 8.
2. Откройте Rhino 8 и перетащите файл `.yak` в его окно. Rhino установит пакет.
3. Перезапустите Rhino.
4. Введите команду `JewelWeight`.
5. Проверить или удалить пакет можно командой `_PackageManager` → вкладка Installed. Настройки при удалении остаются в `%APPDATA%\JewelWeight`.
6. Кнопка на панели (по желанию): на любой панели инструментов → New Button → в Command впишите `_JewelWeight`.

Если на этом же ПК вы раньше запускали скрипт из ScriptEditor, ничего чистить не нужно: настройки и история общие.

## 5. Выпустить новую версию (ID не меняется)
1. ScriptEditor → File → **Open Project** → тот же `JewelWeight.rhproj`. **Не создавайте проект заново:** новый проект получит новый ID, и Rhino будет считать его другим плагином с той же командой.
2. Edit Project → поднимите **Version** (например 1.0 → 1.1) и такое же значение пропишите в `__version__` в `src\lib\jewelweight\__init__.py`.
3. Новые модули ничего добавлять не требуют: проект ссылается на папку `src\lib\jewelweight` целиком. Иконки, наоборот, хранятся внутри `.rhproj`: после изменения SVG удалите иконку в Edit Command и добавьте её заново.
4. Publish Project → Build Package.
5. Закоммитьте изменения, включая `.rhproj`.
6. Пользователи перетаскивают новый `.yak` в Rhino 8 поверх старого и перезапускают Rhino. Свои сплавы и плотности сохраняются: они хранятся в `%APPDATA%\JewelWeight`, а не в папке плагина.

## Если что-то не так
- **Build Target пустой, «Failed getting latest Rhino releases».** Для сборки Rhino должен скачивать пакеты с `api.nuget.org`. В логе ScriptEditor (`%USERPROFILE%\.rhinocode\logs\`) при этом видно `SocketException (10013)`. Причина — правило брандмауэра «Rhino 8», которое запрещает Rhino.exe выход в интернет. На время сборки отключите его: Брандмауэр Защитника Windows → Дополнительные параметры → Правила для исходящего подключения → «Rhino 8» → Отключить правило. Или в PowerShell от администратора: `Disable-NetFirewallRule -DisplayName "Rhino 8"`. Затем заново откройте Publish Project и соберите. После сборки включите правило обратно: `Enable-NetFirewallRule -DisplayName "Rhino 8"`. Плагину и установке `.yak` интернет не нужен.
- Ошибка `No module named 'jewelweight'` в собранном плагине — библиотека добавлена не той папкой: в `Libraries/` должна быть именно `jewelweight` с `__init__.py`.
- Полный текст любой ошибки плагин пишет в командную строку Rhino (F2).
