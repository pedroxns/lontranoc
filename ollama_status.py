import json
import os
import time
import subprocess
from datetime import datetime, timezone
from openobserve_ingest import emit

import requests
from dotenv import load_dotenv
import paho.mqtt.client as mqtt


load_dotenv("/opt/lontranoc/.env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "").strip()
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "").strip()
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "homelab/ollama/status")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_loaded_model_info():
    try:
        response = requests.get(
            f"{OLLAMA_URL}/api/ps",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        models = data.get("models", [])
        if not models:
            return {
                "loaded": False,
                "model": None,
                "expires_at": None,
                "size_vram_bytes": 0,
                "size_vram_gb": 0,
            }

        selected = None
        for model in models:
            if model.get("name") == OLLAMA_MODEL or model.get("model") == OLLAMA_MODEL:
                selected = model
                break

        if selected is None:
            selected = models[0]

        size_vram = selected.get("size_vram") or 0

        return {
            "loaded": True,
            "model": selected.get("name") or selected.get("model"),
            "expires_at": selected.get("expires_at"),
            "size_vram_bytes": size_vram,
            "size_vram_gb": round(size_vram / 1024 / 1024 / 1024, 2),
        }

    except Exception as error:
        return {
            "loaded": False,
            "model": None,
            "expires_at": None,
            "size_vram_bytes": 0,
            "size_vram_gb": 0,
            "error": f"api_ps_failed: {error}",
        }


def measure_latency():
    start = time.perf_counter()

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": "responda apenas ok",
                "stream": False,
                "keep_alive": "24h",
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        latency_ms = round((time.perf_counter() - start) * 1000)

        return {
            "latency_ms": latency_ms,
            "ok": True,
            "response": data.get("response", "").strip(),
            "total_duration_ns": data.get("total_duration"),
            "load_duration_ns": data.get("load_duration"),
            "prompt_eval_duration_ns": data.get("prompt_eval_duration"),
            "eval_duration_ns": data.get("eval_duration"),
        }

    except Exception as error:
        latency_ms = round((time.perf_counter() - start) * 1000)

        return {
            "latency_ms": latency_ms,
            "ok": False,
            "response": None,
            "error": f"generate_failed: {error}",
        }


def publish_mqtt(payload):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    result = client.publish(
        MQTT_TOPIC,
        json.dumps(payload, ensure_ascii=False),
        qos=1,
        retain=True,
    )

    result.wait_for_publish(timeout=10)

    if not result.is_published():
        raise RuntimeError("Falha ao publicar mensagem MQTT")

    client.loop_stop()
    client.disconnect()

def build_summary(payload):
    if not payload.get("gpu_available"):
        return "Atenção: GPU indisponível para o Ollama."

    if not payload.get("loaded"):
        return "Atenção: modelo do Ollama não está carregado."

    if payload.get("gpu_temp", 0) >= 80:
        return f"Atenção: GPU quente, {payload['gpu_temp']}°C."

    if payload.get("latency_ms", 99999) > 7000:
        return f"Atenção: Ollama lento, latência de {payload['latency_ms']} ms."

    return (
        f"Ollama operacional. Modelo {payload.get('model')} carregado, "
        f"latência {payload.get('latency_ms')} ms, "
        f"GPU a {payload.get('gpu_temp')}°C e "
        f"VRAM em {payload.get('gpu_mem_percent')}%."
    )

def health_from_latency(latency_ms, ok):
    if not ok:
        return "Deu ruim!"
    if latency_ms < 1000:
        return "Boa garoto!"
    if latency_ms < 3000:
        return "Ta indo"
    if latency_ms < 7000:
        return "Fica esperto"
    return "Deu ruim"

def get_gpu_info():
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]

        output = subprocess.check_output(cmd, timeout=10).decode().strip()
        temp, util, mem_used, mem_total = [
            int(x.strip()) for x in output.split(",")
        ]

        return {
            "gpu_available": True,
            "gpu_temp": temp,
            "gpu_util": util,
            "gpu_mem_used_mb": mem_used,
            "gpu_mem_total_mb": mem_total,
            "gpu_mem_percent": round(mem_used / mem_total * 100, 1),
        }

    except Exception as error:
        return {
            "gpu_available": False,
            "gpu_error": str(error),
        }

def main():
    model_info = get_loaded_model_info()
    latency = measure_latency()
    gpu_info = get_gpu_info()

    payload = {
        "timestamp": now_iso(),
        "ollama_url": OLLAMA_URL,
        "target_model": OLLAMA_MODEL,
        "loaded": model_info.get("loaded", False),
        "model": model_info.get("model"),
        "expires_at": model_info.get("expires_at"),
        "size_vram_bytes": model_info.get("size_vram_bytes", 0),
        "size_vram_gb": model_info.get("size_vram_gb", 0),
        "gpu_available": gpu_info.get("gpu_available", False),
        "gpu_temp": gpu_info.get("gpu_temp"),
        "gpu_util": gpu_info.get("gpu_util"),
        "gpu_mem_used_mb": gpu_info.get("gpu_mem_used_mb"),
        "gpu_mem_total_mb": gpu_info.get("gpu_mem_total_mb"),
        "gpu_mem_percent": gpu_info.get("gpu_mem_percent"),
        "gpu_error": gpu_info.get("gpu_error"),
        "latency_ms": latency.get("latency_ms"),
        "latency_ok": latency.get("ok"),
        "health": health_from_latency(
            latency.get("latency_ms", 999999),
            latency.get("ok", False),
        ),
        "response": latency.get("response"),
    }
    if "error" in model_info:
        payload["model_error"] = model_info["error"]

    if "error" in latency:
        payload["latency_error"] = latency["error"]

    payload["summary"] = build_summary(payload)

    publish_mqtt(payload)

    emit(
        stream="ollama",
        service="ollama",
        component="telemetry",
        event_type="status_snapshot",
        severity="info",
        status=payload.get("health", "unknown"),
        message="Ollama status snapshot",
        schema_version="1.0",
        model=payload.get("model"),
        loaded=payload.get("loaded"),
        latency_ms=payload.get("latency_ms"),
        latency_ok=payload.get("latency_ok"),
        gpu_available=payload.get("gpu_available"),
        gpu_temp=payload.get("gpu_temp"),
        gpu_util=payload.get("gpu_util"),
        gpu_mem_used_mb=payload.get("gpu_mem_used_mb"),
        gpu_mem_total_mb=payload.get("gpu_mem_total_mb"),
        gpu_mem_percent=payload.get("gpu_mem_percent"),
        size_vram_gb=payload.get("size_vram_gb"),
        summary=payload.get("summary"),
    )

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
