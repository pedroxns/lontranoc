import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from openobserve_ingest import emit

load_dotenv("/opt/lontranoc/.env")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_url(host, port, https):
    scheme = "https" if str(https).lower() == "true" else "http"
    return f"{scheme}://{host}:{port}"


def get_instances():
    instances = []

    for n in [1, 2]:
        name = os.getenv(f"ADGUARD{n}_NAME")
        host = os.getenv(f"ADGUARD{n}_HOST")
        port = os.getenv(f"ADGUARD{n}_PORT", "80")
        https = os.getenv(f"ADGUARD{n}_HTTPS", "false")
        user = os.getenv(f"ADGUARD{n}_USER")
        password = os.getenv(f"ADGUARD{n}_PASS")

        if name and host and user and password:
            instances.append({
                "name": name,
                "host": host,
                "port": port,
                "https": https,
                "url": build_url(host, port, https),
                "user": user,
                "password": password,
            })

    return instances


def fetch_json(instance, path):
    response = requests.get(
        f"{instance['url']}{path}",
        auth=(instance["user"], instance["password"]),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def health_score(running, protection_enabled, blocked_percent, querylog_error_count):
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


def collect_instance(instance):
    status = fetch_json(instance, "/control/status")
    stats = fetch_json(instance, "/control/stats")

    try:
        querylog = fetch_json(instance, "/control/querylog?limit=50")
        querylog_items = querylog.get("data", [])
    except Exception:
        querylog_items = []

    running = status.get("running")
    protection_enabled = status.get("protection_enabled")

    num_dns_queries = stats.get("num_dns_queries")
    num_blocked_filtering = stats.get("num_blocked_filtering")

    blocked_percent = None
    if num_dns_queries:
        blocked_percent = round((num_blocked_filtering or 0) / num_dns_queries * 100, 2)

    error_count = 0
    top_error_domains = []

    for item in querylog_items:
        status_text = str(item.get("status", "")).lower()
        answer = str(item.get("answer", "")).lower()

        if "servfail" in status_text or "nxdomain" in status_text or "error" in answer:
            error_count += 1
            domain = item.get("question", {}).get("name")
            if domain:
                top_error_domains.append(domain)

    score = health_score(
        running=running,
        protection_enabled=protection_enabled,
        blocked_percent=blocked_percent,
        querylog_error_count=error_count,
    )

    health = classify_health(score)

    print("Enviando AdGuard:", instance["name"], num_dns_queries, num_blocked_filtering, blocked_percent, flush=True)

    emit(
        stream="adguard",
        service="adguard",
        component="dns",
        event_type="status_snapshot",
        severity="info" if health in ["healthy", "warning"] else "error",
        status=health,
        message=f"AdGuard status snapshot: {instance['name']}",
        timestamp=now_iso(),
        schema_version="1.0",

        instance=instance["name"],
        node=instance["name"],
        host=instance["host"],
        port=instance["port"],

        running=running,
        protection_enabled=protection_enabled,
        version=status.get("version"),
        language=status.get("language"),
        dns_addresses=status.get("dns_addresses"),
        dns_port=status.get("dns_port"),
        http_port=status.get("http_port"),

        num_dns_queries=num_dns_queries,
        num_blocked_filtering=num_blocked_filtering,
        blocked_percent=blocked_percent,

        num_replaced_safebrowsing=stats.get("num_replaced_safebrowsing"),
        num_replaced_safesearch=stats.get("num_replaced_safesearch"),
        num_replaced_parental=stats.get("num_replaced_parental"),

        querylog_error_count=error_count,
        querylog_error_domains=top_error_domains[:10],

        health_score=score,
        health_status=health,

#        top_queried_domains=stats.get("top_queried_domains"),
#        top_blocked_domains=stats.get("top_blocked_domains"),
#        top_clients=stats.get("top_clients"),
    )


def main():
    for instance in get_instances():
        try:
            print(f"Coletando {instance['name']} em {instance['url']}", flush=True)
            collect_instance(instance)
        except Exception as error:
            print(f"ERRO AdGuard {instance.get('name')}: {error}", flush=True)
            emit(
                stream="adguard",
                service="adguard",
                component="dns",
                event_type="status_error",
                severity="error",
                status="error",
                message=f"Erro ao consultar AdGuard: {instance.get('name')}",
                timestamp=now_iso(),
                schema_version="1.0",
                instance=instance.get("name"),
                node=instance.get("name"),
                host=instance.get("host"),
                port=instance.get("port"),
                error=str(error),
            )
    

if __name__ == "__main__":
    main()