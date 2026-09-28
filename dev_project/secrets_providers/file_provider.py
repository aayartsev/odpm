"""Built-in file secrets provider."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..host.cli.args import OdpmCliArgs
from ..project_env.secrets import import_secrets_from_path, read_secrets_source


class FileSecretsProvider:
    """Import ``--secrets-file`` or return the existing source map."""

    name = "file"

    def fetch(
        self,
        *,
        provider_config: Mapping[str, Any],
        credentials: Mapping[str, str],
        project_dir: str,
        arguments: OdpmCliArgs | None = None,
    ) -> dict[str, str]:
        del provider_config, credentials
        if arguments is not None and arguments.secrets_file:
            import_secrets_from_path(project_dir, arguments.secrets_file)
        loaded = read_secrets_source(project_dir)
        return dict(loaded) if loaded is not None else {}
