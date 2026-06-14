# Fedora / RHEL (.rpm)

Рекомендуемый способ на Fedora 41+.

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
odpm --version
```

## Зависимости

- **Requires:** `python3-packaging`, `git`
- **Recommends:** `moby-engine` / `docker`

Ставит `/usr/bin/odpm`, `dev_project` в `python3/site-packages`.

Артефакт также в [GitHub Releases](https://github.com/aayartsev/odpm/releases) и workflow `release-packages`.

Полная таблица установки: [Установка odpm (все платформы)](README.md).
