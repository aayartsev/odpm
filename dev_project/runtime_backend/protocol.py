"""Protocol for stack runtime engines (compose today; Helm later)."""

from __future__ import annotations

from typing import Protocol


class RuntimeBackend(Protocol):
    def ensure_base_image(self) -> None: ...

    def up(self) -> None: ...

    def down(self) -> None: ...

    def logs(self) -> None: ...

    def exec(self) -> None: ...
