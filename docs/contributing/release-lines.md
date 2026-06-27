# Линии релизов и каналы публикации

Политика для **maintainers** odpm: какие git-ветки живы, куда попадают пакеты и документация, и как перевести **4.4.2-beta → stable 4.4.2**.

См. также: [packaging.md](packaging.md) (deb/rpm/wheel, CI), [ADR-001](adr-001-extensions-and-manifest-v2.md) (оси версий manifest vs manager).

## Git-линии

| Линия | Ветка / тег | Статус | Назначение |
|-------|-------------|--------|------------|
| **4.3.x** | `4.3.0`, тег `v4.3.0` | **заморожена** | Последний stable до 4.4; только критичные security-fix по решению maintainer (cherry-pick → patch tag). Новые фичи не добавляем. |
| **4.4.x** | `4.4-dev` | **заморожена** (patch only) | Линия 4.4; stable **v4.4.3** |
| **4.5.x** | `4.5-dev` | **заморожена** (patch only) | Линия 4.5; stable **v4.5.0**; архив: `v4.5.0-beta` |
| **4.6.x** | `4.6.0-dev` | **stable** | Debt closure D1–D5 **RELEASED** stable **v4.6.0**; архив: `v4.6.0-beta` |
| **4.7.x** | `4.7.0-dev` | **активная** | Scenario overlays (ADR-011), compose prefix (ADR-012), layered `.env` (ADR-013); pre-release на ветке |
| Старые | `3.0`, `4.0-*`, … | архив | Без поддержки; документация и релизы остаются на GitHub для истории. |

**Правило:** изменения 4.7 merge в `4.7.0-dev`. Линии 4.4 (`4.4-dev`), 4.5 (`4.5-dev`) и 4.6 (`4.6.0-dev`) — только patch/security по решению maintainer. Тег `v*` создаётся только когда `RELEASE_VERSION` в `dev_project/constants/scenarios.py` совпадает с тегом (проверяет `scripts/verify_release_tag_version.py` в CI).

### Константы в `scenarios.py`

| Константа | Когда менять | Пример сейчас |
|-----------|--------------|---------------|
| `RELEASE_VERSION` | Каждый релиз / pre-release на `4.7.0-dev` | `4.6.0` (до bump stable 4.7) |
| `LATEST_STABLE_RELEASE` | **Только** при выходе **stable** тега (без `-beta`/`-rc`) | `4.6.0` |
| `ODPM_VERSION` | Alias `RELEASE_VERSION`; не трогать отдельно | = `RELEASE_VERSION` |
| `MANIFEST_V1_CONTRACT_LINE` | Контракт flat `odpm.json`; не путать с версией менеджера | `4.0` |

После stable `v4.4.2` обновить hub [documentation-versions](../getting-started/documentation-versions.md) и install-доки, если меняются рекомендуемые ссылки (см. чеклист ниже).

## Каналы пакетов

Workflow: [`.github/workflows/release-packages.yml`](../../.github/workflows/release-packages.yml) (только push тега `v*`).

| Канал | URL / registry | Suite / условие | Содержимое |
|-------|----------------|-----------------|------------|
| **APT stable** | `https://aayartsev.github.io/odpm/apt/` → `dists/stable` | Stable tag (`v4.3.0`, `v4.4.2`, …) | `.deb` релиза; **merge** с live Pages (`--merge`) |
| **APT testing** | тот же host → `dists/testing` | Pre-release (`*-beta`, `*-rc`, `*-alpha`) | Beta/rc `.deb`; stable suite не затирается |
| **YUM stable / testing** | `https://aayartsev.github.io/odpm/yum/` | Те же правила, что APT | fc40/fc41/fc44 RPM; `.repo` на Pages: `odpm-stable.repo`, `odpm-testing.repo` |
| **GitHub Release** | [releases](https://github.com/aayartsev/odpm/releases) | Любой `v*` | deb, rpm, SHA256SUMS; wheel/sdist после `publish-pypi` |
| **PyPI production** | https://pypi.org/project/odpm/ | Stable tag | Job `publish-pypi`, `prerelease=false` |
| **TestPyPI** | https://test.pypi.org/project/odpm/ | Pre-release tag | Job `publish-pypi`, `prerelease=true` |
| **PyPI вручную** | — | Без тега | [`.github/workflows/publish-pypi.yml`](../../.github/workflows/publish-pypi.yml) — `workflow_dispatch`, ad-hoc |

Pre-release определяется суффиксом в `RELEASE_VERSION` / имени тега: `*-beta`, `*-rc`, `*-alpha` → **testing** + TestPyPI.

### Incremental publish (не затирать другой suite)

1. `scripts/fetch_pages_repo.sh` — скачать live `apt/` или `yum/` с GitHub Pages.
2. `scripts/build_apt_repo.sh --merge SUITE …` / `scripts/build_yum_repo.sh --merge SUITE …` — добавить пакеты только в нужный suite.
3. `publish-pages` — `scripts/mike_pages_finalize.sh` кладёт apt/yum поверх mike-дерева сайта.

One-shot bootstrap (если на Pages ещё нет `stable` или mike-версий):

| Workflow | Input | Действие |
|----------|-------|----------|
| **Bootstrap docs versions** | `v4.3.0` | `prepare_bootstrap_docs.sh` → mike `4.3.0`, aliases `stable`/`4.3`, default `stable` |
| **Bootstrap Pages repos** | `v4.3.0` | Скачать assets релиза, `--merge stable` для APT/YUM |

Оба checkout **`4.4-dev`** (скрипты merge/mike). Порядок ops: bootstrap docs → bootstrap repos → push `4.4-dev` (deploy `/dev/`) → retag beta при необходимости.

## Документация (mike)

| Версия на сайте | Alias | Как появляется | Аудитория |
|-----------------|-------|----------------|-----------|
| `stable` | default | Stable tag → `mike deploy VERSION stable --set-default stable` | Production, install по умолчанию |
| `4.3.0` | `4.3` | Bootstrap или ручной deploy | Линия 4.3.x |
| `4.6.0-beta` | — | Pre-release tag → mike deploy | Early adopters, debt closure D1–D5 |
| `4.5.0-beta`, … | — | Pre-release tag (без alias stable) | Архив early adopters |
| `dev` | — | Push `4.6.0-dev` ([docs.yml](../../.github/workflows/docs.yml)) | Разработчики odpm |

`site_url` в `mkdocs.yml`: `/stable/`. Пользовательский hub: [documentation-versions](../getting-started/documentation-versions.md).

Раздел `docs/contributing/**` **не** попадает в публичный MkDocs (`exclude_docs` в `mkdocs.yml`) — только для maintainers в git.

### Verify Pages после deploy (OPS-01 / OPS-02)

После `deploy-pages` CI вызывает `scripts/verify_pages_deploy.sh` (с retry на CDN lag):

| Workflow | Проверка |
|----------|----------|
| [docs.yml](../../.github/workflows/docs.yml) | `--version dev` → `/versions.json`, `/dev/install/linux-deb/` |
| [release-packages.yml](../../.github/workflows/release-packages.yml) `publish-pages` | pre-release: `/{VERSION}/install/`; stable: `stable` + `/{VERSION}/install/`; pre-release также APT `testing` |

Если push в `4.6.0-dev` и тег `v*` на одном коммите, **docs.yml** больше не деплоит Pages (release выигрывает). Если CDN отстаёт от ветки `gh-pages` (docs/apt 404 при успешном CI), вручную: workflow **[Redeploy Pages](../../.github/workflows/redeploy-pages.yml)** (`workflow_dispatch`, `verify_version=4.6.0-beta`).

Ручная проверка после релиза (если CDN отстаёт):

```bash
./scripts/verify_pages_deploy.sh --version stable
./scripts/verify_pages_deploy.sh --version dev
curl -fsSL https://aayartsev.github.io/odpm/apt/dists/stable/Release | head
```

Переменные: `PAGES_REPO_BASE`, `ODPM_PAGES_VERIFY_RETRIES` (default 6), `ODPM_PAGES_VERIFY_SLEEP` (default 10s).

## Чеклист: stable **v4.5.0** (после smoke beta)

Выполнять на `4.5-dev` после успешного smoke `v4.5.0-beta` (APT testing, TestPyPI, docs `/4.5.0-beta/`).

1. **Версия в коде**
   - [x] `RELEASE_VERSION = "4.5.0"` в `dev_project/constants/scenarios.py`
   - [x] `LATEST_STABLE_RELEASE = "4.5.0"`
   - [x] `debian/changelog`, `packaging/odpm.spec` — та же версия
2. **Release notes**
   - [x] `.github/release-notes/4.5.0.md` (ссылки на `/stable/`, не flat `/install/`)
3. **Install / hub docs**
   - [x] `docs/install/*`, `docs/en/install/*` — stable first; beta как archived
   - [x] `docs/getting-started/documentation-versions.md` (+ EN)
   - [x] reference docs: `requires_odpm` / version tables → `4.5.0`
4. **Commit + tag**
   - [x] Commit на `4.5-dev`, push
   - [x] `git tag v4.5.0` && `git push origin v4.5.0`
5. **CI (автоматически на тег)**
   - [x] `release-packages`: GitHub Release, APT/YUM **stable** merge, `publish-pages` → mike `4.5.0` + alias **stable**
   - [x] `publish-pypi` → **production PyPI**
6. **Проверка live**
   - [ ] `https://aayartsev.github.io/odpm/stable/` — 200, переключатель версий
   - [ ] `https://aayartsev.github.io/odpm/apt/dists/stable/Release` — 200
   - [ ] `pip install odpm` → `4.5.0`
7. **Следующий pre-release**
   - [x] Поднять `RELEASE_VERSION` на `4.6.0-beta` на `4.6.0-dev` **до** тега beta/stable 4.6

## Чеклист: линия **4.6.0-dev** (R0, после stable v4.5.0)

1. **Ветка и CI**
   - [x] Активная ветка `4.6.0-dev`
   - [x] `ci.yml`, `ci-docker.yml`, `docs.yml` → `4.6.0-dev`
2. **Версия в коде**
   - [x] `RELEASE_VERSION = "4.6.0-beta"`; `LATEST_STABLE_RELEASE = "4.5.0"`
   - [x] `debian/changelog`, `packaging/odpm.spec` synced
3. **Docs maintainer**
   - [x] `mkdocs.yml` `edit_uri` → `4.6.0-dev`
   - [ ] GitHub branch protection → `4.6.0-dev` (вручную в UI)
4. **Дальше**
   - [x] D1–D5 на `4.6.0-dev` (код) → tag `v4.6.0-beta` (pre-release smoke)
   - [ ] tag `v4.6.0` stable (единый debt release после beta smoke)

## Чеклист: stable **v4.6.0** (после smoke beta)

Выполнять на `4.6.0-dev` после успешного smoke `v4.6.0-beta` (APT testing, TestPyPI, docs `/4.6.0-beta/`).

1. **Версия в коде**
   - [ ] `RELEASE_VERSION = "4.6.0"` в `dev_project/constants/scenarios.py`
   - [ ] `LATEST_STABLE_RELEASE = "4.6.0"`
   - [ ] `debian/changelog`, `packaging/odpm.spec` — та же версия
2. **Release notes**
   - [ ] `.github/release-notes/4.6.0.md` (ссылки на `/stable/`, не flat `/install/`)
3. **Install / hub docs**
   - [ ] `docs/install/*`, `docs/en/install/*` — stable first; beta как archived
   - [ ] `docs/getting-started/documentation-versions.md` (+ EN)
   - [ ] reference docs: `requires_odpm` / version tables → `4.6.0`
4. **Commit + tag**
   - [ ] Commit на `4.6.0-dev`, push
   - [ ] `git tag v4.6.0` && `git push origin v4.6.0`
5. **CI (автоматически на тег)**
   - [ ] `release-packages`: GitHub Release, APT/YUM **stable** merge, `publish-pages` → mike `4.6.0` + alias **stable**
   - [ ] `publish-pypi` → **production PyPI**
6. **Проверка live**
   - [ ] `https://aayartsev.github.io/odpm/stable/` — 200, переключатель версий
   - [ ] `https://aayartsev.github.io/odpm/apt/dists/stable/Release` — 200
   - [ ] `pip install odpm` → `4.6.0`
7. **Runner ops**
   - [ ] `ODPM_GOLDEN_PATH_PROJECT`: `first_module` version `19.0.1.0`; odpm на runner → stable deb

## Чеклист: линия **4.7.0-dev** (features A+B+C+D, pre-release)

Выполнять на `4.7.0-dev` после merge треков scenario overlays, compose prefix, layered `.env` и compose network.

1. **Код и тесты**
   - [x] ADR-011 / ADR-012 / ADR-013 accepted; schema `scenarios`; `ODPM_COMPOSE_PREFIX`; `load_layered_dotenv_dict`
   - [x] ADR-014 accepted (compose stack network contract)
   - [x] `ODPM_COMPOSE_NETWORK` / `network_names.py` parse + `test_compose_network` (track D1)
   - [x] compose document generation + `apply_compose_network` + validate (track D2)
   - [x] sidecar `stack` network warning in manifest validate; plugins.md proxy (track D3)
   - [x] extended tests T10 + env-dotenv CHANGELOG (track D4–D5)
   - [x] Unit: scenario + compose prefix + `test_user_env_bootstrap`, `test_odpm_locale_env`, `test_env_substitution`
   - [x] Plan matrix: `test_scenario_overlay_marks_compose_fragments_stale`
   - [ ] `ci.yml`, `ci-docker.yml`, `docs.yml` → `4.7.0-dev` (если ещё на `4.6.0-dev`)
2. **Документация (pre-release)**
   - [x] `docs/reference/odpm-json.md` — блок `scenarios`
   - [x] `docs/reference/env-dotenv.md`, `config-hierarchy.md`, `database-state.md`, `odoo-conf.md`
   - [x] `CHANGELOG.md` `[Unreleased]` / `.github/release-notes/4.7.0.md` (A+B+C+D)
   - [x] `docs/reference/env-dotenv.md`, `locale.md` — `ODPM_COMPOSE_NETWORK`, layered `ODPM_LOCALE`
   - [x] `docs/getting-started/legacy-project.md` — compose network + prefix, layered `.env`
3. **Release commit (отдельно, после smoke)**
   - [ ] `RELEASE_VERSION = "4.7.0"` (или `4.7.0-beta` для pre-release)
   - [ ] `LATEST_STABLE_RELEASE = "4.6.0"` до stable `v4.7.0`
   - [ ] Закрыть `[Unreleased]` в CHANGELOG → `[4.7.0]`
   - [ ] `debian/changelog`, `packaging/odpm.spec`
   - [ ] `git tag v4.7.0` && push → `release-packages`, mike `4.7.0` + alias **stable**

## Чеклист: stable **v4.4.2** (архив, после smoke beta)

Выполнять на `4.4-dev` после успешного smoke `v4.4.2-beta` (APT testing, TestPyPI, docs `/4.4.2-beta/`).

1. **Версия в коде**
   - [ ] `RELEASE_VERSION = "4.4.2"` в `dev_project/constants/scenarios.py`
   - [ ] `LATEST_STABLE_RELEASE = "4.4.2"`
   - [ ] `debian/changelog`, `packaging/odpm.spec` — та же версия
2. **Release notes**
   - [ ] `.github/release-notes/4.4.2.md` (ссылки на `/stable/`, не flat `/install/`)
3. **Install / hub docs**
   - [ ] `docs/install/*`, `docs/en/install/*` — stable first; beta как optional; `LATEST_STABLE_RELEASE` в тексте
   - [ ] `docs/getting-started/documentation-versions.md` (+ EN)
4. **Commit + tag**
   - [ ] Commit на `4.4-dev`, push
   - [ ] `git tag v4.4.2` && `git push origin v4.4.2`
5. **CI (автоматически на тег)**
   - [ ] `release-packages`: GitHub Release, APT/YUM **stable** merge, `publish-pages` → mike `4.4.2` + alias **stable**
   - [ ] `publish-pypi` → **production PyPI**
6. **Проверка live**
   - [ ] `https://aayartsev.github.io/odpm/stable/` — 200, переключатель версий
   - [ ] `https://aayartsev.github.io/odpm/apt/dists/stable/Release` — 200
   - [ ] `pip install odpm` → `4.4.2`
7. **Следующий pre-release**
   - [ ] Поднять `RELEASE_VERSION` на `4.4.3-beta` или следующий плановый номер **до** следующего тега

## Чеклист: retag **v4.4.2-beta** (infra fix)

Если beta-тег указывал на commit **без** P0/P1 (merge APT, mike):

1. Удалить remote tag (maintainer): `git push origin :refs/tags/v4.4.2-beta`
2. Убедиться, что `4.4-dev` содержит merge-скрипты и mike CI
3. Пересоздать `v4.4.2-beta` на нужном commit, push tag
4. Дождаться `release-packages`; проверить `/4.4.2-beta/`, `apt/dists/testing`, TestPyPI

## Связанные файлы

| Путь | Назначение |
|------|------------|
| [`packaging/apt/README.md`](../../packaging/apt/README.md) | APT keyring, reprepro, local smoke |
| [`packaging/yum/README.md`](../../packaging/yum/README.md) | `.repo` шаблоны, createrepo |
| [`scripts/mike_pages_deploy.sh`](../../scripts/mike_pages_deploy.sh) | Deploy версии docs |
| [`scripts/mike_pages_finalize.sh`](../../scripts/mike_pages_finalize.sh) | Overlay apt/yum на site tree |
| [`.github/release-notes/`](../../.github/release-notes/) | Текст GitHub Release (обязателен для тега) |
