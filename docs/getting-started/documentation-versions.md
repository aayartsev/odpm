# Какую документацию читать

На сайте несколько **версий документации**. Переключатель — в шапке страницы (иконка версии). Ниже — краткая шпаргалка.

| Версия | Кому | Установка odpm |
|--------|------|----------------|
| **stable** (рекомендуется) | production, новые пользователи | APT/YUM ветка `stable` (**4.6.0**), [релиз v4.6.0](https://github.com/aayartsev/odpm/releases/tag/v4.6.0) |
| **4.6.0-beta** | архив предварительной версии 4.6 | APT/YUM **`testing`**, [релиз v4.6.0-beta](https://github.com/aayartsev/odpm/releases/tag/v4.6.0-beta) |
| **4.5.0-beta** | архив предварительной версии 4.5 | APT/YUM **`testing`**, [релиз v4.5.0-beta](https://github.com/aayartsev/odpm/releases/tag/v4.5.0-beta) |
| **4.4.3-beta**, **4.4.2-beta** и др. (архив) | архив предварительных версий 4.4 | [4.4.3-beta](https://github.com/aayartsev/odpm/releases/tag/v4.4.3-beta), [4.4.2-beta](https://github.com/aayartsev/odpm/releases/tag/v4.4.2-beta) |
| **dev** | разработка самого odpm | не для production |

## Быстрые ссылки

- Стабильная установка: `/stable/install/` (alias **stable**, сейчас **4.6.0**)
- Архив beta 4.6: `/4.6.0-beta/install/` · [инструкция APT](https://aayartsev.github.io/odpm/4.6.0-beta/install/linux-deb/)
- Архив 4.3: `/4.3.0/install/` (alias **4.3** в переключателе)
- Архив beta 4.5: `/4.5.0-beta/install/`
- Архив beta 4.4: `/4.4.3-beta/install/`, `/4.4.2-beta/install/`
- Разработка: `/dev/install/`

!!! tip "Версия odpm ≠ версия документации"
    `odpm --version` показывает **установленный** менеджер. Документация на сайте версионируется **отдельно** по релизным тегам и alias `stable`.

## Дальше

- [Установка odpm](../install/README.md)
- [Локальная разработка с нуля](local-dev-from-scratch.md)
