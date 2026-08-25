# LEDSetup

Окно на Windows для **одной** аналоговой RGB-ленты: нашли контроллер по Bluetooth, выбрали его, задали цвет всей полосе. Можно включить синхронизацию: лента roughly повторяет **оттенок** среднего цвета выбранного монитора на полной яркости.

Это не «умная» адресная лента и не несколько устройств. Вся полоса всегда **одного** цвета — не периметр и не разные зоны.

Комплект, на котором собрано: Smartbuy `SBL-RGBW-KIT-75`, контроллер Zengge LEDnetWF, вендорское приложение **ZENGGE**.

## Что уже работает

- Окно: поиск ленты → пикер цвета, вкл/выкл, GATT, настройки, **экран → лента**
- То же в терминале: `ledsetup menu` (пункт sync)
- Разовые команды: `scan`, `color`, `off`, `gatt`, `sync`

Цвет и выключение проверены глазами. Имя в Bluetooth может меняться — программа запоминает **адрес**.

## Запуск

Нужны Windows 10/11, **Python 3.11+**, включённый Bluetooth и [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/) (обычно уже стоит).

```powershell
cd app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
ledsetup
```

Если команда `python` не находится: `winget install Python.Python.3.12` и новый терминал.

Сначала экран «какая лента», затем цвет. Справа на экране цвета — тумблер «Экран → лента» и выбор монитора. Закройте **ZENGGE**, если лента не находится или не подключается — оно часто держит линк.

То же окно: `ledsetup gui`. Без установки скрипта: `python -m ledsetup`.

### Терминал и скрипты

```powershell
ledsetup menu
```

Один раз выбрать устройство (в списке `*` — похоже на LEDnetWF, это только подсказка):

```powershell
ledsetup scan
ledsetup scan --index 1
ledsetup scan --address E4:98:BB:6B:1A:AC
```

Адрес сохраняется в `%LOCALAPPDATA%\ledsetup\`. Дальше:

```powershell
ledsetup color 255 0 0
ledsetup color 0 255 0
ledsetup color 0 0 255
ledsetup off
ledsetup gatt
ledsetup sync
ledsetup sync --seconds 30 --monitor 1
```

`sync` крутит оттенок среднего цвета выбранного монитора **на полной яркости**, пока не Ctrl+C или не кончатся `--seconds`. Чёрный кадр остаётся off. Лента после остановки остаётся на последнем цвете. Другой адрес разово: `--address …`. Команда `on` есть, на этом ките её не проверяли. Кадр HSV (`--hsv`) — гипотеза, пикер в окне его не шлёт.

Если Windows запрещает захват экрана, программа пишет об этом явно — не красит ленту молча в чёрный.

## Железо

| | |
|--|--|
| Комплект | Smartbuy `SBL-RGBW-KIT-75` |
| Связь | Bluetooth Low Energy |
| Питание | 12 В / 2 А, до 24 Вт |
| Выход | `+ / R / G / B` |
| Цвет | вся лента — один RGB |

Пример last-seen (имя **не** ID): `LEDnetWF0200086B1AAC` · `E4:98:BB:6B:1A:AC`.

Протокол (UUID FFFF/FF01/FF02, кадры RGB и off) разобран и сверен на этом контроллере: [docs/protocol-notes.md](docs/protocol-notes.md).

## Разработка

Код — в `app/`. Стек: Python 3.11+, Bleak, окно на WebView2, захват экрана — `mss`.

```powershell
cd app
python -m pytest
python -m ruff check src tests
python -m mypy
```

Тесты без Bluetooth-адаптера и без обязательного живого экрана.

Новые фичи пишутся только по утверждённой спеке. Как это устроено: [specs/README.md](specs/README.md), правила для агентов: [AGENTS.md](AGENTS.md).

Сделано: каркас, выбор по адресу, меню, окно, типы, screen-sync ([005](specs/005-screen-color-sync/spec.md)). Не планируется в ближайших срезах: трей, `.exe`, облако, несколько лент, addressable / per-LED, настоящий ambilight по краям.
