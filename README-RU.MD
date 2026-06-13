[![CI](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml)
[![CI Docker](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci-docker.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci-docker.yml)
[![Release packages](https://github.com/aayartsev/odoo_dev_project/actions/workflows/release-packages.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/release-packages.yml)
[![GitHub release](https://img.shields.io/github/v/release/aayartsev/odoo_dev_project?include_prereleases&label=release)](https://github.com/aayartsev/odoo_dev_project/releases)
[![packages](https://img.shields.io/badge/packages-.deb%20%7C%20.rpm-2ea44f?style=flat-square)](https://github.com/aayartsev/odoo_dev_project/releases)

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.MD)
[![code AI-assisted](https://img.shields.io/badge/code-AI--assisted-6366F1?style=flat-square)](docs/contributing/README.md#ai-disclosure)
[![AI-assisted docs](https://img.shields.io/badge/docs-AI--assisted-8B5CF6?style=flat-square)](docs/README.md)

#  odpm (Odoo Developer Project Manager)

> Odoo-разработка ломается не на синтаксисе Python, а на **инфраструктуре**: много репозиториев, согласованность путей, разные ОС и архитектуры на рабочих местах в команде разработки, Docker, venv, odoo.conf, IDE, CI и еще куча слоев закоторыми надо следить. **odpm** превращает это в **один воспроизводимый проектный контур** из единственного файла `odpm.json`, чтобы команда тратила время на модули, а не на повторную сборку или отладку окружения.

 odpm — это инструмент, который собирает **полноценное рабочее место разработчика** и **одинаковое окружение Odoo** для всей команды, в том числе для серверов и ci. Достаточно файла описания проекта `odpm.json` в репозитории: odpm сам подготовит каталоги, контейнеры, конфигурацию, пути к модулям и типовые операции с базой данных.

Проект изначально создавался, чтобы **снизить очень высокий порог входа** в разработку на Odoo — в том числе для разработчиков-одиночек и небольших команд, где нет отдельного администратора инфраструктуры.

## Какие проблемы решает odpm

Установить Odoo системным пакетом (deb, rpm) или по инструкции из сети **можно**, и служба **запустится**. Но для **ежедневной разработки** этого недостаточно.

Разработчику нужно не «сервер поднят», а **связанное целое**:

- каталог, в котором он **пишет свой код** (модули заказчика или своей компании);
- быстрый доступ к **настройкам всего окружения** — не разбросанным по десятку мест;
- понятные **системные и Python-зависимости** внутри изолированного окружения;
- **файл конфигурации Odoo** с правильными путями к дополнениям;
- **исходный код платформы** Odoo — для чтения, отладки и обновления модулей;
- **исходники всех подключённых проектов и зависимостей** (OCA, корпоративные репозитории);
- согласованные **пути к каталогам дополнений** и к **собственной кодовой базе**.

Собрать это вручную «системным способом» трудно даже на одной машине. Если сверху добавить **Docker** «чтобы у всех было одинаково», появляется второй слой сложности: что куда подключать с диска, права пользователя, пути внутри контейнера и снаружи, совпадение путей в конфигурации с реальной файловой системой. На этом этапе чаще всего и возникают ошибки «у коллеги работает, у меня модуль не находится».

**odpm берёт на себя эту сборку:** один каталог проекта на вашем компьютере, один файл `odpm.json` в git-репозитории модуля и вы получаете автоматическое клонирование репозиториев, генерацию `docker-compose`, конфигурацию Odoo и команды для резервного копирования, установки модулей, отладки в редакторе.

Полная статья (10 слоёв болей, роли программы, альтернативы и границы): [Зачем odpm](docs/getting-started/why-odpm.md). 

Краткий вход для новичков: [Дружелюбность к новичкам](docs/getting-started/beginner-friendly.md).

## Быстрый старт

На компьютере должны быть установлены **Docker**, **git** и **odpm** (см. [установку](docs/install/linux-deb.md)).

```bash
mkdir my-odoo-project-17 && cd my-odoo-project-17
odpm --init https://github.com/your-org/your-odoo-project.git --branch 17.0
```

При первом запуске мастер настройки задаст вопросы о каталогах и сценарии использования; на незнакомые пункты можно отвечать клавишей Enter.

После подготовки окружения:

```bash
odpm -d test_db -i -u
```

Откройте в браузере: `http://127.0.0.1:8069`.

Пошаговое описание: [Локальная разработка с нуля](docs/getting-started/local-dev-from-scratch.md).

## Установка odpm

| Платформа | Статья |
|-----------|--------|
| Debian / Ubuntu (пакет .deb) | [linux-deb.md](docs/install/linux-deb.md) |
| Fedora (пакет .rpm) | [fedora-rpm.md](docs/install/fedora-rpm.md) |
| macOS | [macos-pipx.md](docs/install/macos-pipx.md) |
| Windows (подсистема WSL) | [windows-wsl.md](docs/install/windows-wsl.md) |
| Установка через pip или из исходников | [pip-legacy.md](docs/install/pip-legacy.md) |

## Сценарии использования

Сценарий задаётся переменной `ODPM_SCENARIO` в файле `.env`. Один и тот же `odpm.json`; меняется способ запуска (отладка, безопасность, сборка образа).

| Значение | Для кого и зачем |
|----------|------------------|
| `developer` | Разработчик на своём компьютере: отладка в VS Code, режим разработки Odoo |
| `server` | Виртуальная машина или сервер заказчика без отладчика, с ограничением доступа к базе |
| `ci` | Сборка готового образа для конвейера непрерывной интеграции |

Статьи: [разработка](docs/scenarios/developer.md) · [сервер](docs/scenarios/server.md) · [непрерывная интеграция](docs/scenarios/ci.md) · [масштабирование команды](docs/scenarios/scaling.md).

## Полная документация

Оглавление всех статей: **[docs/README.md](docs/README.md)**.

| Тема | Ссылка |
|------|--------|
| Подключение чужого или унаследованного проекта | [legacy-project.md](docs/getting-started/legacy-project.md) |
| Роль координатора в команде | [team-coordinator.md](docs/scenarios/team-coordinator.md) |
| Свой форк платформы Odoo | [platform-fork.md](docs/scenarios/platform-fork.md) |
| Ссылки на репозитории (git, https, file) | [git-links.md](docs/reference/git-links.md) |
| Все параметры командной строки | [cli.md](docs/reference/cli.md) |
| Файлы `.env`, `odpm.json`, `odoo.conf` | [справочник](docs/reference/) |
| Безопасность на сервере | [security.md](docs/operations/security.md) |
| Переход с версии 3.0 | [migration-3-to-4.md](docs/operations/migration-3-to-4.md) |

## Разработчикам самого odpm

Участие в разработке инструмента, тесты, переводы интерфейса: [docs/contributing/README.md](docs/contributing/README.md).

## Цели проекта в целом

- **Независимость от операционной системы** и по возможности от архитектуры процессора (в том числе Apple Silicon через Docker).
- **Передача описания проекта через `odpm.json`** — новое окружение разворачивается автоматически.
- **Удобные операции разработчика:** удаление и восстановление базы, создание базы с нужным языком и демо-данными, смена пароля администратора, установка и обновление модулей, экспорт переводов, генерация каркаса нового модуля.
- **Один состав проекта — три сценария запуска:** разработчик, администратор сервера и инженер сборки используют одно описание, меняется только способ упаковки окружения.
