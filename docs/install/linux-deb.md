# Debian / Ubuntu (.deb)

Рекомендуемый способ на Linux. Полная таблица платформ: [Установка odpm (все платформы)](README.md) · docs: [stable](https://aayartsev.github.io/odpm/stable/install/linux-deb/).

## Установка через APT (обновления `apt upgrade`)

После [релизного тега](https://github.com/aayartsev/odpm/releases) odpm публикует подписанный репозиторий на GitHub Pages (`https://aayartsev.github.io/odpm/apt/`).

### Ключ репозитория (один раз)

Бинарный keyring для `signed-by=` (готов для `/usr/share/keyrings/`):

```bash
sudo curl -fsSL https://aayartsev.github.io/odpm/apt/odpm-archive-keyring.gpg \
  -o /usr/share/keyrings/odpm-archive-keyring.gpg
```

Проверка:

```bash
sudo gpg --no-default-keyring \
  --keyring /usr/share/keyrings/odpm-archive-keyring.gpg \
  --list-keys
# ожидается: 03040028F53D7AB8  Alexander Yartsev
```

### Stable (рекомендуется для production)

Suite **`stable`** — сейчас odpm **4.3.0** (тег `v4.3.0`, без `-rc`/`-beta`):

```bash
echo 'deb [signed-by=/usr/share/keyrings/odpm-archive-keyring.gpg] https://aayartsev.github.io/odpm/apt stable main' | sudo tee /etc/apt/sources.list.d/odpm.list

sudo apt update
sudo apt install odpm
odpm --version
# ожидается: odpm version: 4.3.0
```

### Pre-release (4.4 beta / RC)

Suite **`testing`** — сейчас **4.4.2-beta** и другие pre-release теги (`*-beta`, `*-rc*`):

```bash
echo 'deb [signed-by=/usr/share/keyrings/odpm-archive-keyring.gpg] https://aayartsev.github.io/odpm/apt testing main' | sudo tee /etc/apt/sources.list.d/odpm.list

sudo apt update
sudo apt install odpm
```

Инструкции и новые функции 4.4: [docs 4.4.2-beta](https://aayartsev.github.io/odpm/4.4.2-beta/install/linux-deb/).

Обновление при следующих релизах:

```bash
sudo apt update && sudo apt upgrade odpm
```

## Установка вручную (.deb с GitHub Releases)

Скачайте `odpm_*_all.deb` из [GitHub Releases](https://github.com/aayartsev/odpm/releases) для нужного тега (`v4.3.0` — stable, `v4.4.2-beta` — testing) или соберите локально:

```bash
./scripts/build_deb.sh
sudo apt install ./dist/odpm_*_all.deb
odpm --version
```

Сверяйте checksum из `SHA256SUMS` релиза.

## Зависимости пакета

- **Depends:** `python3 (>= 3.10)`, `python3-packaging`, `git`
- **Recommends:** Docker (`docker.io` / `moby-engine`)
- Без PyPI runtime-зависимостей

Пакет ставит `/usr/bin/odpm`, шаблоны и i18n в `python3/dist-packages`.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
