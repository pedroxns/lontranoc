from context_router import route_context
from time_parser import parse_time_window
from entity_parser import parse_entities


def build_query_context(question: str):
    stream, query_name, sql, route_score = route_context(question)
    time_ctx = parse_time_window(question)
    entity_ctx = parse_entities(question)

    return {
        "question": question,
        "stream": stream,
        "query_name": query_name,
        "sql": sql,
        "route_score": route_score,
        "time": time_ctx,
        "limit": 50,
        "filters": entity_ctx["filters"],
        "entities": entity_ctx["entities"],
        "valid": bool(stream and sql),
    }
