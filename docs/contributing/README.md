# Участие в разработке odpm

Этот раздел документации — для тех, кто **меняет исходный код** репозитория [odpm](https://github.com/aayartsev/odpm), а не для администраторов клиентских Odoo-проектов.

| Статья | О чём |
|--------|--------|
| [Непрерывная интеграция репозитория](ci.md) | GitHub Actions, compose-smoke, golden-path |
| [Тесты и статический анализ](tests.md) | Unit-тесты, ruff |
| [Переводы интерфейса](i18n.md) | gettext, каталоги ru_RU |
| [Сборка пакетов](packaging.md) | deb, rpm, wheel |
| [Architecture debt (status)](architecture-debt.md) | Ретроспектива G/C/E (A10, A4, A11) |
| [ADR-001: extensions and manifest v2](adr-001-extensions-and-manifest-v2.md) | Версии, manifest v2, plugins, locks |
| [ADR-002: CI secrets bake](adr-002-ci-secrets-bake.md) | TD-FEAT-09 Phase B — bake module secrets in CI image |
| [Переименование модулей 4.0→4.1](imports-migration.md) | Таблица импортов Python |

Пользовательская документация по работе **с Odoo через odpm**: [оглавление](../README.md).

<a id="ai-disclosure"></a>

## AI disclosure

Parts of the **odpm codebase** and user documentation in `docs/` are **AI-assisted** and reviewed by maintainers. English pages under `docs/en/` are **AI-translated** from Russian.

Отдельные части **кода odpm** и **пользовательской документации** в `docs/` подготовлены **с помощью ИИ** (AI-assisted) и вычитаны авторами. Английские страницы в `docs/en/` — **перевод** с русской (плашка AI-translated docs в `README.MD`).
