import re
from pathlib import Path

import yaml


ROUTES_FILE = Path("/opt/lontranoc/config/routes.yaml")


GENERAL_HISTORY_KEYWORDS = {
    "hoje": 2,
    "ontem": 2,
    "últimas": 2,
    "ultimas": 2,
    "horas": 2,
    "histórico": 3,
    "historico": 3,
    "aconteceu": 3,
    "erro": 4,
    "falha": 4,
    "lento": 3,
    "lenta": 3,
    "lentidão": 3,
    "lentidao": 3,
    "dias": 3,
    "meses": 4,
}


def load_routes() -> dict:
    with ROUTES_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError("routes.yaml precisa conter um dicionário no topo")

    return data


STREAM_ROUTES = load_routes()


def keyword_matches(question: str, keyword: str) -> bool:
    q = question.lower()
    k = keyword.lower()

    if len(k) <= 3:
        return re.search(rf"\b{re.escape(k)}\b", q) is not None

    return k in q


def score_keywords(question: str, keywords: dict[str, int]) -> int:
    if not keywords:
        return 0

    return sum(
        weight
        for keyword, weight in keywords.items()
        if keyword_matches(question, keyword)
    )


def select_query(question: str, route: dict):
    best_name = "default"
    best_score = 0

    for query_name, query in route.get("queries", {}).items():
        if query_name == "default":
            continue

        score = score_keywords(question, query.get("keywords", {}))

        if score > best_score:
            best_score = score
            best_name = query_name

    queries = route.get("queries", {})

    if best_name not in queries:
        return None, None

    return best_name, queries[best_name].get("sql")


def route_context(question: str):
    q = question.lower()

    general_score = score_keywords(q, GENERAL_HISTORY_KEYWORDS)

    best_stream = None
    best_score = 0

    for stream, route in STREAM_ROUTES.items():
        score = score_keywords(q, route.get("keywords", {}))

        if score > best_score:
            best_score = score
            best_stream = stream

    if best_stream:
        query_name, sql = select_query(q, STREAM_ROUTES[best_stream])
        return best_stream, query_name, sql, best_score

    if general_score > 0:
        return "lontranoc", "default", """
        SELECT event_type, question, answer, duration_ms, status, message, timestamp
        FROM lontranoc
        ORDER BY _timestamp DESC
        LIMIT 30
        """, general_score

    return None, None, None, 0
