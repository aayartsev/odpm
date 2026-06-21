# Какую документацию читать

На сайте несколько **версий документации**. Переключатель — в шапке страницы (иконка версии). Ниже — краткая шпаргалка.

| Версия | Кому | Установка odpm |
|--------|------|----------------|
| **stable** (рекомендуется) | production, новые пользователи | APT suite `stable` (**4.4.2**), [релиз v4.4.2](https://github.com/aayartsev/odpm/releases/tag/v4.4.2) |
| **4.3** / **4.3.0** | остаётесь на линии 4.3.x | `.deb` / `.rpm` релиза 4.3.0 |
| **4.4.2-beta** и др. `*-beta` | архив early adopters | APT suite `testing`, [релиз beta](https://github.com/aayartsev/odpm/releases/tag/v4.4.2-beta) |
| **dev** | разработка odpm, HEAD `4.4-dev` | не для end-user production |

## Быстрые ссылки

- Стабильная установка: `/stable/install/` (alias **stable**, сейчас **4.4.2**)
- Архив 4.3: `/4.3.0/install/` (alias **4.3** в переключателе)
- Beta 4.4 (архив): `/4.4.2-beta/install/`
- Разработка: `/dev/install/`

!!! tip "Версия odpm ≠ версия документации"
    `odpm --version` показывает **установленный** менеджер. Документация на сайте версионируется **отдельно** по релизным тегам и alias `stable`.

## Дальше

- [Установка odpm](../install/README.md)
- [Локальная разработка с нуля](local-dev-from-scratch.md)
