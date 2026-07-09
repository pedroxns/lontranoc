import json
import os
import requests
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from dotenv import load_dotenv
from openobserve_ingest import emit

load_dotenv("/opt/lontranoc/.env")

HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")

IMPORTANT_ENTITIES = {
    "rack_temp": "sensor.clima_servidor_temperature",
    "ollama_status": "sensor.ollama_status_geral",
    "ollama_latency": "sensor.ollama_latencia",
    "gpu_temp": "sensor.ollama_gpu_temp_mqtt",
    "gpu_mem": "sensor.ollama_gpu_mem_percent_mqtt",
    "ups_status": "sensor.dnb_status",
    "ups_battery": "sensor.dnb_carga_da_bateria",
    "matx_cpu": "sensor.192_168_68_5_cpu_usage",
    "mitx_cpu": "sensor.192_168_68_200_cpu_usage",
    "mini_cpu": "sensor.192_168_68_100_cpu_usage",
    "z2m_1": "binary_sensor.zigbee2mqtt_bridge_connection_state_4",
    "z2m_2": "binary_sensor.zigbee2mqtt_bridge_connection_state_3",
    "frigate": "sensor.frigate_status"
}

headers = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

result = {}

for name, entity_id in IMPORTANT_ENTITIES.items():
    r = requests.get(
        f"{HA_URL}/api/states/{entity_id}",
        headers=headers,
        timeout=10,
    )

    if r.status_code == 200:
        result[name] = r.json()["state"]
    else:
        result[name] = "error"

def now_iso():
    return datetime.now(timezone.utc).isoformat()
def to_float(value, default=0):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def build_summary(entities):
    alerts = []

    rack_temp = to_float(entities.get("rack_temp"))
    ollama_status = entities.get("ollama_status")
    ollama_latency = to_float(entities.get("ollama_latency"))
    gpu_temp = to_float(entities.get("gpu_temp"))
    gpu_mem = to_float(entities.get("gpu_mem"))
    ups_status = str(entities.get("ups_status", "")).lower()
    ups_battery = to_float(entities.get("ups_battery"))
    frigate = str(entities.get("frigate", "")).lower()
    z2m_1 = entities.get("z2m_1")
    z2m_2 = entities.get("z2m_2")

    if rack_temp >= 45:
        alerts.append(f"rack quente ({rack_temp:.1f}°C)")

    if gpu_temp >= 80:
        alerts.append(f"GPU quente ({gpu_temp:.0f}°C)")

    if ollama_latency >= 7000:
        alerts.append(f"Ollama lento ({ollama_latency:.0f} ms)")

    if "operacional" not in str(ollama_status).lower():
        alerts.append(f"Ollama em estado {ollama_status}")

    if "ol" not in ups_status and "online" not in ups_status:
        alerts.append(f"nobreak em estado {entities.get('ups_status')}")

    if ups_battery <= 30:
        alerts.append(f"bateria do nobreak baixa ({ups_battery:.0f}%)")

    if z2m_1 != "on":
        alerts.append("Zigbee2MQTT 1 desconectado")

    if z2m_2 != "on":
        alerts.append("Zigbee2MQTT 2 desconectado")

    if frigate not in ["running", "ok", "online"]:
        alerts.append(f"Frigate em estado {entities.get('frigate')}")

    if alerts:
        return "Atenção: " + "; ".join(alerts) + "."

    return (
        f"Homelab operacional. Rack a {rack_temp:.1f}°C, "
        f"Ollama {ollama_status} com latência de {ollama_latency:.0f} ms, "
        f"GPU a {gpu_temp:.0f}°C usando {gpu_mem:.1f}% da memória, "
        f"nobreak online com {ups_battery:.0f}% de bateria, "
        f"Frigate e Zigbee2MQTT ativos."
    )

def publish_mqtt(payload):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(os.getenv("MQTT_HOST"), int(os.getenv("MQTT_PORT", "1883")), 60)
    client.loop_start()

    result = client.publish(
        os.getenv("MQTT_HOMELAB_TOPIC", "homelab/status/raw"),
        json.dumps(payload, ensure_ascii=False),
        qos=1,
        retain=True,
    )

    result.wait_for_publish(timeout=10)
    client.loop_stop()
    client.disconnect()

summary = build_summary(result)

numeric_entities = dict(result)

for key in [
    "rack_temp",
    "gpu_temp",
    "gpu_mem",
    "ollama_latency",
    "ups_battery",
    "matx_cpu",
    "mitx_cpu",
    "mini_cpu",
]:
    numeric_entities[key] = to_float(result.get(key))

payload = {
    "timestamp": now_iso(),
    "summary": summary,
    "entities": numeric_entities,
}

emit(
    stream="homelab",
    service="homelab",
    component="telemetry",
    event_type="status_snapshot",
    severity="info",
    status="ok",
    message="Homelab status snapshot",
    summary=payload.get("summary"),
    schema_version="1.0",
    **numeric_entities,
)

publish_mqtt(payload)

print(json.dumps(payload, indent=2, ensure_ascii=False))
