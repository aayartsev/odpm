"""Single-pass resolution of project dependencies including OCA transitive deps."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable


def parse_oca_dependencies_line(line: str) -> str | None:
    """Parse one line from oca_dependencies.txt into a git URL."""
    oca_dep_string = line.strip()
    if not oca_dep_string:
        return None
    if "#" in oca_dep_string:
        return None
    if "github" not in oca_dep_string:
        oca_dep_string = f"https://github.com/OCA/{oca_dep_string}.git"
    return oca_dep_string


def read_oca_dependency_urls(project_path: str) -> list[str]:
    """Read dependency URLs from oca_dependencies.txt under project_path."""
    oca_dependencies_txt = os.path.join(project_path, "oca_dependencies.txt")
    if not os.path.exists(oca_dependencies_txt):
        return []
    urls: list[str] = []
    with open(oca_dependencies_txt) as oca_deps:
        for line in oca_deps.readlines():
            url = parse_oca_dependencies_line(line)
            if url:
                urls.append(url)
    return urls


def resolve_dependency_urls(
    seed_urls: Iterable[str],
    get_oca_urls: Callable[[str], list[str]],
    *,
    initial_extra_urls: Iterable[str] | None = None,
) -> list[str]:
    """
    Resolve full dependency list in one pass.

    seed_urls: dependencies from odpm.json (stable order).
    initial_extra_urls: URLs discovered from developing project oca_dependencies.txt
        before dependency iteration (same as legacy append-before-loop behavior).
    get_oca_urls: callback for a checked-out dependency; returns new URLs from its
        oca_dependencies.txt (project checkout is caller responsibility).
    """
    queue: list[str] = []
    queued: set[str] = set()
    ordered: list[str] = []
    processed: set[str] = set()

    def enqueue(urls: Iterable[str]) -> None:
        for url in urls:
            normalized = (url or "").strip()
            if not normalized or normalized in queued:
                continue
            queued.add(normalized)
            queue.append(normalized)

    enqueue(seed_urls)
    if initial_extra_urls:
        enqueue(initial_extra_urls)

    while queue:
        dependency_string = queue.pop(0)
        if dependency_string in processed:
            continue
        processed.add(dependency_string)
        ordered.append(dependency_string)
        enqueue(get_oca_urls(dependency_string))

    return ordered
