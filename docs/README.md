# Документация odpm

[![en](https://img.shields.io/badge/lang-en-red.svg)](https://aayartsev.github.io/odpm/en/)

Пользовательская документация на этой странице подготовлена **с помощью ИИ** (AI-assisted) и вычитана авторами. Английская версия — в переключателе языка на сайте (`docs/en/`); перевод **AI-translated**, вычитывается постепенно.

**odpm** (Odoo Developer Project Manager) помогает разработчикам и администраторам **собрать единое рабочее окружение Odoo**: свой код, платформу, зависимости, конфигурацию и контейнеры — из одного файла описания `odpm.json`, без ручной «склейки» путей и настроек.

Здесь собраны статьи по установке, сценариям работы, справочнику параметров и эксплуатации. Текст ориентирован на практическое применение: что делать в том или ином случае, какие файлы править, какие команды вызывать.

Если вы впервые выбираете odpm для команды или проекта, начните с [Зачем odpm: какие проблемы решает утилита](getting-started/why-odpm.md) — для всех ролей (разработчик, координатор, DevOps). Новичкам в Odoo дальше — [Дружелюбность к новичкам](getting-started/beginner-friendly.md): установка на рабочий компьтер и первые шаги.

---

## С чего начать

| Статья | О чём |
|--------|--------|
| [Зачем odpm](getting-started/why-odpm.md) | Какие боли решает утилита; без odpm / с odpm; сравнение с альтернативами; границы |
| [Дружелюбность к новичкам](getting-started/beginner-friendly.md) | Установка на хост; пакетный Odoo против рабочего места; Docker и типичные ошибки |
| [Локальная разработка с нуля](getting-started/local-dev-from-scratch.md) | Каталог проекта, VS Code, `odpm --init`, первая база и модули |
| [Чужой или унаследованный проект](getting-started/legacy-project.md) | Подключение существующего репозитория, журналы, план изменений, фиксация версий |

## Установка odpm на компьютер

| Статья | Платформа |
|--------|-----------|
| [Debian / Ubuntu (.deb)](install/linux-deb.md) | Рекомендуется для Linux |
| [Fedora / RHEL (.rpm)](install/fedora-rpm.md) | Fedora 41 и новее |
| [macOS](install/macos-pipx.md) | Установка через pipx |
| [Windows (WSL)](install/windows-wsl.md) | Docker Desktop и подсистема Linux |
| [pip и копирование исходников](install/pip-legacy.md) | Разработка odpm, системы без готового пакета |

## Сценарии (`ODPM_SCENARIO`)

| Сценарий | Статья |
|----------|--------|
| `developer` — разработка на своём компьютере | [developer](scenarios/developer.md) |
| `server` — виртуальная машина или сервер | [server](scenarios/server.md) |
| `ci` — образ для непрерывной интеграции | [ci](scenarios/ci.md) |
| Координатор команды и фиксация версий | [team-coordinator](scenarios/team-coordinator.md) |
| Свой репозиторий платформы Odoo | [platform-fork](scenarios/platform-fork.md) |
| Одна команда — разные роли и машины | [scaling](scenarios/scaling.md) |

На самом выбор сценария всегда за вами, но каждый из них имеет свое базовое поведние, поэтому учитывайте это

## Справочник и инструменты

| Статья | Содержание |
|--------|------------|
| [Инструменты по сценариям](reference/tools-by-scenario.md) | Какие команды уместны в каждом режиме |
| [Иерархия конфигурации](reference/config-hierarchy.md) | Что перекрывает что: командная строка, json, `.env` |
| [odpm.json и user_settings.json](reference/config-split.md) | Что относится к стеку, что — к работе разработчика |
| [Переменные `.env`](reference/env-dotenv.md) | Порты, каталоги, сценарий, язык сообщений |
| [Ссылки на репозитории](reference/git-links.md) | HTTPS, SSH, локальный каталог `file://` |
| [odpm.json](reference/odpm-json.md) | Описание стека проекта |
| [user_settings.json](reference/user-settings.md) | Модули, база, поведение git |
| [odoo.conf](reference/odoo-conf.md) | Файл в каталоге проекта и конфигурация в контейнере |
| [Параметры командной строки](reference/cli.md) | Полный перечень |
| [deps.lock.json](reference/deps-lock.md) | Фиксация ревизий git-зависимостей |
| [Структура каталога проекта](reference/project-layout.md) | Назначение каталогов и файлов |
| [Сгенерированные файлы](reference/generated-files.md) | Что не следует править вручную |
| [Язык сообщений odpm](reference/locale.md) | Переменная `ODPM_LOCALE` |

## Эксплуатация

| Статья | Содержание |
|--------|------------|
| [Отладка в IDE](operations/vscode-debug.md) | `debugpy_listen` (VS Code / PyCharm DAP) и `pydevd_connect` (PyCharm Debug Server) |
| [Локальные секреты](operations/secrets.md) | API-ключи и токены модулей → `/run/odpm/secrets.json` |
| [Запуск без диалогов](operations/non-interactive.md) | Скрипты и машины сборки |
| [Безопасность](operations/security.md) | Пароли, обратный прокси, порты |
| [Переход с версии 3.0](operations/migration-3-to-4.md) | Совместимость не сохраняется |

## Разработчикам odpm

Материалы для контрибьюторов odpm — в репозитории на GitHub: [docs/contributing/](https://github.com/aayartsev/odpm/tree/main/docs/contributing).
