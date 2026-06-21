# Установка odpm

!!! info "Рекомендуется stable"
    Для production используйте документацию **[stable](https://aayartsev.github.io/odpm/stable/install/)** (сейчас odpm **4.4.2**) и APT/YUM suite **`stable`**.
    Pre-release (например **4.4.2-beta**) — suite **`testing`** и архив docs **[4.4.2-beta](https://aayartsev.github.io/odpm/4.4.2-beta/install/)**.
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

Готовые `.deb` и `.rpm` публикуются в [GitHub Releases](https://github.com/aayartsev/odpm/releases) (теги `v*`) и попадают в APT/YUM на [GitHub Pages](https://aayartsev.github.io/odpm/apt/) после релизного CI.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
