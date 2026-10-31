#!/usr/bin/env bash
set -euo pipefail

OLLAMA_URL="http://127.0.0.1:11434"
MODEL="qwen3.5:9b"

MQTT_HOST="192.168.20.10"
MQTT_PORT="1883"
MQTT_TOPIC="homelab/ollama/latency"

START=$(date +%s%3N)

if ! curl -fsS --max-time 120 \
  "$OLLAMA_URL/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5:9b",
    "prompt": "Responda apenas OK.",
    "think": false,
    "stream": false,
    "keep_alive": -1,
    "options": {
      "num_predict": 16
    }
  }' > /dev/null; then

  echo "ERRO: Falha na consulta ao Ollama." >&2
  exit 1
fi

END=$(date +%s%3N)
LATENCY=$((END - START))

mosquitto_pub \
  -h "$MQTT_HOST" \
  -p "$MQTT_PORT" \
  -t "$MQTT_TOPIC" \
  -m "$LATENCY"

echo "Latência publicada: ${LATENCY} ms"
