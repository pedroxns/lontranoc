from datetime import datetime, timezone

import requests

from otterpilot.core.config import get_env
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_url(host, port, https):
    scheme = "https" if str(https).lower() == "true" else "http"
    return f"{scheme}://{host}:{port}"


def get_instances():
    instances = []

    for n in [1, 2]:
        name = get_env(f"ADGUARD{n}_NAME")
        host = get_env(f"ADGUARD{n}_HOST")
        port = get_env(f"ADGUARD{n}_PORT", "80")
        https = get_env(f"ADGUARD{n}_HTTPS", "false")
        user = get_env(f"ADGUARD{n}_USER")
        password = get_env(f"ADGUARD{n}_PASS")

        if name and host and user and password:
            instances.append(
                {
                    "name": name,
                    "host": host,
                    "port": port,
                    "https": https,
                    "url": build_url(host, port, https),
                    "user": user,
                    "password": password,
                }
            )

    return instances


def fetch_json(instance, path):
    response = requests.get(
        f"{instance['url']}{path}",
        auth=(instance["user"], instance["password"]),
        timeout=10,
    )
    response.raise_for_status()

    return response.json()


def health_score(
    running,
    protection_enabled,
    blocked_percent,
    querylog_error_count,
):
    score = 100

    if not running:
        score -= 70

    if not protection_enabled:
        score -= 30

    if querylog_error_count >= 10:
        score -= 20
    elif querylog_error_count >= 3:
        score -= 10

    if blocked_percent is None:
        score -= 5

    return max(score, 0)


def classify_health(score):
    if score >= 90:
        return "healthy"

    if score >= 70:
        return "warning"

    if score >= 40:
        return "degraded"

    return "critical"


def severity_for_health(health):
    if health == "healthy":
        return "info"

    if health == "warning":
        return "warning"

    if health == "degraded":
        return "error"

    return "critical"


def collect_instance(instance):
    status = fetch_json(
        instance,
        "/control/status",
    )

    stats = fetch_json(
        instance,
        "/control/stats",
    )

    try:
        querylog = fetch_json(
            instance,
            "/control/querylog?limit=50",
        )
        querylog_items = querylog.get("data", [])

    except Exception:
        querylog_items = []

    running = status.get("running")
    protection_enabled = status.get("protection_enabled")

    num_dns_queries = stats.get("num_dns_queries")
    num_blocked_filtering = stats.get("num_blocked_filtering")

    blocked_percent = None

    if num_dns_queries:
        blocked_percent = round(
            (num_blocked_filtering or 0)
            / num_dns_queries
            * 100,
            2,
        )

    error_count = 0
    top_error_domains = []

    for item in querylog_items:
        status_text = str(
            item.get("status", "")
        ).lower()

        answer = str(
            item.get("answer", "")
        ).lower()

        if (
            "servfail" in status_text
            or "nxdomain" in status_text
            or "error" in answer
        ):
            error_count += 1

            domain = (
                item.get("question", {})
                .get("name")
            )

            if domain:
                top_error_domains.append(domain)

    score = health_score(
        running=running,
        protection_enabled=protection_enabled,
        blocked_percent=blocked_percent,
        querylog_error_count=error_count,
    )

    health = classify_health(score)

    return EventEnvelope(
        capability="dns",
        connector="adguard",
        event_type="snapshot",
        resource_id=instance["name"],
        severity=severity_for_health(health),
        status=health,
        message=(
            f"AdGuard snapshot: "
            f"{instance['name']}"
        ),
        payload={
            "instance": instance["name"],
            "node": instance["name"],
            "host": instance["host"],
            "port": instance["port"],

            "running": running,
            "protection_enabled": (
                protection_enabled
            ),

            "version": status.get("version"),
            "language": status.get("language"),

            "dns_addresses": status.get(
                "dns_addresses"
            ),
            "dns_port": status.get("dns_port"),
            "http_port": status.get("http_port"),

            "num_dns_queries": (
                num_dns_queries
            ),
            "num_blocked_filtering": (
                num_blocked_filtering
            ),
            "blocked_percent": (
                blocked_percent
            ),

            "num_replaced_safebrowsing": (
                stats.get(
                    "num_replaced_safebrowsing"
                )
            ),
            "num_replaced_safesearch": (
                stats.get(
                    "num_replaced_safesearch"
                )
            ),
            "num_replaced_parental": (
                stats.get(
                    "num_replaced_parental"
                )
            ),

            "querylog_error_count": (
                error_count
            ),
            "querylog_error_domains": (
                top_error_domains[:10]
            ),

            "health_score": score,
            "health_status": health,
        },
    )


def build_error_event(instance, error):
    return EventEnvelope(
        capability="dns",
        connector="adguard",
        event_type="status_error",
        resource_id=instance.get("name"),
        severity="error",
        status="error",
        message=(
            "Erro ao consultar AdGuard: "
            f"{instance.get('name')}"
        ),
        payload={
            "instance": instance.get("name"),
            "node": instance.get("name"),
            "host": instance.get("host"),
            "port": instance.get("port"),
            "error": str(error),
        },
    )


def publish_event(bus, event):
    bus.publish(event)


def main():
    bus = build_default_event_bus()

    for instance in get_instances():
        try:
            print(
                f"Coletando {instance['name']} "
                f"em {instance['url']}",
                flush=True,
            )

            event = collect_instance(instance)

            print(
                "Enviando AdGuard:",
                instance["name"],
                event.payload.get(
                    "num_dns_queries"
                ),
                event.payload.get(
                    "num_blocked_filtering"
                ),
                event.payload.get(
                    "blocked_percent"
                ),
                flush=True,
            )

            publish_event(
                bus,
                event,
            )

        except Exception as error:
            print(
                f"ERRO AdGuard "
                f"{instance.get('name')}: "
                f"{error}",
                flush=True,
            )

            error_event = build_error_event(
                instance,
                error,
            )

            publish_event(
                bus,
                error_event,
            )


if __name__ == "__main__":
    main()