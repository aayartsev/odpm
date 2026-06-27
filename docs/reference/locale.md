# Язык сообщений odpm (ODPM_LOCALE)

Сообщения утилиты odpm на **хосте** (ошибки, вопросы мастера, краткие статусы при запуске compose) переводятся через каталоги GNU gettext в `dev_project/i18n/`.

Журнал **внутри контейнера** (Odoo, PostgreSQL) намеренно остаётся **на английском** — так проще сопоставлять с общей документацией.

## Как выбирается язык

| Приоритет | Источник |
|-----------|----------|
| 1 | `ODPM_LOCALE` в merged `.env` (home + project; project побеждает) |
| 2 | `ODPM_LOCALE` в окружении процесса |
| 3 | `LC_ALL`, `LC_MESSAGES` или `LANG` |
| 4 | Локаль операционной системы |
| 5 | `en_US` |

С **4.7** odpm при чтении **объединяет** `~/.odpm/.env` и project `.env`; `ODPM_LOCALE` может жить в home, а порты — в project ([переменные .env](env-dotenv.md), [ADR-013](../contributing/adr-013-layered-env-dotenv.md)).

Пример в каталоге проекта:

```ini
ODPM_LOCALE=ru_RU
```

Полный перевод интерфейса odpm доступен для **`ru_RU`**; для остальных локалей — английский текст.

## Не путать с языком базы Odoo

Поле **`db_lang`** в `user_settings.json` задаёт язык **базы данных** Odoo при создании (`ru_RU`, `en_US`), а не язык сообщений самой утилиты odpm.

## Обновление переводов (для разработчиков odpm)

См. [contributing/i18n.md](https://github.com/aayartsev/odpm/blob/main/docs/contributing/i18n.md) в репозитории odpm.
