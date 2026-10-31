from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt

from otterpilot.core.config import NotConfiguredError, get_env, get_int, watch_config
from otterpilot.state import build_default_state_store

# Intervalo mínimo entre registros de "mensagem recebida" no State Store.
HEARTBEAT_SECONDS = 60
RECONNECT_SECONDS = 10


@dataclass(frozen=True, slots=True)
class MQTTSettings:
    host: str
    port: int
    username: str | None
    password: str | None


def load_settings() -> MQTTSettings:
    host = get_env("MQTT_HOST")

    if not host:
        raise NotConfiguredError("Broker MQTT não configurado (MQTT_HOST)")

    return MQTTSettings(
        host=host,
        port=get_int("MQTT_PORT", 1883),
        username=get_env("MQTT_USERNAME"),
        password=get_env("MQTT_PASSWORD"),
    )


def build_client(settings: MQTTSettings) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if settings.username:
        client.username_pw_set(settings.username, settings.password)

    return client


class _ComponentReporter:
    def __init__(self, component: str) -> None:
        self.component = component
        self._store = build_default_state_store()
        self._last_heartbeat = 0.0

    def report(self, status: str, detail: str | None = None) -> None:
        try:
            self._store.report_component(self.component, status, detail=detail)
        except Exception as error:
            print(f"[{self.component}] Falha ao registrar status: {error}", flush=True)

    def heartbeat(self) -> None:
        now = time.monotonic()

        if now - self._last_heartbeat < HEARTBEAT_SECONDS:
            return

        self._last_heartbeat = now

        try:
            self._store.report_component(
                self.component,
                "connected",
                message_seen=True,
            )
        except Exception:
            pass


def _wait_for_configuration(reporter: _ComponentReporter, reason: str) -> None:
    reporter.report("not_configured", reason)
    print(f"[{reporter.component}] Aguardando configuração: {reason}", flush=True)

    # watch_config() reinicia o processo quando a configuração mudar.
    while True:
        time.sleep(3600)


def run_subscriber(
    component: str,
    topics: Callable[[], Iterable[tuple[str, int]]],
    handle_message: Callable[[mqtt.Client, Any], None],
) -> None:
    """Mantém um assinante MQTT conectado para sempre."""

    watch_config()
    reporter = _ComponentReporter(component)

    try:
        settings = load_settings()
        subscriptions = list(topics())
    except NotConfiguredError as error:
        _wait_for_configuration(reporter, str(error))
        return

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            reporter.report("error", f"Conexão recusada: {reason_code}")
            print(f"[{component}] Conexão MQTT recusada: {reason_code}", flush=True)
            return

        for topic, qos in subscriptions:
            client.subscribe(topic, qos=qos)

        reporter.report("connected", f"{settings.host}:{settings.port}")
        print(
            f"[{component}] Conectado a {settings.host}:{settings.port} "
            f"({len(subscriptions)} tópicos).",
            flush=True,
        )

    def on_disconnect(client, userdata, flags, reason_code, properties):
        reporter.report("disconnected", str(reason_code))
        print(f"[{component}] Desconectado do MQTT: {reason_code}", flush=True)

    def on_message(client, userdata, msg):
        reporter.heartbeat()

        try:
            handle_message(client, msg)
        except Exception as error:
            print(f"[{component}] Erro ao processar {msg.topic}: {error}", flush=True)

    while True:
        client = build_client(settings)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        try:
            client.connect(settings.host, settings.port, 60)
            client.loop_forever(retry_first_connection=True)
        except Exception as error:
            reporter.report("error", str(error))
            print(
                f"[{component}] Erro MQTT: {error}. "
                f"Nova tentativa em {RECONNECT_SECONDS}s.",
                flush=True,
            )
            time.sleep(RECONNECT_SECONDS)
