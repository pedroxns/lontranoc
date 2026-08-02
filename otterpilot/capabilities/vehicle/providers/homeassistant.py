from datetime import datetime, timezone

import requests
import yaml

from otterpilot.core.config import config_path, get_env
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus


CONFIG_FILE = config_path("vehicle.yaml")

HA_URL = (get_env("HA_URL", required=True) or "").rstrip("/")
HA_TOKEN = (
    get_env("HA_TOKEN_VEHICLE")
    or get_env("HA_TOKEN", required=True)
)

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)["vehicle"]


def get_ha_states():
    response = requests.get(
        f"{HA_URL}/api/states",
        headers={
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=20,
    )
    response.raise_for_status()
    return {item["entity_id"]: item for item in response.json()}


def state_value(states, entity_id, cast=None):
    if not entity_id:
        return None

    item = states.get(entity_id)
    if not item:
        return None

    value = item.get("state")

    if value in [None, "unknown", "unavailable"]:
        return None

    if cast:
        try:
            return cast(value)
        except Exception:
            return None

    return value


def bool_state(states, entity_id):
    value = state_value(states, entity_id)
    if value is None:
        return None
    return value == "on"


def tracker_data(states, entity_id):
    item = states.get(entity_id)
    if not item:
        return {}

    attrs = item.get("attributes", {}) or {}

    return {
        "zone": item.get("state"),
        "latitude": attrs.get("latitude"),
        "longitude": attrs.get("longitude"),
        "gps_accuracy": attrs.get("gps_accuracy"),
        "in_zones": attrs.get("in_zones", []),
        "source_type": attrs.get("source_type"),
    }


def build_snapshot(config, states):
    v = config

    return {
        "vehicle_id": v["id"],
        "manufacturer": v.get("manufacturer"),
        "model": v.get("model"),

        "location": tracker_data(states, v["location"]["tracker"]),

        "fuel": {
            "range_km": state_value(states, v["fuel"].get("range"), float),
            "percent": state_value(states, v["fuel"].get("percent"), float),
            "liters": state_value(states, v["fuel"].get("liters"), float),
            "average_consumption_km_l": state_value(states, v["fuel"].get("average_consumption"), float),
        },

        "engine": {
            "running": bool_state(states, v["engine"].get("running")),
            "temperature_c": state_value(states, v["engine"].get("temperature"), float),
        },

        "battery": {
            "aux_voltage": state_value(states, v["battery"].get("aux_voltage"), float),
            "aux_percent": state_value(states, v["battery"].get("aux_percent"), float),
            "hybrid_percent": state_value(states, v["battery"].get("hybrid_percent"), float),
        },

        "maintenance": {
            "odometer_km": state_value(states, v["maintenance"].get("odometer"), float),
            "distance_to_service_km": state_value(states, v["maintenance"].get("distance_to_service"), float),
            "days_to_service": state_value(states, v["maintenance"].get("days_to_service"), int),
        },

        "tires": {
            "front_left_psi": state_value(states, v["tires"].get("front_left"), float),
            "front_right_psi": state_value(states, v["tires"].get("front_right"), float),
            "rear_left_psi": state_value(states, v["tires"].get("rear_left"), float),
            "rear_right_psi": state_value(states, v["tires"].get("rear_right"), float),
        },

        "doors": {
            "locked": bool_state(states, v["doors"].get("locked")),
            "driver_open": bool_state(states, v["doors"].get("driver")),
            "passenger_open": bool_state(states, v["doors"].get("passenger")),
            "rear_left_open": bool_state(states, v["doors"].get("rear_left")),
            "rear_right_open": bool_state(states, v["doors"].get("rear_right")),
            "trunk_open": bool_state(states, v["doors"].get("trunk")),
            "hood_open": bool_state(states, v["doors"].get("hood")),
        },

        "metadata": {
            "last_update": state_value(states, v["metadata"].get("last_update")),
            "update_interval_s": state_value(states, v["metadata"].get("update_interval"), int),
        },
    }


def emit_snapshot(snapshot: dict) -> None:
    tires = snapshot["tires"]
    doors = snapshot["doors"]
    fuel = snapshot["fuel"]
    location = snapshot["location"]

    tire_values = [
        tires.get("front_left_psi"),
        tires.get("front_right_psi"),
        tires.get("rear_left_psi"),
        tires.get("rear_right_psi"),
    ]

    valid_tires = [
        value
        for value in tire_values
        if isinstance(value, (int, float))
    ]

    min_tire = min(valid_tires) if valid_tires else None

    any_door_open = any(
        doors.get(key) is True
        for key in (
            "driver_open",
            "passenger_open",
            "rear_left_open",
            "rear_right_open",
            "trunk_open",
            "hood_open",
        )
    )

    event = EventEnvelope(
        capability="vehicle",
        connector="homeassistant",
        event_type="snapshot",
        resource_id=snapshot["vehicle_id"],
        severity="info",
        status="ok",
        message=f"Vehicle snapshot: {snapshot['vehicle_id']}",
        payload={
            "vehicle_id": snapshot["vehicle_id"],
            "manufacturer": snapshot["manufacturer"],
            "model": snapshot["model"],

            "zone": location.get("zone"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "gps_accuracy": location.get("gps_accuracy"),

            "range_km": fuel.get("range_km"),
            "fuel_percent": fuel.get("percent"),
            "fuel_liters": fuel.get("liters"),
            "average_consumption_km_l": fuel.get(
                "average_consumption_km_l"
            ),

            "engine_running": snapshot["engine"].get("running"),
            "engine_temp_c": snapshot["engine"].get(
                "temperature_c"
            ),

            "aux_battery_voltage": snapshot["battery"].get(
                "aux_voltage"
            ),
            "aux_battery_percent": snapshot["battery"].get(
                "aux_percent"
            ),
            "hybrid_battery_percent": snapshot["battery"].get(
                "hybrid_percent"
            ),

            "odometer_km": snapshot["maintenance"].get(
                "odometer_km"
            ),
            "distance_to_service_km": snapshot["maintenance"].get(
                "distance_to_service_km"
            ),
            "days_to_service": snapshot["maintenance"].get(
                "days_to_service"
            ),

            "tire_front_left_psi": tires.get("front_left_psi"),
            "tire_front_right_psi": tires.get("front_right_psi"),
            "tire_rear_left_psi": tires.get("rear_left_psi"),
            "tire_rear_right_psi": tires.get("rear_right_psi"),
            "tire_min_psi": min_tire,

            "locked": doors.get("locked"),
            "any_door_open": any_door_open,
            "door_driver_open": doors.get("driver_open"),
            "door_passenger_open": doors.get("passenger_open"),
            "door_rear_left_open": doors.get("rear_left_open"),
            "door_rear_right_open": doors.get("rear_right_open"),
            "door_trunk_open": doors.get("trunk_open"),
            "door_hood_open": doors.get("hood_open"),

            "last_update": snapshot["metadata"].get("last_update"),
            "update_interval_s": snapshot["metadata"].get(
                "update_interval_s"
            ),

            "snapshot": snapshot,
        },
    )

    bus = build_default_event_bus()
    bus.publish(event)

def collect() -> dict:
    """Coleta e normaliza o estado atual do veículo via Home Assistant."""

    if not HA_URL or not HA_TOKEN:
        raise RuntimeError(
            "HA_URL e HA_TOKEN_VEHICLE/HA_TOKEN "
            "precisam estar configurados"
        )

    config = load_config()
    states = get_ha_states()

    return build_snapshot(config, states)

def publish(snapshot: dict) -> None:
    """Publica um snapshot normalizado no Knowledge Provider."""

    emit_snapshot(snapshot)

def main() -> None:
    snapshot = collect()

    print(
        "OtterPilot vehicle snapshot:",
        snapshot,
        flush=True,
    )

    publish(snapshot)


if __name__ == "__main__":
    main()
