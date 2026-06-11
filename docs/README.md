# Документация odpm

[![en](https://img.shields.io/badge/lang-en-red.svg)](../README.MD)

Пользовательская документация на этой странице подготовлена **с помощью ИИ** (AI-assisted) и вычитана авторами. Английский перевод (`docs/README.en.md`) появится позже с плашкой **AI-translated docs**.

**odpm** (Odoo Developer Project Manager) помогает разработчикам и администраторам **собрать единое рабочее окружение Odoo**: свой код, платформу, зависимости, конфигурацию и контейнеры — из одного файла описания `odpm.json`, без ручной «склейки» путей и настроек.

Здесь собраны статьи по установке, сценариям работы, справочнику параметров и эксплуатации. Текст ориентирован на практику: что делать, какие файлы править, какие команды вызывать.

Если вы впервые сталкиваетесь с Odoo в разработке, начните с раздела [Дружелюбность к новичкам](getting-started/beginner-friendly.md) — там подробно описано, **какие проблемы** решает odpm и чем он отличается от «просто установленного» Odoo.

Учебный репозиторий для первого прохода: [odoo_demo_project](https://github.com/aayartsev/odoo_demo_project).

---

## С чего начать

| Статья | О чём |
|--------|--------|
| [Дружелюбность к новичкам](getting-started/beginner-friendly.md) | Зачем нужен odpm; пакетный Odoo против рабочего места разработчика; Docker и типичные ошибки |
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
| [VS Code и отладка](operations/vscode-debug.md) | Подключение отладчика к процессу в контейнере |
| [Запуск без диалогов](operations/non-interactive.md) | Скрипты и машины сборки |
| [Безопасность](operations/security.md) | Пароли, обратный прокси, порты |
| [Переход с версии 3.0](operations/migration-3-to-4.md) | Совместимость не сохраняется |

## Разработчикам odpm

| Статья | Содержание |
|--------|------------|
| [Участие в разработке](contributing/README.md) | Тесты, сборка пакетов, непрерывная интеграция репозитория odpm |
