# Debian / Ubuntu (.deb)

Рекомендуемый способ на Linux.

## Установка

Скачайте `odpm_*_all.deb` из [GitHub Releases](https://github.com/aayartsev/odoo_dev_project/releases), из **Actions → Release packages → Artifacts** (`release-packages`) после push в `4.0-beta` / `4.0-rc1` / `main`, или соберите локально:

```bash
./scripts/build_deb.sh
sudo apt install ./dist/odpm_*_all.deb
odpm --version
```

## Зависимости пакета

- **Depends:** `python3 (>= 3.10)`, `python3-packaging`, `git`
- **Recommends:** Docker (`docker.io` / `moby-engine`)
- Без PyPI runtime-зависимостей

Пакет ставит `/usr/bin/odpm`, шаблоны и i18n в `python3/dist-packages`.

При установке с GitHub сверяйте checksum из `SHA256SUMS` релиза.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
