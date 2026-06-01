from __future__ import annotations

from typing import Any


def _agent_native_schema_type_name(value: object) -> str:
    typed_names = (
        (bool, "boolean"),
        (dict, "object"),
        (list, "array"),
        (str, "string"),
        (int, "integer"),
        (float, "number"),
    )
    if value is None:
        return "null"
    for value_type, type_name in typed_names:
        if isinstance(value, value_type):
            return type_name
    return type(value).__name__


def _agent_native_schema_value_matches_type(value: object, expected_type: str) -> bool:
    validators = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
    }
    validator = validators.get(expected_type)
    return True if validator is None else bool(validator(value))


def _agent_native_schema_object_issues(value: dict, schema: dict[str, Any], *, path: str) -> list[str]:
    issues: list[str] = []
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = [str(item) for item in list(schema.get("required") or []) if str(item)]
    missing = [field for field in required if field not in value]
    issues.extend(f"{path}.{field} is required" for field in missing)
    if schema.get("additionalProperties") is False:
        extra_fields = sorted(str(field) for field in value if str(field) not in properties)
        issues.extend(f"{path}.{field} is not allowed by output_schema" for field in extra_fields)
    for field, field_schema in properties.items():
        if field in value:
            issues.extend(agent_native_schema_validation_issues(value[field], field_schema, path=f"{path}.{field}"))
    return issues


def _agent_native_schema_array_issues(value: list, schema: dict[str, Any], *, path: str) -> list[str]:
    item_schema = schema.get("items")
    if not isinstance(item_schema, dict):
        return []
    issues: list[str] = []
    for index, item in enumerate(value):
        issues.extend(agent_native_schema_validation_issues(item, item_schema, path=f"{path}[{index}]"))
    return issues


def agent_native_schema_validation_issues(value: object, schema: object, *, path: str = "$") -> list[str]:
    if not isinstance(schema, dict):
        return []
    issues: list[str] = []
    expected_type = str(schema.get("type") or "").strip()
    if expected_type and not _agent_native_schema_value_matches_type(value, expected_type):
        return [f"{path} expected {expected_type}, got {_agent_native_schema_type_name(value)}"]
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        issues.append(f"{path} must be one of {enum_values!r}")
    if expected_type == "object" and isinstance(value, dict):
        issues.extend(_agent_native_schema_object_issues(value, schema, path=path))
    elif expected_type == "array" and isinstance(value, list):
        issues.extend(_agent_native_schema_array_issues(value, schema, path=path))
    return issues


def agent_native_result_scaffold_from_schema(schema: object) -> object:
    if not isinstance(schema, dict):
        return None
    expected_type = str(schema.get("type") or "").strip()
    if expected_type == "object":
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        property_schemas = {str(field): field_schema for field, field_schema in properties.items()}
        required = [str(item) for item in list(schema.get("required") or []) if str(item)]
        ordered_fields = list(dict.fromkeys(required))
        ordered_fields.extend(field for field in property_schemas if field not in ordered_fields)
        return {field: agent_native_result_scaffold_from_schema(property_schemas.get(field)) for field in ordered_fields}
    if expected_type == "array":
        item_schema = schema.get("items")
        return [agent_native_result_scaffold_from_schema(item_schema)] if isinstance(item_schema, dict) else [None]
    return None
