import sys
from importlib.metadata import EntryPoint, entry_points


def get_entry_points(group: str) -> list[EntryPoint]:
    if sys.version_info >= (3, 10):
        entrypoints = entry_points(group=group)
    else:
        entrypoints = entry_points()
    try:
        return entrypoints.get(group, [])
    except AttributeError:
        return entrypoints.select(group=group)


def get_entrypoint(group_name: str, target_entrypoint: str = "target", default_entrypoint: str = "basic") -> EntryPoint:
    entrypoints = get_entry_points(group_name)
    try:
        return entrypoints.select(name=target_entrypoint)[0]
    except KeyError:
        return entrypoints.select(name=default_entrypoint)[0]



def default_stringify_rule_for_arguments(args):
    if len(args) == 1:
        return str(args[0])
    else:
        return str(tuple(args))
