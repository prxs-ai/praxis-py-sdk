import sys
from importlib.metadata import EntryPoint, entry_points

from base_agent.const import EntrypointGroup


def get_entry_points(group: str) -> list[EntryPoint]:
    if sys.version_info >= (3, 10):
        entrypoints = entry_points(group=group)
    else:
        entrypoints = entry_points()
    try:
        return entrypoints.get(group, [])
    except AttributeError:
        return entrypoints.select(group=group)


def get_entrypoint(
    group: EntrypointGroup, target_entrypoint: str = "target", default_entrypoint: str = "basic"
) -> EntryPoint:
    entrypoints = get_entry_points(group.group_name)
    try:
        return entrypoints.select(name=target_entrypoint)[0]
    except (KeyError, IndexError):
        return entrypoints.select(name=default_entrypoint)[0]
