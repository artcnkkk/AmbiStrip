# Читаемый и типизированный код

| Поле | Значение |
|------|----------|
| ID | `006-typed-refactor` |
| Status | `done` |
| Author | агент + пользователь |
| Date | 2026-08-25 |
| Сценарии | нет новых; качество кода S1–S4 |

## Проблема / зачем

Код управления лентой работает, но без линтера и type-checker, с именами вроде `HYPOTHESIS_*` для сверенных UUID и с дырами в типах на границе BLE/GUI. Нужно привести пакет к читаемому, строго типизированному виду **без смены** пользовательского поведения.

## Пользовательский сценарий

**Дано:** Windows, Python 3.11+, тот же комплект Smartbuy `SBL-RGBW-KIT-75`, те же кадры RGB/off и UUID FFFF/FF01/FF02.

**Когда:** пользователь запускает `ledsetup`, `ledsetup menu`, `ledsetup scan` / `color` / `off` как раньше; разработчик гоняет pytest, ruff, mypy.

**Тогда:** поведение то же (кадры, persist, throttle, экраны окна, CLI). Код аннотирован; `ruff check` и `mypy --strict` по `ledsetup` проходят.

## Scope

- Ruff (format + lint) и mypy strict на `app/src/ledsetup`; маркер `py.typed`.
- Иерархия `LedSetupError`; общие `paths` / `types` / `gatt_text`.
- Переименовать сверенные UUID: `SERVICE_UUID` / `WRITE_UUID` / `NOTIFY_UUID`. Поля снимка: `service_matched` / `write_matched` / `notify_matched`. `HYPOTHESIS_NOTE` в protocol оставить (кадр `on` / HSV).
- Protocol клиента BLE в сессии; `ScanFn` / `LogFn`; убрать `Any` и `# type: ignore` на scan.
- Распил GUI-моста: `gui_bridge` / `gui_api` / `gui`; TypedDict для сообщений окна; ошибки GUI по типу исключения.
- JSDoc на `window.__led` и ответы API. TypeScript не вводить.
- Тесты без адаптера зелёные; README с командами ruff/mypy.

## Вне scope

- Screen-sync (`005`), новые кадры, смена стека, `.exe`, удаление CLI/меню.
- Hexagonal architecture, DI-контейнер, фронтенд-сборка, перевод UI на TypeScript.

## Допущения по железу

- Идентификация: BLE-адрес (имя рекламы нестабильно). Пример last-seen: имя `LEDnetWF0200086B1AAC`, адрес `E4:98:BB:6B:1A:AC`
- Тип: analog RGB, один общий цвет
- GATT UUID FFFF/FF01/FF02 сверены на этом ките; не утверждать TBD из `docs/protocol-notes.md`

## Критерии успеха

- [x] `ruff check src tests` в `app/` проходит.
- [x] `mypy` strict по пакету `ledsetup` проходит.
- [x] `python -m pytest` без Bluetooth зелёный.
- [x] Кадры RGB/off, write на FF01, persist-файлы, CLI-команды и экраны окна не меняют контракт.
- [x] GUI не импортирует форматирование GATT из терминального меню.
- [x] README описывает pytest / ruff / mypy.

## Открытые вопросы

- Нет (план утверждён запросом на реализацию).

## Заметки по реализации

Утверждено вместе с планом рефакторинга (чат: «Implement the plan»). Стек тот же: Python 3.11+, Bleak, WebView2, код в `app/`.

- Новые модули: `exceptions.py`, `paths.py`, `types.py`, `gatt_text.py`, `gui_bridge.py`, `gui_api.py`.
- `_maybe_enable_notify` → публичный `enable_kit_notify`.
- `AppSettings`: `dataclasses.replace`.
- Общий разбор RGB 0–255 для CLI и меню.
- Узкие `except Exception` только вокруг native WebView.

## Как утвердить

План рефакторинга утверждён пользователем явным запросом на реализацию. Статус сразу `in-progress`.

## Трассировка

| Сценарий | В этой спеке |
|----------|----------------|
| S1 BLE discovery + connect | нет (рефактор существующего) |
| S2 Verify protocol | нет |
| S3 Set solid color | нет |
| S4 Desktop color picker | нет |
| S5 Screen color sync | нет |
