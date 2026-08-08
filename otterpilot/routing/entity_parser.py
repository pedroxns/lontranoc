OBJECT_ALIASES = {
    "cachorro": ("object", "label", "dog"),
    "cachorros": ("object", "label", "dog"),
    "dog": ("object", "label", "dog"),
    "dogs": ("object", "label", "dog"),

    "gato": ("object", "label", "cat"),
    "gatos": ("object", "label", "cat"),
    "cat": ("object", "label", "cat"),

    "pessoa": ("object", "label", "person"),
    "pessoas": ("object", "label", "person"),
    "person": ("object", "label", "person"),
    "alguem": ("object", "label", "person"),
    "gente": ("object", "label", "person"),

    "carro": ("object", "label", "car"),
    "carros": ("object", "label", "car"),
    "car": ("object", "label", "car"),

    "bicicleta": ("object", "label", "bicycle"),
    "bike": ("object", "label", "bicycle"),

    "moto": ("object", "label", "motorcycle"),
    "motocicleta": ("object", "label", "motorcycle"),
}

CAMERA_ALIASES = {
    "olho": "Olho",
    "olho mágico": "Olho",
    "olho magico": "Olho",
    "estar": "Estar",
    "jantar": "Jantar",
    "joca": "Joca",
    "miguel": "Miguel",
}


def parse_entities(question: str) -> dict:
    q = question.lower()

    filters = {}
    entities = []

    for word, (entity_type, field, value) in OBJECT_ALIASES.items():
        if word in q:
            filters[field] = value
            entities.append({
                "type": entity_type,
                "field": field,
                "value": value,
                "matched": word,
                "confidence": 1.0,
            })

    for word, camera in CAMERA_ALIASES.items():
        if word in q:
            filters["camera"] = camera
            entities.append({
                "type": "camera",
                "field": "camera",
                "value": camera,
                "matched": word,
                "confidence": 1.0,
            })

    return {
        "filters": filters,
        "entities": entities,
    }
