import importlib.metadata

from base_provider.const import EntrypointGroup, EntrypointType


def get_entrypoint(
        group: EntrypointGroup,
        name: EntrypointType = EntrypointType.TARGET,
        default: EntrypointType = EntrypointType.BASIC,
) -> importlib.metadata.EntryPoint:
    """Get an entrypoint from the given group and name.

    Args:
        group: The entrypoint group to search in
        name: The preferred entrypoint name to look for
        default: Fallback entrypoint name if preferred not found

    Returns:
        The found entrypoint

    Raises:
        LookupError: If neither preferred nor default entrypoint found
    """
    entrypoints = get_entrypoints(group)

    try:
        return entrypoints.select(name=name)[0]
    except (KeyError, IndexError):
        try:
            return entrypoints.select(name=default)[0]
        except (KeyError, IndexError) as e:
            raise LookupError(
                f"No entrypoint found in group '{group.group_name}' "
                f"for names '{name}' or '{default}'"
            ) from e


def get_entrypoints(
    group: EntrypointGroup,
) -> list[importlib.metadata.EntryPoint]:
    """Get all entrypoints from the given group."""
    return importlib.metadata.entry_points(group=group.group_name)
