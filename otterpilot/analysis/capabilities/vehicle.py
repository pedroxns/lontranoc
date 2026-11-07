def analyze_vehicle(search_result: dict) -> dict:
    ctx = search_result.get("context", {})
    query_name = ctx.get("query_name")
    rows = search_result.get("rows", [])

    if not rows:
        return {
            "type": "vehicle",
            "query_name": query_name,
            "answer_hint": "Não encontrei dados recentes do veículo.",
            "confidence": 0.2,
        }

    row = rows[0]

    if query_name == "fuel":
        range_km = row.get("range_km")
        return {
            "type": "vehicle",
            "query_name": "fuel",
            "primary_value": range_km,
            "unit": "km",
            "answer_hint": f"O carro pode rodar aproximadamente {range_km:.0f} km com a autonomia atual.",
            "confidence": 1.0 if range_km is not None else 0.3,
        }

    if query_name == "fuel_level":
        return {
            "type": "vehicle",
            "query_name": "fuel_level",
            "fuel_percent": row.get("fuel_percent"),
            "fuel_liters": row.get("fuel_liters"),
            "answer_hint": (
                f"O carro está com {row.get('fuel_percent')}% de combustível, "
                f"aproximadamente {row.get('fuel_liters')} litros."
            ),
            "confidence": 0.95,
        }

    if query_name == "tires":
        tires = {
            "dianteiro esquerdo": row.get("tire_front_left_psi"),
            "dianteiro direito": row.get("tire_front_right_psi"),
            "traseiro esquerdo": row.get("tire_rear_left_psi"),
            "traseiro direito": row.get("tire_rear_right_psi"),
        }

        low = {k: v for k, v in tires.items() if isinstance(v, (int, float)) and v < 36}

        if low:
            hint = "Há pneu abaixo de 36 psi: " + ", ".join(f"{k}: {v} psi" for k, v in low.items())
        else:
            hint = "Nenhum pneu parece precisar de calibragem agora."

        return {
            "type": "vehicle",
            "query_name": "tires",
            "tires": tires,
            "low_tires": low,
            "answer_hint": hint,
            "confidence": 0.95,
        }

    if query_name == "state":
        locked = row.get("locked")
        any_door_open = row.get("any_door_open")

        return {
            "type": "vehicle",
            "query_name": "state",
            "locked": locked,
            "any_door_open": any_door_open,
            "doors": {
                "motorista": row.get("door_driver_open"),
                "passageiro": row.get("door_passenger_open"),
                "traseira esquerda": row.get("door_rear_left_open"),
                "traseira direita": row.get("door_rear_right_open"),
                "porta-malas": row.get("door_trunk_open"),
                "capô": row.get("door_hood_open"),
            },
            "answer_hint": (
                "O carro está trancado e todas as portas parecem fechadas."
                if locked and not any_door_open
                else "Verifique o estado do travamento e das portas."
            ),
            "confidence": 0.9,
        }

    if query_name == "battery_12v":
        return {
            "type": "vehicle",
            "query_name": "battery_12v",
            "voltage": row.get("aux_battery_voltage"),
            "percent": row.get("aux_battery_percent"),
            "answer_hint": (
                f"A bateria 12V está com {row.get('aux_battery_voltage')} V "
                f"e {row.get('aux_battery_percent')}% de carga."
            ),
            "confidence": 0.95,
        }

    if query_name == "battery_hybrid":
        return {
            "type": "vehicle",
            "query_name": "battery_hybrid",
            "percent": row.get("hybrid_battery_percent"),
            "answer_hint": f"A bateria híbrida está com {row.get('hybrid_battery_percent')}% de carga.",
            "confidence": 0.95,
        }

    return {
        "type": "vehicle",
        "query_name": query_name,
        "answer_hint": "Dados do veículo encontrados. Use os campos retornados para responder.",
        "row": row,
        "confidence": 0.7,
    }
