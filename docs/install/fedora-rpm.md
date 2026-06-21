# Fedora / RHEL (.rpm)

Рекомендуемый способ на **Fedora 40+** (системный Python ≥ 3.10). В YUM-репозитории публикуются сборки для Fedora 40, 41 и 44 (`fc40` / `fc41` / `fc44` в имени RPM). На EL9 / RHEL 9 штатный `python3` 3.9 не поддерживается — используйте pip/pipx или соберите RPM на Fedora.

## Установка через DNF (обновления `dnf upgrade`)

После [релизного тега](https://github.com/aayartsev/odpm/releases) odpm публикует подписанный репозиторий на GitHub Pages.

### Ключ репозитория

Тот же GPG-ключ, что и для APT; для RPM/DNF на GitHub Pages публикуется **ASCII-armored** файл (`.asc`), потому что `rpm --import` не принимает бинарный keyring APT (`gpg --dearmor`).

```bash
sudo rpm --import https://aayartsev.github.io/odpm/yum/odpm-archive-keyring.asc
sudo rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n' | grep -i yartsev || true
# ожидается fingerprint: 03040028F53D7AB8  Alexander Yartsev
```

**Pre-release** (`v4.3-rc1`, `*-beta`) — suite **`testing`** (сейчас пакеты здесь; `stable` — после финальных релизов):

```bash
sudo curl -fsSL https://raw.githubusercontent.com/aayartsev/odpm/4.3.0/packaging/yum/odpm-testing.repo \
  -o /etc/yum.repos.d/odpm.repo

sudo dnf makecache
sudo dnf install odpm
```

**Стабильные релизы** (`v4.3.0`, без `-rc`/`-beta`):

```bash
sudo curl -fsSL https://raw.githubusercontent.com/aayartsev/odpm/4.3.0/packaging/yum/odpm-stable.repo \
  -o /etc/yum.repos.d/odpm.repo

sudo dnf makecache
sudo dnf install odpm
```

> Ветка в URL (`4.3.0`) — текущая стабильная линия релиза; в репозитории нет ветки `main`.
> Если `odpm-archive-keyring.asc` ещё не опубликован на Pages после релиза, импортируйте ключ из бинарного keyring APT:
>
> ```bash
> curl -fsSL https://aayartsev.github.io/odpm/apt/odpm-archive-keyring.gpg -o /tmp/odpm-key.gpg
> gpg --no-default-keyring --keyring /tmp/odpm-key.gpg --export --armor | sudo rpm --import -
> ```

На RHEL / AlmaLinux / Rocky Linux вместо `dnf` используйте `yum` (формат `.repo` тот же).

Обновление при следующих релизах:

```bash
sudo dnf makecache && sudo dnf upgrade odpm
```

Полная таблица установки на разных ОС: [Установка odpm (все платформы)](README.md).

## Установка вручную (.rpm с GitHub Releases)

Скачайте `odpm-*.rpm` из [GitHub Releases](https://github.com/aayartsev/odpm/releases), из **Actions → Release packages → Artifacts** (`release-packages`) после push в `4.3.0` / `4.0-beta` / `4.0-rc1`, или соберите локально:

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
odpm --version
```

## Зависимости пакета

- **Requires:** `python3-packaging`, `git`
- **Recommends:** `moby-engine` / `docker`

Пакет ставит `/usr/bin/odpm` и `dev_project` в `python3/site-packages`.

При установке с GitHub Releases сверяйте checksum из `SHA256SUMS` релиза.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
