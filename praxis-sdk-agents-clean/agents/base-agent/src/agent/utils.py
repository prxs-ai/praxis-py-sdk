
import importlib
import sys


def get_entry_points(group: str) -> list[importlib.metadata.EntryPoint]:
    if sys.version_info >= (3, 10):
        entrypoints = importlib.metadata.entry_points(group=group)

    entrypoints = importlib.metadata.entry_points()
    try:
        return entrypoints.get(group, [])
    except AttributeError:
        return entrypoints.select(group=group)

def get_entry_point(group: str, name: str) -> importlib.metadata.EntryPoint:
    try:
        return get_entry_points(group=group)[name]
    except KeyError:
        raise
