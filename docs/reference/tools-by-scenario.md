# Инструменты odpm по сценариям

Одна утилита odpm предоставляет **набор команд**; в разных сценариях (`ODPM_SCENARIO`) часть из них не применяется или ведёт себя иначе.

| Задача | Разработчик | Сервер | Сборка образа |
|--------|:-----------:|:------:|:-------------:|
| Инициализация `odpm init` | да | да | да |
| Подготовка `odpm prepare` / `odpm up` | да | да | `prepare` да; `up` **запрещён** (ADR-017) |
| Запуск стека | `odpm up` / `docker compose up` | да | только `docker compose` после `prepare` / `build` |
| База и модули `odpm up -d -i -u` | да | да | после `compose up` через `compose exec` (не `odpm up`) |
| Тесты модулей `-t` (на `up`) | да | редко | да |
| Резервное копирование / восстановление (`odpm database …` / `odpm up --db-*`) | да | да | стековый `database` в ci **запрещён** |
| Смена пароля администратора, переводы | да | да | по необходимости |
| Генерация каркаса модуля `scaffold` | да | нет | **запрещён** в ci |
| Отладка в VS Code | да | нет | нет |
| Секреты модулей (`--secrets-file`, `/run/odpm/secrets.json`) | да | да | нет (host mount) |
| Запуск pre-commit в контейнере | да | нет | нет |
| План изменений `odpm plan` | да | да | да |
| Обновление фиксации `odpm prepare --update-lock` | координатор | чтение | строго |
| Сборка образа `odpm build` | **нет** | **нет** | **да** |
| Бэкенд `--image-builder` / env `ODPM_CI_IMAGE_BUILDER` (`docker`, `kaniko`) | **нет** | **нет** | **да** |
| Публикация `--image-push` / env `ODPM_CI_IMAGE_PUSH` | **нет** | **нет** | **да** |
| Подготовка без git `--no-git-update` | да | да | да |

Полный перечень параметров: [командная строка](cli.md). Для `kaniko` см. [сценарий ci](../scenarios/ci.md) и [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md).
