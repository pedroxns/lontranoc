#!/bin/bash

START=$(date +%s%3N)

curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen2.5:7b-instruct",
    "prompt":"ok",
    "stream":false
  }' > /dev/null

END=$(date +%s%3N)

LATENCY=$((END-START))

mosquitto_pub \
  -h 192.168.20.10 \
  -p 1883 \
  -t homelab/ollama/latency \
  -m "$LATENCY"
