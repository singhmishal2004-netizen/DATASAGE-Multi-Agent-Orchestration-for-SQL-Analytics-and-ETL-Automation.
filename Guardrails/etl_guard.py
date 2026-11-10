import os


ALLOWED_OPERATIONS = {
    "drop_duplicates",
    "drop_nulls",
    "fill_nulls",
    "rename_columns",
    "select_columns",
    "sort_values"
}

ALLOWED_FORMATS = {"csv", "json", "parquet"}


def resolve_data_path(project_root: str, path: str) -> str:
    """
    Resolve a path and ensure it stays inside the project's data directory.
    """

    data_root = os.path.realpath(os.path.join(project_root, "data"))

    if os.path.isabs(path):
        resolved_path = os.path.realpath(path)
    else:
        resolved_path = os.path.realpath(os.path.join(project_root, path))

    if os.path.commonpath([data_root, resolved_path]) != data_root:
        raise ValueError("File access outside the data directory is not allowed.")

    return resolved_path


def validate_format(file_format: str) -> bool:
    return file_format.lower() in ALLOWED_FORMATS


def validate_transformation_plan(plan: dict) -> tuple[bool, str]:
    """
    Validate the LLM-generated transformation plan.
    Only explicitly supported Pandas operations are allowed.
    """

    if not isinstance(plan, dict):
        return False, "Transformation plan must be a JSON object."

    operations = plan.get("operations")

    if not isinstance(operations, list) or not operations:
        return False, "No valid transformation operations provided."

    for item in operations:

        if not isinstance(item, dict):
            return False, "Each operation must be a JSON object."

        operation = item.get("operation")

        if operation not in ALLOWED_OPERATIONS:
            return False, f"Unsupported operation: {operation}"

        if operation == "drop_duplicates":
            continue

        if operation in {"drop_nulls", "select_columns", "sort_values"}:
            columns = item.get("columns")

            if not isinstance(columns, list) or not columns:
                return False, f"{operation} requires a non-empty columns list."

        elif operation == "fill_nulls":
            column = item.get("column")

            if not isinstance(column, str) or not column:
                return False, "fill_nulls requires a column name."

            if "value" not in item:
                return False, "fill_nulls requires a value."

        elif operation == "rename_columns":
            mapping = item.get("mapping")

            if not isinstance(mapping, dict) or not mapping:
                return False, "rename_columns requires a non-empty mapping."

    return True, "Transformation plan passed validation."