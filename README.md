# LEDSetup

Настольное приложение для **одной** аналоговой RGB-ленты Smartbuy / Zengge LEDnetWF: сначала надёжное управление по BLE, затем синхронизация среднего цвета экрана ноутбука с лентой.

Стек зафиксирован в спеке `001`: Python 3.11+, Bleak, CLI, каталог `app/`. GATT UUID FFFF/FF01/FF02 **сверены**. Кадры RGB и off **визуально подтверждены**. Имя в рекламе **нестабильно** — цель задаётся BLE-адресом (спека `002`).

## Что это

Комплект **Smartbuy SBL-RGBW-KIT-75**, контроллер семейства **Zengge LEDnetWF**, вендорское приложение **ZENGGE**. Лента **аналоговая RGB**: вся полоса — один общий цвет, не addressable и не по секциям.

Цели по приоритету:

1. Простое desktop-приложение для **этого одного** устройства.
2. Ближайший шаг: найти ленту, выбрать её, задать RGB.
3. Дальняя цель: ambient / ambilight — средний цвет экрана ноутбука → цвет ленты.

## Оборудование

| Параметр | Значение |
|----------|----------|
| Комплект | Smartbuy `SBL-RGBW-KIT-75` |
| Приложение вендора | ZENGGE |
| Радио | BLE |
| Имя (last seen, не ID) | `LEDnetWF0200086B1AAC` |
| Адрес (last seen, ID) | `E4:98:BB:6B:1A:AC` |
| Блок питания | `12V DC / 2A` |
| Макс. мощность | `24W` |
| Вход БП | `100–240V AC, 50/60Hz` |
| Вход контроллера | `12V DC` |
| Выход контроллера | `+ / R / G / B` |
| Тип ленты | analog RGB (не addressable, не per-LED, не per-section) |
| Цвет | вся лента — один общий цвет |

Имя в Windows Bluetooth / рекламе может измениться. Не зашивать его как единственную цель. Устаревшая гипотеза точного имени: `LEDnetWF0200006B1AAC`.

### GATT (сверено enumeration 2026-08-25)

| Роль | UUID |
|------|------|
| Service | `0000FFFF-0000-1000-8000-00805F9B34FB` |
| Write | `0000FF01-0000-1000-8000-00805F9B34FB` |
| Notify | `0000FF02-0000-1000-8000-00805F9B34FB` |

RGB `0B 31` и off `0B 3B 24` визуально подтверждены (вся полоса красный → зелёный → синий, затем погасла). HSV, `on`, seq/checksum, смысл notify — TBD. См. [docs/protocol-notes.md](docs/protocol-notes.md).

## Запуск (Windows)

Нужны **Python 3.11+** и включённый Bluetooth. Команды из корня репозитория:

```powershell
cd app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
```

Дальше одна команда `ledsetup` (venv должен быть активен).

### Окно (основной запуск)

```powershell
ledsetup
```

То же: `ledsetup gui`. Сначала экран выбора ленты, затем цвет. Нужен Microsoft Edge WebView2 (на Windows 10/11 обычно уже стоит).

### Терминальное меню

```powershell
ledsetup menu
```

### Разовые команды (скрипты)

Сначала выбрать устройство — имя не зашито:

```powershell
ledsetup scan
# в списке `*` — префикс LEDnetWF (подсказка). Введите номер.

ledsetup scan --index 1
ledsetup scan --address E4:98:BB:6B:1A:AC
ledsetup scan --name LEDnetWF0200086B1AAC
```

Адрес пишется в `%LOCALAPPDATA%\ledsetup\selected-device.json`. Настройки меню (таймауты) — рядом, в `settings.json`. Дальше без повторного выбора:

```powershell
ledsetup gatt
ledsetup on
ledsetup color 255 0 0
ledsetup color 0 255 0
ledsetup color 0 0 255
ledsetup off
```

Разово другой адрес: `ledsetup gatt --address E4:98:BB:6B:1A:AC` (и то же для `color` / `on` / `off`). Если ничего не выбрано — ошибка с просьбой сделать `scan` или передать `--address`.

Альтернативный кадр цвета (HSV после `0B 3B A1`, гипотеза): `ledsetup color 255 0 0 --hsv`.

Юнит-тесты **без** адаптера Bluetooth (из каталога `app/`):

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy
```

Эквивалент без скрипта: `python -m ledsetup` (окно) или `python -m ledsetup menu` / `python -m ledsetup scan`.

Если `python` не находится, установите Python 3.11+ (например `winget install Python.Python.3.12`) и откройте новый терминал.

Прогон 2026-08-25: цвет глазами подтверждён. ZENGGE / удержание линка Windows могут мешать connect.

## Текущий охват и не-цели

**В охвате:** спека `001` (`done`) — каркас, GATT, RGB/off. Спека `002` — scan и выбор по адресу. Спека `003` — меню в терминале. Спека `004` — то же в окне. Спека `006` — типы, ruff, mypy.

**Не в этих спеках:** GUI-окно, color picker мышью, трей, screen-sync, несколько одновременных устройств, облако, addressable/per-LED, упаковка в `.exe`.

## Дорожная карта

| Фаза | Что | Сценарии |
|------|-----|----------|
| **A. BLE control proof** | Scan, выбор по адресу, GATT, рабочий payload RGB / off | S1, S2, минимальный S3 |
| **B. Desktop UI** | Простой color picker и вкл/выкл | S4 |
| **C. Screen color sync** | Средний цвет экрана ноутбука → лента, достаточно быстро для атмосферы | S5 |

Подробности сценариев: [specs/README.md](specs/README.md).

## Spec-Driven Development

В этом репозитории код фичи **не пишут без утверждённой спецификации**.

1. Создать спеку из [`specs/template.md`](specs/template.md) в новую папку `specs/NNN-short-name/`.
2. Пользователь **утверждает** спеку (`draft` → `approved`).
3. Только после этого реализовать **ровно то**, что написано в утверждённой спеке.

Правила для агентов: [AGENTS.md](AGENTS.md). Каталог спек: [specs/](specs/).

**Сейчас:** [001](specs/001-scaffold-and-color-verify/spec.md) `done`. [002](specs/002-scan-device-select/spec.md) scan. [003](specs/003-terminal-menu-app/spec.md) меню. [004](specs/004-desktop-color-picker/spec.md) окно. [006](specs/006-typed-refactor/spec.md) рефакторинг типов. [005](specs/005-screen-color-sync/spec.md) screen-sync — `draft`.

## Стек

Python 3.11+, Bleak, CLI; исходники — в `app/`. См. спеку `001`.
