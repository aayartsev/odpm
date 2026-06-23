# Установка odpm

!!! info "Рекомендуется stable"
    Для production используйте документацию **[stable](https://aayartsev.github.io/odpm/stable/install/)** (сейчас odpm **4.5.0**) и APT/YUM ветку **`stable`**.
    Предварительная версия **4.6.0-beta**: [установка 4.6.0-beta](https://aayartsev.github.io/odpm/4.6.0-beta/install/) · [dev](https://aayartsev.github.io/odpm/dev/install/) (разработка odpm). Архив beta: [4.5.0-beta](https://aayartsev.github.io/odpm/4.5.0-beta/install/), [4.4.3-beta](https://aayartsev.github.io/odpm/4.4.3-beta/install/), [4.4.2-beta](https://aayartsev.github.io/odpm/4.4.2-beta/install/).
    См. [Какую документацию читать](../getting-started/documentation-versions.md).

Выберите способ установки **odpm** на хост (не путать с развёртыванием Odoo-проекта через `odpm --init`).

| Платформа | Рекомендуемый способ | Статья |
|-----------|----------------------|--------|
| Debian / Ubuntu | пакет `.deb`, APT-репозиторий | [linux-deb.md](linux-deb.md) |
| Fedora / RHEL | пакет `.rpm`, DNF-репозиторий | [fedora-rpm.md](fedora-rpm.md) |
| macOS | pipx (нативного `.pkg` пока нет) | [macos-pipx.md](macos-pipx.md) |
| Windows | WSL2 + Docker Desktop | [windows-wsl.md](windows-wsl.md) |
| Любая ОС / разработка odpm | pip, editable, `odpm.py` | [pip-legacy.md](pip-legacy.md) |

## Что нужно на хосте для работы с проектом

После установки odpm для [локальной разработки](../getting-started/local-dev-from-scratch.md) обычно нужны **Docker** и **git** (см. статью для вашей платформы).

Готовые `.deb` и `.rpm` публикуются в [GitHub Releases](https://github.com/aayartsev/odpm/releases) (теги `v*`) и попадают в APT/YUM на GitHub Pages после релизного CI (см. [Debian / Ubuntu](linux-deb.md) или [Fedora / RHEL](fedora-rpm.md)).

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
