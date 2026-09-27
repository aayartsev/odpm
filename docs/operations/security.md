# Безопасность

## Профили безопасности

Ось **`ODPM_SECURITY_PROFILE`** / **`--security-profile`** задаёт posture (пароли и publish binds), отдельно от `ODPM_SCENARIO` (topology / workflow).

| Profile | Дефолт сценария | Новые `user_settings` / secrets | Published ports |
|---------|-----------------|----------------------------------|-----------------|
| `convenience` | `developer` | manager=`1`, admin user=`admin` (как раньше) | без принудительного `127.0.0.1` |
| `hardened` | `server` | random в `.odpm/secrets.json`; в settings — `${@secret:odpm.db_manager_password}` и `${@secret:odpm.db_default_admin_password}` | Postgres и все published → `127.0.0.1` |

Override: CLI `--security-profile` сильнее env `ODPM_SECURITY_PROFILE`, иначе дефолт от сценария (таблица дефолтов и conflict rules — в `policy_compose`, ADR-024).  
Сценарий **`ci`**: bootstrap Odoo-паролей в secrets **не** выполняется; bind портов остаётся scenario-owned (postgres на localhost, без bind всех published), даже если override = `hardened`.

Точка правды для паролей Odoo — **`user_settings.json` после expand** (`${VAR}` / `${@secret:}` по всему файлу). Существующий settings odpm **не переписывает**. На `hardened`, если парольные поля в raw — plaintext / пусто / без `${@secret:}` — WARNING (файл не меняется).

Новые hardened-проекты: при отсутствии `.odpm/secrets.json` odpm создаёт ключи `odpm.db_manager_password` и `odpm.db_default_admin_password` (`token_urlsafe`, `0600`).  
Уже созданная Odoo-БД сама не получает новый admin-пароль — используйте `--set-admin-pass` с `-d`.

См. ADR-023, ADR-024, [локальные секреты](secrets.md), [user-settings](../reference/user-settings.md).

## Пароли в конфигурации

| Параметр | Назначение |
|----------|------------|
| `db_manager_password` в `user_settings.json` | Пароль **менеджера баз данных** Odoo (`admin_passwd`) |
| `db_default_admin_login` / `db_default_admin_password` | Учётная запись **администратора** при создании новой базы / `--set-admin-pass` |
| Учётные данные PostgreSQL | Подставляются в служебную конфигурацию и compose (общий `POSTGRES_ODOO_PASS` — см. follow-ups) |

На **своём компьютере** (`convenience`) допустимы заводские значения. На **сервере** (`hardened`) предпочитайте secrets + refs.

## Секреты и git

Не помещайте в общий репозиторий пароли, токены доступа, приватные ключи. Файл `.env` каталога проекта обычно **не коммитят**. Шаблон `user_settings.json` в git лучше держать без реальных секретов (на hardened — со ссылками `${@secret:…}`).

### Секреты Odoo-модулей (API-ключи, токены интеграций)

Для произвольных ключей **модулей** используйте **`.odpm/secrets.json`** — файл в `.odpm/.gitignore`. odpm монтирует нормализованную копию в контейнер как `/run/odpm/secrets.json` (сценарии `developer` и `server`).

- В git коммитьте только **`.odpm/secrets.example.json`** с заглушками `REPLACE_ME`.
- После import odpm выставляет права **`0600`** на source.
- Не логируйте значения из `/run/odpm/secrets.json` в Odoo и не дублируйте их в compose `environment:`.

Подробно: [локальные секреты](secrets.md).

`--secrets-file` импортирует JSON v1 в `.odpm/secrets.json` **в начале bootstrap** (до полного expand `user_settings` с `${@secret:}`).

## Сценарий `server` и доступ из интернета

Дефолтный профиль **`hardened`**: порты только на `127.0.0.1`, пароли через secrets.

- Вынесите **HTTPS** на **обратный прокси** (nginx, Caddy, traefik и аналоги).
- В `odoo.conf` включите **`proxy_mode`**; при публикации нескольких баз — **`dbfilter`**.
- Не расширяйте published ports на `0.0.0.0` вручную в compose.
- Роль приложения PostgreSQL (`odoo`) — **NOSUPERUSER**; admin-роль `postgres` (SUPERUSER) нужна odpm для ensure-role. Пароль у admin и app пока общий (`POSTGRES_ODOO_PASS`) — утечка из `odoo.conf` всё ещё даёт логин как `-U postgres`.
- **Межсетевой экран:** снаружи SSH и HTTPS прокси.
- **`dev_mode`** на доступном извне инстансе не используйте; в сценарии `server` он игнорируется.
- Порт отладчика на сервере **не нужен**.

## Разработка на localhost

Дефолтный профиль **`convenience`**: простые пароли и открытые порты для утилит. Для проверки prod-подобной схемы: `ODPM_SECURITY_PROFILE=hardened` или `--security-profile hardened` без смены сценария.
