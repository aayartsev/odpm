# Debian / Ubuntu (.deb)

Рекомендуемый способ на Linux.

## Установка через APT (обновления `apt upgrade`)

После [релизного тега](https://github.com/aayartsev/odpm/releases) odpm публикует подписанный репозиторий на GitHub Pages.

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

**Pre-release** (`v4.3-rc1`, `*-beta`) — suite **`testing`** (сейчас пакеты здесь; `stable` — после финальных релизов):

```bash
echo 'deb [signed-by=/usr/share/keyrings/odpm-archive-keyring.gpg] https://aayartsev.github.io/odpm/apt testing main' | sudo tee /etc/apt/sources.list.d/odpm.list

sudo apt update
sudo apt install odpm
```

**Стабильные релизы** (`v4.3.0`, без `-rc`/`-beta`):

```bash
echo 'deb [signed-by=/usr/share/keyrings/odpm-archive-keyring.gpg] https://aayartsev.github.io/odpm/apt stable main' | sudo tee /etc/apt/sources.list.d/odpm.list

sudo apt update
sudo apt install odpm
```

Обновление при следующих релизах:

```bash
sudo apt update && sudo apt upgrade odpm
```

Полная таблица установки на разных ОС: [Установка odpm (все платформы)](README.md).

## Установка вручную (.deb с GitHub Releases)

Скачайте `odpm_*_all.deb` из [GitHub Releases](https://github.com/aayartsev/odpm/releases), из **Actions → Release packages → Artifacts** (`release-packages`) после push в `4.0-beta` / `4.0-rc1` / `main`, или соберите локально:

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

При установке с GitHub Releases сверяйте checksum из `SHA256SUMS` релиза.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
