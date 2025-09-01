from functools import lru_cache
from importlib.metadata import EntryPoint, entry_points
from typing import Any, Final, Optional

from pydantic import BaseModel, Field, create_model

from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.exceptions import EntryPointError

# Type mapping for JSON schema to Python types
TYPE_MAPPING: Final[dict[str, type]] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": type(None),
}

# Entry point configuration constants
DEFAULT_ENTRY_POINT: Final[str] = "basic"
TARGET_ENTRY_POINT: Final[str] = "target"

# Schema property names to skip during model creation
SKIP_PROPERTIES: Final[frozenset[str]] = frozenset([
    "properties", 
    "required", 
    "default", 
    "additionalProperties",
    "type",
    "description",
    "title"
])

# Cache configuration
ENTRY_POINT_CACHE_SIZE: Final[int] = 128


@lru_cache(maxsize=ENTRY_POINT_CACHE_SIZE)
def get_entry_points(group: str) -> list[EntryPoint]:
    """Retrieve all entry points for a specific group with caching.
    
    Args:
        group: The entry point group name to search for
        
    Returns:
        List of EntryPoint objects found for the specified group
        
    Raises:
        EntryPointError: If entry point retrieval fails
    """
    if not group or not group.strip():
        raise EntryPointError("Entry point group name cannot be empty")
        
    try:
        entrypoints = entry_points(group=group.strip())
        return list(entrypoints)
    except Exception as e:
        raise EntryPointError(f"Failed to retrieve entry points for group '{group}': {e}") from e


def get_entrypoint(
    group: EntrypointGroup, 
    target_entrypoint: str = TARGET_ENTRY_POINT, 
    default_entrypoint: str = DEFAULT_ENTRY_POINT
) -> Optional[EntryPoint]:
    """Find a specific entry point within a group, with fallback to default.
    
    Args:
        group: The EntrypointGroup to search within
        target_entrypoint: The preferred entry point name to find
        default_entrypoint: Fallback entry point name if target is not found
        
    Returns:
        EntryPoint object if found, None otherwise
        
    Raises:
        EntryPointError: If entry point retrieval fails
    """
    if not isinstance(group, EntrypointGroup):
        raise EntryPointError("Group must be an EntrypointGroup instance")
        
    try:
        entrypoints = get_entry_points(group.group_name)
        
        # Create a lookup dictionary for better performance
        entrypoint_lookup = {ep.name: ep for ep in entrypoints}
        
        # First pass: look for target entry point
        if target_entrypoint in entrypoint_lookup:
            return entrypoint_lookup[target_entrypoint]

        # Second pass: look for default entry point
        if default_entrypoint in entrypoint_lookup:
            return entrypoint_lookup[default_entrypoint]

        return None
        
    except EntryPointError:
        raise
    except Exception as e:
        raise EntryPointError(f"Failed to retrieve entry point for group '{group.group_name}': {e}") from e


def create_pydantic_model_from_json_schema(
    class_name: str, 
    schema: dict[str, Any], 
    base_class: Optional[type[BaseModel]] = None
) -> type[BaseModel]:
    """Create a Pydantic model from a JSON schema with enhanced error handling.
    
    Args:
        class_name: Name for the generated Pydantic model class
        schema: JSON schema dictionary containing model definition
        base_class: Optional base class to inherit from
        
    Returns:
        Generated Pydantic model class
        
    Raises:
        ValueError: If schema is invalid or type mapping fails
        EntryPointError: If model creation fails
    """
    # Validate inputs
    if not class_name or not class_name.strip():
        raise ValueError("Class name cannot be empty")
        
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary")
        
    if "properties" not in schema:
        raise ValueError("Schema must contain 'properties' key")
        
    class_name = class_name.strip()
    properties = schema["properties"]
    
    if not isinstance(properties, dict):
        raise ValueError("Schema 'properties' must be a dictionary")
    
    fields = {}
    required_fields = set(schema.get("required", []))
    
    for prop_name, prop_info in properties.items():
        if not isinstance(prop_info, dict):
            continue
            
        # Skip internal schema properties
        if prop_name in SKIP_PROPERTIES:
            continue
            
        try:
            python_type = _resolve_property_type(
                prop_name, prop_info, class_name, properties
            )
            
            if python_type is None:
                continue  # Skip unresolvable types
                
            # Determine field configuration
            is_required = prop_name in required_fields
            default_value = prop_info.get("default", ... if is_required else None)
            description = prop_info.get("description", "")
            
            fields[prop_name] = (
                python_type, 
                Field(default=default_value, description=description)
            )
            
        except Exception as e:
            raise ValueError(f"Error processing property '{prop_name}': {e}") from e

    # Create the Pydantic model
    try:
        return create_model(class_name, __base__=base_class, **fields)
    except Exception as e:
        raise EntryPointError(f"Failed to create Pydantic model '{class_name}': {e}") from e


def _resolve_property_type(
    prop_name: str, 
    prop_info: dict[str, Any], 
    class_name: str, 
    all_properties: dict[str, Any]
) -> Optional[type]:
    """Resolve a JSON schema property to a Python type.
    
    Args:
        prop_name: Name of the property
        prop_info: Property information from schema
        class_name: Parent class name for nested types
        all_properties: All properties in the schema
        
    Returns:
        Resolved Python type or None if not resolvable
        
    Raises:
        ValueError: If type resolution fails
    """
    field_type = prop_info.get("type")
    
    if not field_type:
        return None  # Skip properties without type information
        
    if field_type == "array":
        return _resolve_array_type(prop_name, prop_info, class_name, all_properties)
    elif field_type == "object":
        return _resolve_object_type(prop_name, prop_info, class_name, all_properties)
    elif field_type in TYPE_MAPPING:
        return TYPE_MAPPING[field_type]
    else:
        raise ValueError(f"Unsupported field type '{field_type}' for property '{prop_name}'")


def _resolve_array_type(
    prop_name: str, 
    prop_info: dict[str, Any], 
    class_name: str, 
    all_properties: dict[str, Any]
) -> type:
    """Resolve an array property type."""
    if "items" not in prop_info:
        raise ValueError(f"Array property '{prop_name}' missing 'items' specification")
        
    item_type_info = prop_info["items"]
    item_type = item_type_info.get("type")
    
    if item_type == "object":
        nested_class_name = f"{class_name}_{_normalize_class_name(prop_name)}"
        nested_model = create_pydantic_model_from_json_schema(nested_class_name, item_type_info)
        return list[nested_model]
    elif item_type in TYPE_MAPPING:
        return list[TYPE_MAPPING[item_type]]
    else:
        raise ValueError(f"Unsupported array item type '{item_type}' for property '{prop_name}'")


def _resolve_object_type(
    prop_name: str, 
    prop_info: dict[str, Any], 
    class_name: str, 
    all_properties: dict[str, Any]
) -> type:
    """Resolve an object property type."""
    nested_class_name = f"{class_name}_{_normalize_class_name(prop_name)}"
    
    if prop_info.get("properties"):
        return create_pydantic_model_from_json_schema(nested_class_name, prop_info)
    elif prop_info.get("$ref"):
        ref_name = prop_info["$ref"].split("/")[-1]
        ref_info = all_properties.get(ref_name)
        if ref_info is None:
            raise ValueError(f"Reference '{ref_name}' not found in schema properties")
        return create_pydantic_model_from_json_schema(nested_class_name, ref_info)
    elif prop_info.get("additionalProperties", {}).get("$ref"):
        ref_name = prop_info["additionalProperties"]["$ref"].split("/")[-1]
        ref_info = all_properties.get(ref_name)
        if ref_info is None:
            raise ValueError(f"Additional properties reference '{ref_name}' not found")
        nested_type = create_pydantic_model_from_json_schema(nested_class_name, ref_info)
        return dict[str, nested_type]
    else:
        # Generic object without specific structure
        return dict[str, Any]


def _normalize_class_name(name: str) -> str:
    """Normalize a property name for use as a class name."""
    # Convert to title case and remove invalid characters
    normalized = "".join(word.title() for word in name.replace("_", " ").split())
    return normalized if normalized else "Property"
