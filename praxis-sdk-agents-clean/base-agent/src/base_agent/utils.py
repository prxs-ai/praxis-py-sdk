import sys
from importlib.metadata import EntryPoint, entry_points

from base_agent.const import EntrypointGroup
from pydantic import Field, create_model


TYPE_MAPPING: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": type(None),
}



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
) -> EntryPoint | None:
    entrypoints = get_entry_points(group.group_name)
    for ep in entrypoints:
        if ep.name == target_entrypoint:
            return ep
    
    for ep in entrypoints:
        if ep.name == default_entrypoint:
            return ep
    
    return None


def create_pydantic_model_from_json_schema(klass, schema, base_klass = None):
    """
    Creates a Pydantic model from a JSON schema.
    """
    fields = {}
    for prop_name, prop_info in schema['properties'].items():
        field_type = prop_info.get('type', 'default') # if no type, then it's the default?
        py_type = None
        if field_type == 'default' or prop_name in ['properties', 'required', 'default', 'additionalProperties']:
            continue
        if field_type == 'array':
            item_type = prop_info['items']['type']
            if item_type == 'object':
                py_type = list[create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", prop_info['items'])]
            else:
                py_type = list[TYPE_MAPPING.get(item_type, None)]
        elif field_type == 'object':
            if prop_info.get('properties', None):
                py_type = create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", prop_info)
            elif prop_info.get('$ref'):
                # NOTE: We probably need to make this more robust
                ref_info = schema['properties'].get(prop_info['$ref'].split("/")[-1])
                py_type = create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", ref_info)
            elif prop_info.get('additionalProperties', {}).get('$ref', None):
                ref_info = schema['properties'].get(prop_info['additionalProperties']['$ref'].split("/")[-1])
                py_type = dict[str, create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", ref_info)]
            else:
                raise Exception(f"Object Error, {py_type} {prop_name} for {field_type}")
        elif TYPE_MAPPING.get(field_type):
            py_type = TYPE_MAPPING[field_type]

        if py_type is None:
            raise Exception(f"Error, {py_type} for {field_type}")

        default = prop_info.get('default', ...) if prop_name in schema.get('required', []) else ...
        description = prop_info.get('description', '')
        fields[prop_name] = (py_type, Field(default, description=description))

    return create_model(klass, __base__=base_klass, **fields)
