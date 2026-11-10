import sqlglot
from sqlglot import exp


# SQL operations that must never be executed by DataSage.
BLOCKED_NODES = {
    "insert",
    "update",
    "delete",
    "create",
    "drop",
    "alter",
    "truncatetable",
    "merge",
    "command",
    "copy",
    "grant",
    "revoke",
    "into",       # Blocks SELECT INTO.
    "lock",       # Blocks locking clauses such as FOR UPDATE.
}


def validate_sql(query: str) -> tuple[bool, str]:
    """
    Validate generated PostgreSQL SQL.

    Only SELECT-style queries are allowed.
    Returns (is_safe, reason).
    """

    if not query or not query.strip():
        return False, "SQL query is empty."

    try:
        parsed_queries = sqlglot.parse(query, read="postgres")

        # Reject empty or multiple SQL statements.
        if len(parsed_queries) != 1 or parsed_queries[0] is None:
            return False, "Only one SQL statement is allowed."

        parsed_query = parsed_queries[0]

        # Only allow SELECT and set-operation queries.
        allowed_roots = (
            exp.Select,
            exp.Union,
            exp.Intersect,
            exp.Except,
        )

        if not isinstance(parsed_query, allowed_roots):
            return False, "Only SELECT queries are allowed."

        # Check the complete SQL tree, including nested queries and CTEs.
        for node in parsed_query.walk():
            if node.key.lower() in BLOCKED_NODES:
                return False, f"Blocked SQL operation detected: {node.key}"

        return True, "SQL query passed validation."

    except Exception as e:
        return False, f"SQL parsing or validation failed: {str(e)}"