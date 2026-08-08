from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from otterpilot.state import build_default_state_store


HEALTHY_STATUSES = {
    "healthy",
    "ok",
    "online",
}

WARNING_STATUSES = {
    "warning",
    "degraded",
}

CRITICAL_STATUSES = {
    "critical",
    "offline",
    "error",
    "failed",
}


CAPABILITY_IMPACT = {
    "host_health": "critical",
    "ups": "critical",
    "dns": "critical",
    "llm_runtime": "critical",

    "zigbee_health": "warning",
    "environment_health": "warning",
    "camera_health": "warning",

    "vehicle": "informational",
}


STALE_AFTER_SECONDS = {
    "host_health": 300,
    "ups": 300,
    "dns": 300,
    "llm_runtime": 300,
    "zigbee_health": 600,
    "environment_health": 300,
    "camera_health": 300,
    "vehicle": 1800,
}

NEUTRAL_STATUSES = {
    "stopped",
}


def _age_seconds(timestamp: str) -> float:
    observed = datetime.fromisoformat(timestamp)

    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    return max(
        0.0,
        (now - observed).total_seconds(),
    )


def _is_stale(state: dict[str, Any]) -> bool:
    capability = state["capability"]

    limit = STALE_AFTER_SECONDS.get(
        capability,
        300,
    )

    try:
        return _age_seconds(state["timestamp"]) > limit
    except (TypeError, ValueError):
        return True


def _problem_impact(
    state: dict[str, Any],
    *,
    stale: bool,
) -> str | None:
    capability = state["capability"]
    status = str(state.get("status", "")).lower()

    capability_impact = CAPABILITY_IMPACT.get(
        capability,
        "warning",
    )

    if capability_impact == "informational":
        return None

    if stale:
        return "warning"

    if status in HEALTHY_STATUSES:
        return None

    if status in WARNING_STATUSES:
        return "warning"

    if status in CRITICAL_STATUSES:
        return capability_impact

    if status in NEUTRAL_STATUSES:
        return None

    # Estado desconhecido não é tratado como saudável.
    return "warning"


def _build_problem(
    state: dict[str, Any],
    *,
    stale: bool,
) -> dict[str, Any] | None:
    impact = _problem_impact(
        state,
        stale=stale,
    )

    if impact is None:
        return None

    if stale:
        reason = "estado desatualizado"
    else:
        reason = (
            f"{state['capability']} em estado "
            f"{state.get('status', 'unknown')}"
        )

    return {
        "connector": state["connector"],
        "capability": state["capability"],
        "resource_id": state["resource_id"],
        "status": state.get("status", "unknown"),
        "impact": impact,
        "stale": stale,
        "reason": reason,
    }


def _overall_from_problems(
    problems: list[dict[str, Any]],
) -> tuple[str, str]:
    impacts = {
        problem["impact"]
        for problem in problems
    }

    if "critical" in impacts:
        return "critical", "critical"

    if "warning" in impacts:
        return "degraded", "warning"

    return "healthy", "info"


def _build_summary(
    *,
    overall_status: str,
    resource_count: int,
    problems: list[dict[str, Any]],
) -> str:
    if resource_count == 0:
        return "Nenhum recurso monitorado disponível."

    if not problems:
        return (
            f"Homelab operacional com "
            f"{resource_count} recursos monitorados."
        )

    critical = [
        problem
        for problem in problems
        if problem["impact"] == "critical"
    ]

    warnings = [
        problem
        for problem in problems
        if problem["impact"] == "warning"
    ]

    parts = []

    if critical:
        resources = ", ".join(
            problem["resource_id"]
            for problem in critical
        )

        parts.append(
            f"{len(critical)} problema(s) crítico(s): "
            f"{resources}"
        )

    if warnings:
        resources = ", ".join(
            problem["resource_id"]
            for problem in warnings
        )

        parts.append(
            f"{len(warnings)} alerta(s): "
            f"{resources}"
        )

    return (
        f"Homelab {overall_status}. "
        + "; ".join(parts)
        + "."
    )


def build_overview() -> dict[str, Any]:
    store = build_default_state_store()

    states = [
        state
        for state in store.list_all()
        if not (
            state["connector"] == "otterpilot"
            and state["capability"] == "system_health"
        )
    ]

    problems = []
    stale_count = 0

    by_status = Counter()
    by_capability = defaultdict(
        lambda: {
            "total": 0,
            "healthy": 0,
            "problem": 0,
            "stale": 0,
        }
    )

    for state in states:
        status = str(
            state.get("status", "unknown")
        ).lower()

        by_status[status] += 1

        capability = state["capability"]
        capability_stats = by_capability[capability]
        capability_stats["total"] += 1

        stale = _is_stale(state)

        if stale:
            stale_count += 1
            capability_stats["stale"] += 1

        problem = _build_problem(
            state,
            stale=stale,
        )

        if problem is None:
            capability_stats["healthy"] += 1
        else:
            capability_stats["problem"] += 1
            problems.append(problem)

    overall_status, severity = (
        _overall_from_problems(problems)
    )

    problems.sort(
        key=lambda item: (
            0 if item["impact"] == "critical" else 1,
            item["capability"],
            item["resource_id"],
        )
    )

    resource_count = len(states)

    return {
        "overall_status": overall_status,
        "severity": severity,
        "resource_count": resource_count,
        "healthy_count": (
            resource_count - len(problems)
        ),
        "problem_count": len(problems),
        "critical_count": sum(
            1
            for problem in problems
            if problem["impact"] == "critical"
        ),
        "warning_count": sum(
            1
            for problem in problems
            if problem["impact"] == "warning"
        ),
        "stale_count": stale_count,
        "by_status": dict(by_status),
        "by_capability": {
            capability: dict(stats)
            for capability, stats
            in sorted(by_capability.items())
        },
        "problems": problems,
        "summary": _build_summary(
            overall_status=overall_status,
            resource_count=resource_count,
            problems=problems,
        ),
    }
