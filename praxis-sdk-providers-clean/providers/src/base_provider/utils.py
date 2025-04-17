import importlib.metadata

from base_provider.const import EntrypointGroup, EntrypointType


def get_entrypoint(
    group: EntrypointGroup,
    name: EntrypointType = EntrypointType.TARGET,
    default: EntrypointType = EntrypointType.BASIC,
) -> importlib.metadata.EntryPoint:
    """Get an entrypoint from the given group and name."""
    entrypoints = get_entrypoints(group)

    try:
        return entrypoints.select(name=name)[0]
    except (KeyError, IndexError):
        return entrypoints.select(name=default)[0]


def get_entrypoints(
    group: EntrypointGroup,
) -> list[importlib.metadata.EntryPoint]:
    """Get all entrypoints from the given group."""
    return importlib.metadata.entry_points(group=group.group_name)
