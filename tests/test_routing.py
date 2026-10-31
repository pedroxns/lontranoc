from __future__ import annotations

from otterpilot.routing.context_router import STREAM_ROUTES, route_context
from otterpilot.routing.entity_parser import parse_entities
from otterpilot.routing.query_context import build_query_context
from otterpilot.routing.time_parser import parse_time_window


def test_routes_are_packaged():
    assert isinstance(STREAM_ROUTES, dict) and STREAM_ROUTES


def test_vehicle_routes():
    assert build_query_context("Quantos km posso rodar?")["query_name"] == "fuel"

    stream, query_name, sql, score = route_context("Algum pneu precisa calibrar?")
    assert (stream, query_name) == ("vehicle", "tires")
    assert sql and score > 0


def test_parsers():
    assert isinstance(parse_time_window("o que houve hoje?"), dict)
    assert isinstance(parse_entities("algum cachorro apareceu hoje?"), dict)
