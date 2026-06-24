# Fedora / RHEL (.rpm)

Рекомендуемый способ на **Fedora 40+** (системный Python ≥ 3.10). В YUM-репозитории публикуются сборки для Fedora 40, 41 и 44 (`fc40` / `fc41` / `fc44` в имени RPM). На EL9 / RHEL 9 штатный `python3` 3.9 не поддерживается — используйте pip/pipx или соберите RPM на Fedora.

Полная таблица платформ: [Установка odpm (все платформы)](README.md) · документация stable: [4.6.0](https://aayartsev.github.io/odpm/stable/install/fedora-rpm/).

## Установка через DNF (обновления `dnf upgrade`)

После [релизного тега](https://github.com/aayartsev/odpm/releases) odpm публикует подписанный репозиторий на GitHub Pages (`https://aayartsev.github.io/odpm/yum/`).

### Ключ репозитория

Тот же GPG-ключ, что и для APT; для RPM/DNF на GitHub Pages публикуется **ASCII-armored** файл (`.asc`):

```bash
sudo rpm --import https://aayartsev.github.io/odpm/yum/odpm-archive-keyring.asc
sudo rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n' | grep -i yartsev || true
# ожидается fingerprint: 03040028F53D7AB8  Alexander Yartsev
```

### Stable (рекомендуется для production)

Ветка **`stable`** — сейчас odpm **4.6.0**:

```bash
sudo curl -fsSL https://aayartsev.github.io/odpm/yum/odpm-stable.repo \
  -o /etc/yum.repos.d/odpm.repo

sudo dnf makecache
sudo dnf install odpm
odpm --version
# ожидается: odpm version: 4.6.0
```

### Предварительные версии (архив)

Активного pre-release сейчас нет. Архив инструкций для beta: [4.6.0-beta](https://aayartsev.github.io/odpm/4.6.0-beta/install/fedora-rpm/) · [4.5.0-beta](https://aayartsev.github.io/odpm/4.5.0-beta/install/fedora-rpm/) · [4.4.3-beta](https://aayartsev.github.io/odpm/4.4.3-beta/install/fedora-rpm/) · [4.4.2-beta](https://aayartsev.github.io/odpm/4.4.2-beta/install/fedora-rpm/).

Ветка **`testing`** в YUM по-прежнему используется для будущих pre-release (`https://aayartsev.github.io/odpm/yum/odpm-testing.repo`); сейчас там могут оставаться пакеты архивных beta.

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

## Установка вручную (.rpm с GitHub Releases)

Скачайте `odpm-*.rpm` из [GitHub Releases](https://github.com/aayartsev/odpm/releases) для тега `v4.6.0` (stable), `v4.6.0-beta` (архив testing), `v4.5.0` (архив stable), `v4.5.0-beta` (архив testing), `v4.4.3` (архив stable), `v4.4.3-beta` (архив testing) или `v4.4.2-beta` (архив beta), или соберите локально:

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
odpm --version
```

Сверяйте контрольную сумму из `SHA256SUMS` релиза.

## Зависимости пакета

- **Requires:** `python3-packaging`, `git`
- **Recommends:** `moby-engine` / `docker`

Пакет ставит `/usr/bin/odpm` и `dev_project` в `python3/site-packages`.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
