from collections import Counter, defaultdict
from datetime import datetime, timezone
from analysis_vehicle import analyze_vehicle


def extract_camera(row: dict) -> str:
    if row.get("camera") and row.get("camera") not in ["ffmpeg", "Unable"]:
        return row.get("camera")

    msg = row.get("message", "")

    # formatos comuns:
    # watchdog.Olho
    # ffmpeg.Olho.detect
    # frigate.video ERROR : Olho:
    import re

    patterns = [
        r"watchdog\.(?P<camera>[A-Za-z0-9_-]+)",
        r"ffmpeg\.(?P<camera>[A-Za-z0-9_-]+)\.",
        r":\s+(?P<camera>[A-Za-z0-9_-]+):\s+",
        r"stream=(?P<camera>[A-Za-z0-9_-]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, msg)
        if m:
            return m.group("camera")

    return row.get("camera") or "unknown"


def normalize_event(row: dict) -> dict:
    service = row.get("service") or "unknown"
    event_type = row.get("event_type", "log")
    severity = row.get("severity", "info")

    if service == "unknown":
        if row.get("camera") or row.get("subsystem") in ["rtsp", "ffmpeg", "watchdog"]:
            service = "frigate"
        elif row.get("ha_component"):
            service = "homeassistant"
        elif row.get("ap_from") or row.get("ap_to") or row.get("ssid"):
            service = "omada"
        elif row.get("instance") in ["z2m1", "z2m2"]:
            service = "zigbee"

    camera = extract_camera(row)

    entity = (
        camera
        or row.get("client_name")
        or row.get("device")
        or row.get("host")
        or row.get("node")
        or "unknown"
    )

    category = "general"

    if service == "frigate" or row.get("camera"):
        category = "camera"
    elif service == "omada" or event_type in ["roaming", "dhcp_allocated"]:
        category = "network"
    elif service == "zigbee":
        category = "zigbee"
    elif service == "proxmox":
        category = "infra"

    return {
        "timestamp": row.get("_timestamp"),
        "service": service,
        "event_type": event_type,
        "severity": severity,
        "entity": entity,
        "category": category,
        "message": row.get("message", ""),
        "raw": row,
    }


def normalize_events(rows: list[dict]) -> list[dict]:
    return [normalize_event(row) for row in rows]


def build_statistics(events: list[dict]) -> dict:
    return {
        "total_events": len(events),
        "by_service": dict(Counter(e["service"] for e in events)),
        "by_category": dict(Counter(e["category"] for e in events)),
        "by_severity": dict(Counter(e["severity"] for e in events)),
        "by_event_type": dict(Counter(e["event_type"] for e in events)),
        "by_entity": dict(Counter(e["entity"] for e in events)),
    }


def group_events(events: list[dict]) -> list[dict]:
    groups = defaultdict(list)

    for event in events:
        key = (
            event["service"],
            event["category"],
            event["entity"],
        )
        groups[key].append(event)

    clusters = []

    for (service, category, entity), items in groups.items():
        timestamps = [e["timestamp"] for e in items if e.get("timestamp")]

        clusters.append({
            "service": service,
            "category": category,
            "entity": entity,
            "count": len(items),
            "start_ts": min(timestamps) if timestamps else None,
            "end_ts": max(timestamps) if timestamps else None,
            "event_types": dict(Counter(e["event_type"] for e in items)),
            "severities": dict(Counter(e["severity"] for e in items)),
            "events": items,
        })

    return sorted(clusters, key=lambda c: c["count"], reverse=True)


def classify_incident(cluster: dict) -> dict:
    event_types = cluster["event_types"]
    entity = cluster["entity"]
    category = cluster["category"]

    title = "Atividade relevante"
    probable_causes = []
    confidence = 0.5
    severity = "info"

    if category == "camera":
        if any(k in event_types for k in [
            "camera_unreachable",
            "camera_timeout",
            "rtsp_not_found",
            "ffmpeg_crash",
            "camera_capture_failed",
        ]):
            title = "Falha de conectividade/captura da câmera"
            probable_causes = [
                "câmera indisponível",
                "rota/rede até a câmera com problema",
                "stream RTSP inválido ou indisponível",
                "go2rtc/ffmpeg reiniciando por falha de entrada",
            ]
            confidence = 0.92
            severity = "error"

        if "ffmpeg_restart" in event_types:
            probable_causes.append("watchdog reiniciando ffmpeg repetidamente")
            confidence = max(confidence, 0.88)
            if severity == "info":
                severity = "warning"

    elif category == "network":
        if "roaming" in event_types:
            title = "Roaming Wi-Fi detectado"
            probable_causes = [
                "cliente migrando entre APs",
                "ajuste de sinal/cobertura",
                "balanceamento ou movimentação física",
            ]
            confidence = 0.85
            severity = "info"

    elif category == "zigbee":
        if any(k in event_types for k in ["device_offline", "interview_failed", "mqtt_error"]):
            title = "Instabilidade Zigbee"
            probable_causes = [
                "dispositivo fora de alcance",
                "falha de pareamento/interview",
                "instabilidade no broker MQTT ou coordenador",
            ]
            confidence = 0.82
            severity = "warning"

    elif category == "infra":
        if any(k in event_types for k in ["cluster_quorum", "node_offline", "io_error", "zfs"]):
            title = "Evento relevante de infraestrutura"
            probable_causes = [
                "alteração de estado do cluster",
                "evento de storage",
                "possível degradação de nó ou disco",
            ]
            confidence = 0.8
            severity = "warning"

    return {
        "title": title,
        "service": cluster["service"],
        "category": category,
        "entity": entity,
        "severity": severity,
        "confidence": confidence,
        "event_count": cluster["count"],
        "start_ts": cluster["start_ts"],
        "end_ts": cluster["end_ts"],
        "event_types": cluster["event_types"],
        "probable_causes": list(dict.fromkeys(probable_causes)),
    }


def build_incidents(clusters: list[dict]) -> list[dict]:
    incidents = []

    for cluster in clusters:
        incident = classify_incident(cluster)

        if incident["event_count"] > 1 or incident["severity"] in ["warning", "error", "critical"]:
            incidents.append(incident)

    return incidents


def analyze_search_result(search_result: dict) -> dict:
    rows = search_result.get("rows", [])
    ctx = search_result.get("context", {})
    if ctx.get("stream") == "vehicle":
        vehicle_analysis = analyze_vehicle(search_result)
        return {
            "context": {
                "question": ctx.get("question"),
                "stream": ctx.get("stream"),
                "query_name": ctx.get("query_name"),
                "time": ctx.get("time", {}),
            },
            "statistics": {
                "total_events": len(search_result.get("rows", [])),
            },
            "incidents": [],
            "vehicle": vehicle_analysis,
            "sample_events": search_result.get("rows", [])[:3],
        }

    events = normalize_events(rows)
    statistics = build_statistics(events)
    clusters = group_events(events)
    incidents = build_incidents(clusters)

    def serialize_time_context(time_ctx: dict) -> dict:
        clean = {}

        for key, value in time_ctx.items():
            if isinstance(value, datetime):
                clean[key] = value.isoformat()
            else:
                clean[key] = value

        return clean
    
    return {
        "context": {
            "question": ctx.get("question"),
            "stream": ctx.get("stream"),
            "query_name": ctx.get("query_name"),
            "time": serialize_time_context(ctx.get("time", {})),
        },
        "statistics": statistics,
        "incidents": incidents,
        "clusters": [
            {
                "service": c["service"],
                "category": c["category"],
                "entity": c["entity"],
                "count": c["count"],
                "event_types": c["event_types"],
                "severities": c["severities"],
                "start_ts": c["start_ts"],
                "end_ts": c["end_ts"],
            }
            for c in clusters[:10]
        ],
        "sample_events": rows[:5],
    }