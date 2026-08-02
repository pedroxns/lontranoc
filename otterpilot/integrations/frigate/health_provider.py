from __future__ import annotations

import requests

from otterpilot.core.config import get_env
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus


FRIGATE_URL = (
    get_env("FRIGATE_URL")
    or "http://192.168.10.30:5000"
).rstrip("/")


def fetch_stats() -> dict:
    response = requests.get(
        f"{FRIGATE_URL}/api/stats",
        timeout=10,
    )
    response.raise_for_status()

    return response.json()


def classify_camera_health(stats: dict) -> tuple[str, str]:
    camera_fps = stats.get("camera_fps") or 0
    process_fps = stats.get("process_fps") or 0
    skipped_fps = stats.get("skipped_fps") or 0

    capture_pid = stats.get("capture_pid")
    ffmpeg_pid = stats.get("ffmpeg_pid")

    if (
        camera_fps <= 0
        or process_fps <= 0
        or not capture_pid
        or not ffmpeg_pid
    ):
        return "offline", "critical"

    if skipped_fps > 1:
        return "degraded", "warning"

    return "healthy", "info"


def build_camera_event(
    camera: str,
    stats: dict,
) -> EventEnvelope:
    status, severity = classify_camera_health(stats)

    return EventEnvelope(
        capability="camera_health",
        connector="frigate",
        event_type="camera_health",
        resource_id=camera,
        severity=severity,
        status=status,
        message=f"Frigate camera health: {camera}",
        payload={
            "camera": camera,
            "camera_fps": stats.get("camera_fps"),
            "process_fps": stats.get("process_fps"),
            "skipped_fps": stats.get("skipped_fps"),
            "detection_fps": stats.get("detection_fps"),
            "detection_enabled": stats.get(
                "detection_enabled"
            ),
            "pid": stats.get("pid"),
            "capture_pid": stats.get("capture_pid"),
            "ffmpeg_pid": stats.get("ffmpeg_pid"),
            "audio_rms": stats.get("audio_rms"),
            "audio_dBFS": stats.get("audio_dBFS"),
        },
    )


def collect() -> list[EventEnvelope]:
    stats = fetch_stats()

    events = []

    for camera, camera_stats in (
        stats.get("cameras", {}).items()
    ):
        events.append(
            build_camera_event(
                camera,
                camera_stats,
            )
        )

    return events


def publish(
    events: list[EventEnvelope],
) -> None:
    bus = build_default_event_bus()

    for event in events:
        bus.publish(event)


def main() -> None:
    events = collect()

    for event in events:
        print(
            event.resource_id,
            event.status,
            event.payload.get("camera_fps"),
            flush=True,
        )

    publish(events)


if __name__ == "__main__":
    main()
