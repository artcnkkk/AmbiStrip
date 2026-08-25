# LEDSetup

Окно на Windows для **одной** аналоговой RGB-ленты: нашли контроллер по Bluetooth, выбрали его, задали цвет всей полосе.

Это не «умная» адресная лента и не несколько устройств. Вся полоса всегда **одного** цвета. Дальше по плану — подхватывать средний цвет экрана ноутбука (как мягкий ambilight). Пока этого нет.

Комплект, на котором собрано: Smartbuy `SBL-RGBW-KIT-75`, контроллер Zengge LEDnetWF, вендорское приложение **ZENGGE**.

## Что уже работает

- Окно: поиск ленты → пикер цвета, вкл/выкл, GATT и настройки
- То же в терминале: `ledsetup menu`
- Разовые команды: `scan`, `color`, `off`, `gatt`

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

Сначала экран «какая лента», затем цвет. Закройте **ZENGGE**, если лента не находится или не подключается — оно часто держит линк.

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
```

Другой адрес разово: `--address …` у `color` / `off` / `gatt`. Команда `on` есть, на этом ките её не проверяли. Кадр HSV (`--hsv`) — гипотеза, пикер в окне его не шлёт.

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

Код — в `app/`. Стек: Python 3.11+, Bleak, окно на WebView2.

```powershell
cd app
python -m pytest
python -m ruff check src tests
python -m mypy
```

Тесты без Bluetooth-адаптера.

Новые фичи пишутся только по утверждённой спеке. Как это устроено: [specs/README.md](specs/README.md), правила для агентов: [AGENTS.md](AGENTS.md).

Сейчас сделано: каркас и проверка цвета, выбор по адресу, меню, окно, рефакторинг типов. Черновик screen-sync — [005](specs/005-screen-color-sync/spec.md). Не планируется в ближайших срезах: трей, `.exe`, облако, несколько лент, addressable / per-LED.
