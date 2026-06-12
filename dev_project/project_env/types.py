from typing import Literal, NamedTuple, TypedDict


from ..symlinks.types import SymlinksSources

class MappedPath(NamedTuple):
    local: str
    docker: str


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
