# Какую документацию читать

На сайте несколько **версий документации**. Переключатель — в шапке страницы (иконка версии). Ниже — краткая шпаргалка.

| Версия | Кому | Установка odpm |
|--------|------|----------------|
| **stable** (рекомендуется) | production, новые пользователи | APT suite `stable` (**4.5.0**), [релиз v4.5.0](https://github.com/aayartsev/odpm/releases/tag/v4.5.0) |
| **4.6.0-beta** | early adopters линии 4.6 (debt closure) | APT/YUM **`testing`**, [релиз v4.6.0-beta](https://github.com/aayartsev/odpm/releases/tag/v4.6.0-beta) |
| **4.5.0-beta** | архив pre-release 4.5 | APT/YUM **`testing`**, [релиз v4.5.0-beta](https://github.com/aayartsev/odpm/releases/tag/v4.5.0-beta) |
| **4.4.3-beta**, **4.4.2-beta** и др. (архив) | архив pre-release 4.4 | [4.4.3-beta](https://github.com/aayartsev/odpm/releases/tag/v4.4.3-beta), [4.4.2-beta](https://github.com/aayartsev/odpm/releases/tag/v4.4.2-beta) |
| **dev** | разработка odpm, HEAD `4.6.0-dev` | не для end-user production |

## Быстрые ссылки

- Стабильная установка: `/stable/install/` (alias **stable**, сейчас **4.5.0**)
- Beta 4.6: `/4.6.0-beta/install/`
- Архив 4.3: `/4.3.0/install/` (alias **4.3** в переключателе)
- Beta 4.5: `/4.5.0-beta/install/`
- Beta 4.4 (архив): `/4.4.3-beta/install/`, `/4.4.2-beta/install/`
- Разработка: `/dev/install/`

!!! tip "Версия odpm ≠ версия документации"
    `odpm --version` показывает **установленный** менеджер. Документация на сайте версионируется **отдельно** по релизным тегам и alias `stable`.

## Дальше

- [Установка odpm](../install/README.md)
- [Локальная разработка с нуля](local-dev-from-scratch.md)
