from typing import Literal, NamedTuple, TypedDict


class MappedPath(NamedTuple):
    local: str
    docker: str


class SymlinksSources(NamedTuple):
    source_path: str
    link_path: str


class DebuggerPathRecord(TypedDict):
    localRoot: str
    remoteRoot: str


class DebuggerUnit(TypedDict):
    name: str
    type: Literal["python"]
    request: Literal["attach"]
    port: int
    host: Literal["localhost"]
    pathMappings: list[DebuggerPathRecord]
