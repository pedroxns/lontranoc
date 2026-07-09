from openobserve_search import search_logs
from query_context import build_query_context

def apply_filters(sql: str, filters: dict) -> str:
    if not filters:
        return sql

    extra_conditions = []

    if "label" in filters:
        extra_conditions.append(f"lower(label) = '{filters['label'].lower()}'")

    if "camera" in filters:
        extra_conditions.append(f"camera = '{filters['camera']}'")

    if not extra_conditions:
        return sql

    condition_sql = " AND " + " AND ".join(extra_conditions)

    if "WHERE" in sql.upper():
        return sql.replace("ORDER BY", condition_sql + "\nORDER BY")

    return sql.replace("ORDER BY", "WHERE " + " AND ".join(extra_conditions) + "\nORDER BY")

def search_context(question: str):
    ctx = build_query_context(question)

    if not ctx["valid"]:
        return {
            "valid": False,
            "context": ctx,
            "rows": [],
            "error": None,
        }

    time_ctx = ctx["time"]

    try:
        sql = apply_filters(ctx["sql"], ctx.get("filters", {}))
        rows = search_logs(
        sql,
            ctx["sql"],
            start_time=time_ctx["start_time"],
            end_time=time_ctx["end_time"],
            size=ctx["limit"],
        )

        return {
            "valid": True,
            "context": ctx,
            "rows": rows,
            "error": None,
            "sql": sql,
        }

    except Exception as error:
        return {
            "valid": False,
            "context": ctx,
            "rows": [],
            "error": str(error),
        }


def build_search_summary(result: dict):
    ctx = result["context"]
    time_ctx = ctx["time"]

    return {
        "stream": ctx["stream"],
        "query_name": ctx["query_name"],
        "route_score": ctx["route_score"],
        "time_label": time_ctx["label"],
        "time_expression": time_ctx["expression"],
        "time_confidence": time_ctx["confidence"],
        "time_granularity": time_ctx["time_granularity"],
        "result_count": len(result["rows"]),
        "valid": result["valid"],
        "error": result["error"],
    }
