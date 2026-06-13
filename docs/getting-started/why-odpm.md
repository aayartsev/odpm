# Зачем odpm: какие проблемы решает утилита

Статья для **всех ролей** — разработчик, координатор команды, DevOps, новичок. Сжатый вход «с нуля» и установка на хост — в [дружелюбности к новичкам](beginner-friendly.md). Масштабирование команды и сценарии — в [scaling](../scenarios/scaling.md), [team-coordinator](../scenarios/team-coordinator.md).

---

## Для кого этот текст

| Роль | Зачем читать |
|------|----------------|
| **Разработчик** | Понять, почему «Odoo уже стоит» ≠ готовое рабочее место |
| **Координатор / тимлид** | Обосновать единый `odpm.json` и lock в git |
| **DevOps / CI** | Связать developer/server/ci без трёх разных скриптов |
| **Новичок в Odoo** | Увидеть полную картину до [первого проекта](local-dev-from-scratch.md) |

---

## North Star

> **Сформировал `odpm.json` в репозитории → коллега клонировал проект → тот же Odoo-стек с аддонами, Python, БД и отладчиком — на ноутбуке, на сервере и в CI.**

**odpm** — не «ещё один способ поставить Odoo», а **менеджер воспроизводимого окружения** из декларативного manifest (`odpm.json`), который является частью проекта.

---

## Боли по слоям

### 1. «Odoo работает» ≠ «можно разрабатывать»

Системный пакет, голый `docker run odoo:19` или длинная wiki-инструкция дают **запущенный сервис** — это не то же самое, что **рабочее место разработчика**. Для его создания нужно ответить на вопросы:

- где лежит **ваш** код и как он попадает в `addons_path`;
- где **исходники ядра** для чтения, отладки и LSP;
- где **OCA и корпоративные репозитории** и какие у них ветки;
- какой **Python/venv** и какие **pip-зависимости** у проекта;
- какой **odoo.conf** связывает всё это вместе.

**Без odpm** — ручная «склейка» или целый букет инструментов при каждой смене версии Odoo, компьютера или проекта. **С odpm** — весь контур в **одном каталоге проекта** из единого описания стека.

### 2. Multi-repo и пути — «модуль не найден»

Зрелый Odoo-проект — не один git-репозиторий, а **platform + developing + N зависимостей**. Типичные боли:

- забытый каталог в `addons_path`;
- разные пути на хосте и в контейнере;
- симлинки, subprojects, OCA `oca_dependencies.txt`;
- «у меня работает» из-за локального расположения каталога с модулями или платформы.

**С odpm** — централизованный resolver, `map_folders`, nested `odpm.json`, [`deps.lock.json`](../reference/deps-lock.md), подстановка `${VAR}` в manifest для локальных путей без форка json в git.

### 3. Разнородные ОС и архитектуры в распределённой команде

**Без odpm / с инструкциями «под свою машину»:**

- отдельные гайды: Ubuntu, Fedora, macOS, Windows (WSL), Apple Silicon;
- пути (`/home/...` vs `C:\` vs `/Users/...`), shell, права, line endings;
- Python/pip и нативные wheels под **конкретную** архитектуру хоста;
- «у меня на Linux работает» — у коллеги на macOS или ARM другая ошибка;
- CI на amd64, ноутбук на arm64 — сюрпризы при сборке образа или бинарных зависимостей;
- onboarding = «сначала выясни ОС, потом открой нужную ветку wiki».

**С odpm:**

- один `odpm.json` в git — **один** состав стека для всей команды;
- локальные отличия машины — в [`.env`](../reference/env-dotenv.md), а не в форк wiki;
- поле `arch` в manifest и lock venv учитывают архитектуру; CI-образ под целевую платформу;
- установка **самого odpm** на Linux / macOS / WSL — без отдельного «как поднять Odoo» на каждую ОС.

**Честная граница:** arm64 на Mac и amd64 на CI не схлопываются сами; для Apple Silicon могут понадобиться multi-arch образы или builder той же архитектуры. **Правила** (manifest, compose, lock, сценарии) у команды остаются одними — подробнее в [масштабировании](../scenarios/scaling.md).

Типичный ответ на эту боль — **Docker** (следующий пункт): единый runtime внутри контейнера. Но без оркестратора контейнер сам по себе проблему не закрывает.

### 4. Docker удваивает сложность, если нет оркестратора

Чтобы снять боль из п. 3, команды идут в Docker — контейнеры дают одинаковость Ubuntu/macOS/Windows **внутри образа**. Но **без оркестратора** Docker **переносит** сложность на другой уровень:

- bind-mount'ы platform/developing/deps;
- UID/GID и права на файлы;
- compose + PostgreSQL + порты;
- pip-пакеты **внутри** контейнера;
- отладчик для процесса внутри контейнера.

**С odpm** (оркестратор поверх Docker):

- на хосте — Docker, git и odpm; **один** сценарий запуска на любой настольной ОС;
- стек Odoo (Debian-образ, Python, venv, postgres, compose) **в контейнере** по одному `odpm.json`;
- автоматическая генерация compose, Dockerfile, odoo.conf, volume mapping, настройка отладчиков и остального «docker-слоя».

### 5. «У каждого своё» — боль команды

**Без общего manifest:**

- у одного Python 3.10, у другого 3.12;
- разные состояния зависимостей OCA;
- разные способы поднять postgres/debugger;
- onboarding = длинный чеклист на десятки пунктов.

**С odpm** — разделение **командного** ([`odpm.json`](../reference/odpm-json.md) + lock в git) и **личного** ([`user_settings.json`](../reference/user-settings.md), `.env` на машине). Координатор фиксирует стек; остальные воспроизводят задекларированное. См. [разделение конфигурации](../reference/config-split.md).

### 6. Три роли — один движок

Одна кодовая база, разное поведение по [`ODPM_SCENARIO`](../reference/env-dotenv.md):

| Роль | Боль без odpm | Что даёт odpm |
|------|---------------|---------------|
| **Разработчик** | долгая настройка под свой компьютер | [`developer`](../scenarios/developer.md): полный арсенал разработки, дебаггер, CLI, VS Code и PyCharm |
| **Сервер / VM** | отдельная настройка проекта | [`server`](../scenarios/server.md): тот же стек, без dev-утилит, postgres на localhost |
| **CI** | отдельные сценарии сборки | [`ci`](../scenarios/ci.md): baked-образ по тем же правилам, что и у команды |

Один pipeline, профиль задаёт сценарий — не три несвязанных инструмента.

### 7. Непредсказуемость при повторной настройке

**Без odpm** (свои скрипты, ansible, «setup.sh», ручной compose):

- неясно, что править руками, а что перегенерируется;
- повторный setup затирает `docker-compose.yml`, Dockerfile или конфиг;
- нет dry-run — последствия видны после факта;
- нет общего списка «generated vs source of truth».

**С odpm:**

- [`odpm plan`](../reference/cli.md) — preview шагов и diff до materialize;
- перечень [сгенерированных файлов](../reference/generated-files.md);
- шаблоны в `.odpm/` vs артефакты в корне (compose, runtime config);
- один manifest описывает состав стека.

### 8. Операционные задачи размазаны по инструментам

Помимо «поднять Odoo», в работе нужны:

- restore БД из архива;
- новая БД с языком/страной/demo;
- сброс пароля admin;
- установка и обновление модулей (`-i` / `-u`);
- pre-commit в контейнере;
- секреты модулей без коммита в git.

**С odpm** — единый CLI-оркестратор вокруг одного compose-стека ([справочник CLI](../reference/cli.md), [секреты](../operations/secrets.md)).

### 9. IDE и отладка

**Без odpm:** вручную `launch.json`, path mappings host/container, `extraPaths` для Pylance, совместимость PyCharm/pydevd.

**С odpm:** `debug-profile.json`, генерация VS Code / PyCharm конфигов, `debugpy` и `odoo-stubs` в сценарии developer. См. [отладку в IDE](../operations/vscode-debug.md).

### 10. CI и воспроизводимость сборок

**Без odpm:**

- на CI другой pip/venv;
- зависимости без зафиксированных SHA;
- образ собирается ad-hoc.

**С odpm:** [`deps.lock.json`](../reference/deps-lock.md), `--update-lock`, bake CI-образа по хэшам коммитов. См. [сценарий ci](../scenarios/ci.md).

---

## Где odpm на карте решений

Ниша **между** «голым Docker Odoo» и **тяжёлым Doodba / Odoo.sh**:

| Альтернатива | Чего не хватает типичной команде |
|-------------|----------------------------------|
| Пакет / bare metal | multi-repo, Docker, IDE, CI profile |
| Official Odoo Docker | developing project, git deps, venv, debug |
| Dev Containers | Odoo-specific: odpm.json, OCA graph, lock, scenarios |
| Doodba | выше порог DevOps; меньше «одна кнопка для новичка» |
| Odoo.sh | SaaS, не self-hosted laptop |

**odpm** — Odoo-specific Dev Container manager: declarative manifest + scenario + plan + container contract, без облачной привязки.

---

## Что odpm сознательно не решает

- **Не PaaS** — нет staging/prod как у Odoo.sh.
- **Не полный prod-hardening** — [`server`](../scenarios/server.md) даёт профиль, nginx/TLS/backup — на вас ([безопасность](../operations/security.md)).
- **Не замена знанию Odoo** — framework, ORM, модули нужно учить.
- **Plugins/hooks** — в разработке; объём Doodba `custom/` hooks **сегодня** не покрыт.
- **Не byte-identical reproducibility** (как Nix) — **практическая** воспроизводимость через lock + image + manifest.

---

## Следующие шаги

1. [Дружелюбность к новичкам](beginner-friendly.md) — что установить на хост и первый запуск.
2. [Локальная разработка с нуля](local-dev-from-scratch.md) — `odpm --init`, первая база.
3. [Координатор команды](../scenarios/team-coordinator.md) — lock, non-interactive, CI.
4. [Сценарий developer](../scenarios/developer.md) — отладка и `dev_mode`.

---

## Кратко

> Odoo-разработка ломается не на синтаксисе Python, а на **инфраструктуре**: multi-repo, пути, разные ОС и архитектуры в команде, Docker, venv, конфиг, IDE, CI. odpm превращает это в **один воспроизводимый проектный контур** из `odpm.json`, чтобы команда тратила время на модули, а не на повторную сборку окружения.
