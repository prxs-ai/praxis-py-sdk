from functools import lru_cache
from importlib.metadata import EntryPoint, entry_points
from typing import Any, Final

from pydantic import BaseModel, Field, create_model

from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.exceptions import EntryPointError

TYPE_MAPPING: Final[dict[str, type]] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": type(None),
}

# Default entry point configuration
DEFAULT_ENTRY_POINT: Final[str] = "basic"
TARGET_ENTRY_POINT: Final[str] = "target"

# Schema property names to skip during model creation
SKIP_PROPERTIES: Final[list[str]] = ["properties", "required", "default", "additionalProperties"]


@lru_cache(maxsize=128)
def get_entry_points(group: str) -> list[EntryPoint]:
    """Retrieve all entry points for a specific group with caching.
    
    Args:
        group: The entry point group name to search for
        
    Returns:
        List of EntryPoint objects found for the specified group
    """
    entrypoints = entry_points(group=group)
    return list(entrypoints)


def get_entrypoint(
    group: EntrypointGroup, target_entrypoint: str = TARGET_ENTRY_POINT, default_entrypoint: str = DEFAULT_ENTRY_POINT
) -> EntryPoint | None:
    """Find a specific entry point within a group, with fallback to default.
    
    Args:
        group: The EntrypointGroup to search within
        target_entrypoint: The preferred entry point name to find
        default_entrypoint: Fallback entry point name if target is not found
        
    Returns:
        EntryPoint object if found, None otherwise
    """
    try:
        entrypoints = get_entry_points(group.group_name)
        
        # First pass: look for target entry point
        for entry_point in entrypoints:
            if entry_point.name == target_entrypoint:
                return entry_point

        # Second pass: look for default entry point
        for entry_point in entrypoints:
            if entry_point.name == default_entrypoint:
                return entry_point

        return None
    except Exception as e:
        raise EntryPointError(f"Failed to retrieve entry point for group '{group.group_name}': {e}") from e


def create_pydantic_model_from_json_schema(
    class_name: str, schema: dict[str, Any], base_class: type[BaseModel] | None = None
) -> type[BaseModel]:
    """Create a Pydantic model from a JSON schema.
    
    Args:
        class_name: Name for the generated Pydantic model class
        schema: JSON schema dictionary containing model definition
        base_class: Optional base class to inherit from
        
    Returns:
        Generated Pydantic model class
        
    Raises:
        ValueError: If schema is invalid or type mapping fails
        KeyError: If required schema properties are missing
    """
    if not isinstance(schema, dict) or "properties" not in schema:
        raise ValueError("Schema must be a dictionary with 'properties' key")
        
    fields = {}
    properties = schema["properties"]
    
    for prop_name, prop_info in properties.items():
        if not isinstance(prop_info, dict):
            continue
            
        field_type = prop_info.get("type", "default")
        python_type = None
        
        if field_type == "default" or prop_name in SKIP_PROPERTIES:
            continue
            
        try:
            if field_type == "array":
                if "items" not in prop_info:
                    raise ValueError(f"Array property '{prop_name}' missing 'items' specification")
                    
                item_type = prop_info["items"].get("type")
                if item_type == "object":
                    nested_class_name = f"{class_name}_{prop_name.title()}"
                    python_type = list[create_pydantic_model_from_json_schema(nested_class_name, prop_info["items"])]
                elif item_type in TYPE_MAPPING:
                    python_type = list[TYPE_MAPPING[item_type]]
                else:
                    raise ValueError(f"Unsupported array item type '{item_type}' for property '{prop_name}'")
                    
            elif field_type == "object":
                nested_class_name = f"{class_name}_{prop_name.title()}"
                
                if prop_info.get("properties"):
                    python_type = create_pydantic_model_from_json_schema(nested_class_name, prop_info)
                elif prop_info.get("$ref"):
                    ref_name = prop_info["$ref"].split("/")[-1]
                    ref_info = properties.get(ref_name)
                    if ref_info is None:
                        raise ValueError(f"Reference '{ref_name}' not found in schema properties")
                    python_type = create_pydantic_model_from_json_schema(nested_class_name, ref_info)
                elif prop_info.get("additionalProperties", {}).get("$ref"):
                    ref_name = prop_info["additionalProperties"]["$ref"].split("/")[-1]
                    ref_info = properties.get(ref_name)
                    if ref_info is None:
                        raise ValueError(f"Additional properties reference '{ref_name}' not found")
                    nested_type = create_pydantic_model_from_json_schema(nested_class_name, ref_info)
                    python_type = dict[str, nested_type]
                else:
                    raise ValueError(f"Object property '{prop_name}' has insufficient type information")
                    
            elif field_type in TYPE_MAPPING:
                python_type = TYPE_MAPPING[field_type]
            else:
                raise ValueError(f"Unsupported field type '{field_type}' for property '{prop_name}'")
                
        except (KeyError, TypeError) as e:
            raise ValueError(f"Error processing property '{prop_name}': {e}") from e

        if python_type is None:
            raise ValueError(f"Failed to determine Python type for property '{prop_name}'")

        is_required = prop_name in schema.get("required", [])
        default_value = prop_info.get("default", ... if is_required else None)
        description = prop_info.get("description", "")
        
        fields[prop_name] = (python_type, Field(default=default_value, description=description))

    try:
        return create_model(class_name, __base__=base_class, **fields)
    except Exception as e:
        raise ValueError(f"Failed to create Pydantic model '{class_name}': {e}") from e
