# macOS (pipx)

There is no native `.pkg` for macOS yet. Install via **pipx** (isolated from system Python).

## Requirements

- [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) **4.25+** (Compose **v2.23+** recommended; older builds may not support `docker compose up -y` and can try to pull local Odoo images from Docker Hub)
- [git](https://git-scm.com/)
- Python 3.10+ (often preinstalled; otherwise [python.org](https://www.python.org/) or Homebrew)

## Install odpm

From a release wheel:

```bash
pipx install odpm  # when published on PyPI
# or from a clone / wheel file:
pipx install /path/to/odpm
odpm --version
```

On Apple Silicon, Docker Desktop may emulate linux/amd64 or use arm64 images — ensure Docker is running.

Full install table: [Installing odpm (all platforms)](README.md).

## Next

[Local dev from scratch](../getting-started/local-dev-from-scratch.md)
