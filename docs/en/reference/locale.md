# odpm message locale (ODPM_LOCALE)

> **AI-translated** from Russian.

odpm utility messages on the **host** (errors, setup wizard questions, brief statuses when starting compose) are translated via GNU gettext catalogs in `dev_project/i18n/`.

The **container** log (Odoo, PostgreSQL) intentionally stays **in English** — easier to match with general documentation.

## How language is chosen

| Priority | Source |
|----------|--------|
| 1 | `ODPM_LOCALE` in merged `.env` (home + project; project wins) |
| 2 | `ODPM_LOCALE` in the process environment |
| 3 | `LC_ALL`, `LC_MESSAGES`, or `LANG` |
| 4 | Operating system locale |
| 5 | `en_US` |

Since **4.7**, odpm **merges** `~/.odpm/.env` and project `.env` on read; `ODPM_LOCALE` can live in home while ports stay in project ([`.env` variables](env-dotenv.md), [ADR-013](../../contributing/adr-013-layered-env-dotenv.md)).

Example in the project directory:

```ini
ODPM_LOCALE=ru_RU
```

Full odpm UI translation is available for **`ru_RU`**; other locales fall back to English.

## Do not confuse with Odoo database language

Field **`database.language`** in [odpm.json](odpm-json.md) (or deprecated **`db_lang`** in `user_settings.json`) sets the **Odoo database** language on creation (`ru_RU`, `en_US`), not odpm’s own message language. When both exist, the manifest wins.

## Updating translations (for odpm developers)

See [contributing/i18n.md](https://github.com/aayartsev/odpm/blob/main/docs/contributing/i18n.md) in the odpm repository.
