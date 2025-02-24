
import sys
from importlib.metadata import EntryPoint, entry_points


def get_entry_points(group: str) -> list[EntryPoint]:
    if sys.version_info >= (3, 10):
        entrypoints = entry_points(group=group)

    entrypoints = entry_points()
    try:
        return entrypoints.get(group, [])
    except AttributeError:
        return entrypoints.select(group=group)
