# Какую документацию читать

На сайте несколько **версий документации**. Переключатель — в шапке страницы (иконка версии). Ниже — краткая шпаргалка.

| Версия | Кому | Установка odpm |
|--------|------|----------------|
| **stable** (рекомендуется) | production, новые пользователи | APT suite `stable`, [GitHub Release](https://github.com/aayartsev/odpm/releases) stable |
| **4.3** / **4.3.0** | остаётесь на линии 4.3.x | `.deb` / `.rpm` релиза 4.3.0 |
| **4.4.2-beta** и др. `*-beta` | early adopters 4.4 | APT suite `testing`, [релиз beta](https://github.com/aayartsev/odpm/releases) |
| **dev** | разработка odpm, HEAD `4.4-dev` | не для end-user production |

## Быстрые ссылки

- Стабильная установка: [install/README.md](https://aayartsev.github.io/odpm/stable/install/) (или `/stable/install/` на этом сайте)
- Архив 4.3: `/4.3.0/install/` (alias **4.3** в переключателе)
- Beta 4.4: `/4.4.2-beta/install/`
- Разработка: `/dev/install/`

!!! tip "Версия odpm ≠ версия документации"
    `odpm --version` показывает **установленный** менеджер. Документация на сайте версионируется **отдельно** по релизным тегам и alias `stable`.

## Дальше

- [Установка odpm](../install/README.md)
- [Локальная разработка с нуля](local-dev-from-scratch.md)
