import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv("/opt/lontranoc/.env")

GRAYLOG_URL = os.getenv("GRAYLOG_URL")
GRAYLOG_TOKEN = os.getenv("GRAYLOG_TOKEN")

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")

def local_timestamp(ts):
    if not ts:
        return ts

    dt = datetime.fromisoformat(
        ts.replace("Z", "+00:00")
    )

    return dt.astimezone(LOCAL_TZ).strftime(
        "%d/%m/%Y %H:%M:%S"
    )

def search_graylog(query="*", minutes=60, limit=10):
    url = f"{GRAYLOG_URL}/api/search/universal/relative"

    params = {
        "query": query,
        "range": minutes * 60,
        "limit": limit,
        "sort": "timestamp:desc",
    }

    response = requests.get(
        url,
        params=params,
        auth=(GRAYLOG_TOKEN, "token"),
        headers={
            "Accept": "application/json",
            "X-Requested-By": "lontranoc",
        },
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    events = []

    for item in data.get("messages", []):
        msg = item.get("message", {})
        events.append({
            "timestamp": local_timestamp(msg.get("timestamp")),
            "source": msg.get("source"),
            "message": msg.get("message"),

            "service": msg.get("service"),
            "component": msg.get("component"),
            "status": msg.get("status"),
            "summary": msg.get("summary"),

            "stream": msg.get("gl2_source_input"),
            "facility": msg.get("facility"),
            "level": msg.get("level"),
            "program": msg.get("program"),
            "application_name": msg.get("application_name"),
            "container_name": msg.get("container_name"),

            "gpu_temp": msg.get("gpu_temp"),
            "gpu_util": msg.get("gpu_util"),
            "gpu_mem_percent": msg.get("gpu_mem_percent"),
            "latency_ms": msg.get("latency_ms"),
            "rack_temp": msg.get("rack_temp"),
            "ups_battery": msg.get("ups_battery"),
            "frigate": msg.get("frigate"),
        })

    return events

GRAYLOG_QUERIES = {
    "ia": 'service:ollama OR service:lontranoc OR message:ollama OR source:ollama',
    "infra": 'service:homelab',
    "zigbee": 'zigbee2mqtt OR z2m OR source:z2m-1 OR source:z2m-2',
    "frigate": 'frigate OR source:frigate',
    "rede": 'omada OR adguard OR dns OR wifi OR lan',
    "geral": 'service:ollama OR service:homelab OR service:lontranoc OR frigate OR omada OR adguard OR dns',
    "mqtt": 'mqtt OR emqx OR',
    "investigacao": 'service:ollama OR service:homelab OR zigbee2mqtt OR z2m OR frigate OR omada OR emqx'
}


def query_for_question(question: str) -> str:
    q = question.lower()

    if "zigbee" in q or "z2m" in q or "sensor" in q or "dispositivo zigbee" in q:
        return GRAYLOG_QUERIES["zigbee"]

    if "frigate" in q or "camera" in q or "câmera" in q or "cameras" in q or "câmeras" in q:
        return GRAYLOG_QUERIES["frigate"]

    if "omada" in q or "rede" in q or "wifi" in q or "wi-fi" in q or "lan" in q or "dns" in q or "adguard" in q or "internet" in q:
        return GRAYLOG_QUERIES["rede"]

    if "mqtt" in q or "emqx" in q:
        return GRAYLOG_QUERIES["mqtt"]

    if "ollama" in q or "gpu" in q or "ia" in q or "lontranoc" in q:
        return GRAYLOG_QUERIES["ia"]

    if "rack" in q or "nobreak" in q or "ups" in q or "energia" in q or "fase" in q or "bateria" in q:
        return GRAYLOG_QUERIES["infra"]

    if "investigue" in q or "diagnostico" in q or "diagnosticar" in q or "analise" in q or "o que aconteceu" in q or "algo estranho" in q or "deu ruim" in q:
       return GRAYLOG_QUERIES["investigacao"]

    return GRAYLOG_QUERIES["geral"]
