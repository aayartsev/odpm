# Установка odpm

Выберите способ установки **odpm** на хост (не путать с развёртыванием Odoo-проекта через `odpm --init`).

| Платформа | Рекомендуемый способ | Статья |
|-----------|----------------------|--------|
| Debian / Ubuntu | пакет `.deb`, APT-репозиторий | [linux-deb.md](linux-deb.md) |
| Fedora / RHEL | пакет `.rpm` | [fedora-rpm.md](fedora-rpm.md) |
| macOS | pipx (нативного `.pkg` пока нет) | [macos-pipx.md](macos-pipx.md) |
| Windows | WSL2 + Docker Desktop | [windows-wsl.md](windows-wsl.md) |
| Любая ОС / разработка odpm | pip, editable, `odpm.py` | [pip-legacy.md](pip-legacy.md) |

## Что нужно на хосте для работы с проектом

После установки odpm для [локальной разработки](../getting-started/local-dev-from-scratch.md) обычно нужны **Docker** и **git** (см. статью для вашей платформы).

Готовые `.deb` и `.rpm` публикуются в [GitHub Releases](https://github.com/aayartsev/odpm/releases) и в CI-артефактах workflow **Release packages** после push в `4.0-beta` / `4.0-rc1` / `main`.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
