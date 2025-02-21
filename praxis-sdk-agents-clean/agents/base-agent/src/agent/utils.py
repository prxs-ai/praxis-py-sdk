
import sys
import uuid
from importlib.metadata import EntryPoint, entry_points

import ray


def get_entry_points(group: str) -> list[EntryPoint]:
    if sys.version_info >= (3, 10):
        entrypoints = entry_points(group=group)

    entrypoints = entry_points()
    try:
        return entrypoints.get(group, [])
    except AttributeError:
        return entrypoints.select(group=group)



@ray.remote
def generate_request_id() -> str:
   # Generate a unique idempotency token.
   return uuid.uuid4().hex
