# macOS (pipx)

На macOS нативного `.pkg` пока нет. Установите через **pipx** (изолированно от системного Python).

## Требования

- [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
- [git](https://git-scm.com/)
- Python 3.10+ (часто уже есть; иначе [python.org](https://www.python.org/) или Homebrew)

## Установка odpm

Из wheel релиза:

```bash
pipx install odpm  # когда пакет опубликован на PyPI
# или из клона / wheel файла:
pipx install /path/to/odpm
odpm --version
```

На Apple Silicon Docker Desktop эмулирует linux/amd64 или использует arm64-образы — убедитесь, что Docker запущен.

## Дальше

[Локальная разработка с нуля](../getting-started/local-dev-from-scratch.md)
