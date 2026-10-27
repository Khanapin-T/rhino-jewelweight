JewelWeight — расчёт веса ювелирных изделий (только Rhino 8)

УСТАНОВКА
1. Распакуйте архив целиком в любую папку.
2. В Rhino 8 введите команду _ScriptEditor.
3. В ScriptEditor: File → Open → install.py из распакованной папки → Run (зелёная кнопка или F5).
4. Введите команду JewelWeight.

КНОПКА НА ПАНЕЛИ (по желанию, один раз на каждом компьютере)
1. Правый щелчок по серой области любой панели инструментов → New Button... → откроется Button Editor.
2. В разделе левой кнопки мыши: Tooltip — JewelWeight, Command — ! JewelWeight
3. Стрелка рядом с квадратом картинки справа вверху → шестерёнка → File → Import… →
   %APPDATA%\JewelWeight\app\icons\jewelweight-light.svg (в нём есть цвета и для тёмной темы).
4. OK, OK.

ОБНОВЛЕНИЕ
Распакуйте новую версию и снова запустите install.py. Свои сплавы и плотности сохранятся.

УДАЛЕНИЕ
Так же запустите uninstall.py. Настройки останутся в %APPDATA%\JewelWeight.

Программа ставится в %APPDATA%\JewelWeight\app, настройки лежат в %APPDATA%\JewelWeight\settings.json.
