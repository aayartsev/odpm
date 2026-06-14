# Windows (WSL)

На Windows odpm работает через **WSL2** и Docker Desktop.

## Пошаговый гайд

Подробная инструкция с иллюстрациями:

**[Настройка окружения Odoo в WSL](https://blog.yartsev.by/odoo_tutorials/001_config_development_environment/004_odoo_development_in_wsl.html)**

## Кратко

1. Установите **WSL2** (Ubuntu рекомендуется).
2. Установите **Docker Desktop** с интеграцией WSL.
3. В терминале WSL установите odpm — [.deb](linux-deb.md) или [pip](pip-legacy.md).
4. Каталог проекта и `odpm --init` выполняйте в файловой системе Linux (`/home/...`), а не на диске `C:\` через `/mnt/c`, если можно — так быстрее работает подключение каталогов в Docker.
5. VS Code: расширение **WSL**, открыть папку в WSL.

## Ссылки `file://`

В WSL используйте пути Linux:

```text
file:///home/user/my_addons
```

Три слэша после `file:` — см. [git-links.md](../reference/git-links.md).

Полная таблица установки: [Установка odpm (все платформы)](README.md).
