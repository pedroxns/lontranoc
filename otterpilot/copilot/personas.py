"""Personas do Copilot: nome, personalidade e avatar.

As personas embutidas vêm com o pacote (`otterpilot/copilot/personas/*.yaml`).
Personas próprias e versões editadas das embutidas ficam em
`<config>/copilot/personas/<id>.yaml`; imagens enviadas, em
`<config>/copilot/avatars/`; a escolha por canal, em
`<config>/copilot/settings.yaml`.

A pasta `copilot/` fica fora do `watch_config` (que só olha `config/*.yaml`):
o Copilot relê as personas a cada pergunta e nenhum serviço reinicia.

A persona define só o tom. As regras sobre fatos ficam fixas no prompt
(`copilot/service.py`) e valem para todas.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from otterpilot.core.config import CONFIG_DIR, write_config_bytes, write_config_file

DEFAULT_PERSONA_ID = "lontraz"
BUILTIN_ORDER = ("lontraz", "unicornio")

CHANNELS = {
    "web": "Chat web",
    "mqtt": "Home Assistant (MQTT)",
    "voice": "Voz (aparelho de mesa)",
}

BUILTIN_AVATARS = {
    "otter": "Lontra ranzinza",
    "unicorn": "Unicórnio bobão",
}
CUSTOM_AVATAR = "custom"
MOODS = ("ok", "warn", "crit", "thinking")

PERSONA_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")

MAX_AVATAR_BYTES = 256 * 1024
IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}
MEDIA_TYPES = {extension: media for media, extension in IMAGE_TYPES.items()}
_DATA_URL = re.compile(r"^data:(image/[a-z0-9+.-]+);base64,(.*)$", re.DOTALL)

COPILOT_DIR = "copilot"
PERSONAS_DIR = f"{COPILOT_DIR}/personas"
AVATARS_DIR = f"{COPILOT_DIR}/avatars"
SETTINGS_FILE = f"{COPILOT_DIR}/settings.yaml"


class PersonaError(ValueError):
    """Persona inválida ou operação impossível."""


class Persona(BaseModel):
    # Strip antes das validações de tamanho (só espaços conta como vazio).
    model_config = ConfigDict(extra="ignore", frozen=True, str_strip_whitespace=True)

    id: str = Field(pattern=PERSONA_ID.pattern)
    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=200)
    avatar: str = "otter"
    color: str = Field(default="#0f7c86", pattern=r"^#[0-9a-fA-F]{6}$")
    temperature: float | None = Field(default=None, ge=0, le=1.5)
    greeting: str = Field(default="", max_length=200)
    personality: str = Field(min_length=1, max_length=4000)

    @field_validator("avatar")
    @classmethod
    def _known_avatar(cls, value: str) -> str:
        if value not in BUILTIN_AVATARS and value != CUSTOM_AVATAR:
            raise ValueError(f"avatar desconhecido: {value}")
        return value


# Usada só se os arquivos do pacote estiverem ilegíveis.
FALLBACK_PERSONA = Persona(
    id=DEFAULT_PERSONA_ID,
    name="Lontraz",
    personality=(
        "Você é uma lontra rabugenta, mal-educada e sarcástica, de mau humor crônico. "
        "Reclama, debocha e xinga de leve, mas faz o trabalho com competência. Sem "
        "ofensas discriminatórias, ameaças ou palavrões pesados. Em falha crítica, "
        "diga primeiro o fato, o impacto e o próximo passo."
    ),
)


@dataclass(frozen=True)
class PersonaEntry:
    persona: Persona
    builtin: bool
    customized: bool

    @property
    def id(self) -> str:
        return self.persona.id


# ---------------------------------------------------------------- arquivos


def _user_dir() -> Path:
    return CONFIG_DIR / PERSONAS_DIR


def _avatar_dir() -> Path:
    return CONFIG_DIR / AVATARS_DIR


def _settings_path() -> Path:
    return CONFIG_DIR / SETTINGS_FILE


def _parse(persona_id: str, text: str, origin: str) -> Persona | None:
    try:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise PersonaError("o arquivo precisa ser um mapa YAML")
        return Persona(**{**data, "id": persona_id})
    except (yaml.YAMLError, ValidationError, PersonaError) as error:
        print(f"[personas] Ignorando {origin}: {error}", flush=True)
        return None


def _load_builtins() -> dict[str, Persona]:
    personas: dict[str, Persona] = {}

    try:
        files = list(resources.files("otterpilot.copilot").joinpath("personas").iterdir())
    except (FileNotFoundError, OSError):
        files = []

    for file in files:
        if not file.name.endswith(".yaml"):
            continue

        persona_id = file.name.removesuffix(".yaml")
        text = file.read_text(encoding="utf-8")
        persona = _parse(persona_id, text, f"persona embutida {file.name}")

        if persona:
            personas[persona_id] = persona

    return personas


def _load_user() -> dict[str, Persona]:
    personas: dict[str, Persona] = {}
    directory = _user_dir()

    if not directory.is_dir():
        return personas

    for path in sorted(directory.glob("*.yaml")):
        persona_id = path.stem

        if not PERSONA_ID.match(persona_id):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            print(f"[personas] Ignorando {path}: {error}", flush=True)
            continue

        persona = _parse(persona_id, text, str(path))

        if persona:
            personas[persona_id] = persona

    return personas


def _sort_key(entry: PersonaEntry) -> tuple[int, int, str]:
    if entry.id in BUILTIN_ORDER:
        return (0, BUILTIN_ORDER.index(entry.id), "")

    return (1 if entry.builtin else 2, 0, entry.persona.name.lower())


def list_personas() -> list[PersonaEntry]:
    builtins = _load_builtins()
    user = _load_user()
    entries = [
        PersonaEntry(
            persona=user.get(persona_id, persona),
            builtin=True,
            customized=persona_id in user,
        )
        for persona_id, persona in builtins.items()
    ]
    entries.extend(
        PersonaEntry(persona=persona, builtin=False, customized=False)
        for persona_id, persona in user.items()
        if persona_id not in builtins
    )

    if not entries:
        entries.append(PersonaEntry(persona=FALLBACK_PERSONA, builtin=True, customized=False))

    return sorted(entries, key=_sort_key)


def get_persona(persona_id: str) -> PersonaEntry | None:
    return next((entry for entry in list_personas() if entry.id == persona_id), None)


# ---------------------------------------------------------------- avatar


def builtin_avatar_svg(filename: str) -> bytes | None:
    """SVG embutido `<avatar>-<humor>.svg` (otterpilot/copilot/avatars/), ou None."""

    avatar, _, mood = filename.removesuffix(".svg").rpartition("-")

    if not filename.endswith(".svg") or avatar not in BUILTIN_AVATARS or mood not in MOODS:
        return None

    try:
        return resources.files("otterpilot.copilot").joinpath("avatars", filename).read_bytes()
    except (FileNotFoundError, OSError):
        return None


def avatar_file(persona_id: str) -> Path | None:
    directory = _avatar_dir()

    for extension in MEDIA_TYPES:
        path = directory / f"{persona_id}.{extension}"

        if path.is_file():
            return path

    return None


def _remove_avatar(persona_id: str) -> None:
    for extension in MEDIA_TYPES:
        (_avatar_dir() / f"{persona_id}.{extension}").unlink(missing_ok=True)


def _looks_like(extension: str, data: bytes) -> bool:
    if extension == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == "jpg":
        return data.startswith(b"\xff\xd8\xff")
    if extension == "webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return b"<svg" in data[:2048].lower()


def decode_avatar(data_url: str) -> tuple[str, bytes]:
    """Valida uma imagem enviada como data URL e devolve (extensão, bytes)."""

    match = _DATA_URL.match(data_url.strip())

    if not match:
        raise PersonaError("Imagem inválida: envie PNG, JPEG, WebP ou SVG")

    extension = IMAGE_TYPES.get(match.group(1))

    if extension is None:
        raise PersonaError("Formato de imagem não suportado: use PNG, JPEG, WebP ou SVG")

    try:
        data = base64.b64decode(match.group(2), validate=False)
    except (binascii.Error, ValueError) as error:
        raise PersonaError("Imagem corrompida") from error

    if len(data) > MAX_AVATAR_BYTES:
        raise PersonaError(f"Imagem grande demais (máximo {MAX_AVATAR_BYTES // 1024} KB)")

    if not _looks_like(extension, data):
        raise PersonaError("O conteúdo da imagem não corresponde ao formato informado")

    return extension, data


# ---------------------------------------------------------------- gravação


def _persona_yaml(persona: Persona) -> str:
    data = persona.model_dump(exclude={"id"})

    if data["temperature"] is None:
        data.pop("temperature")

    header = "# Editado pela interface do OtterPilot (Configurações › Personas).\n"
    return header + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def _build(persona_id: str, data: dict[str, Any]) -> Persona:
    if not PERSONA_ID.match(persona_id):
        raise PersonaError(
            "ID inválido: use até 40 letras minúsculas, números, '-' ou '_'"
        )

    try:
        return Persona(**{**data, "id": persona_id})
    except ValidationError as error:
        problems = "; ".join(_describe_error(item) for item in error.errors())
        raise PersonaError(problems) from error


FIELD_LABELS = {
    "id": "ID",
    "name": "Nome",
    "description": "Descrição",
    "avatar": "Avatar",
    "color": "Cor",
    "temperature": "Temperatura",
    "greeting": "Saudação",
    "personality": "Personalidade",
}


def _number(value: Any) -> str:
    return str(value).replace(".", ",")


def _describe_error(item: dict[str, Any]) -> str:
    """Erro do pydantic em português, pronto para mostrar na interface."""

    field = str(item["loc"][0]) if item.get("loc") else ""
    kind = item.get("type", "")
    ctx = item.get("ctx") or {}

    if kind == "missing" or (kind == "string_too_short" and ctx.get("min_length") == 1):
        message = "obrigatório"
    elif kind == "string_too_short":
        message = f"mínimo de {ctx['min_length']} caracteres"
    elif kind == "string_too_long":
        message = f"máximo de {ctx['max_length']} caracteres"
    elif kind == "string_pattern_mismatch":
        message = "use o formato #rrggbb" if field == "color" else "formato inválido"
    elif kind == "greater_than_equal":
        message = f"mínimo {_number(ctx['ge'])}"
    elif kind == "less_than_equal":
        message = f"máximo {_number(ctx['le'])}"
    elif kind in ("float_parsing", "float_type"):
        message = "informe um número"
    elif kind == "value_error":
        message = str(ctx.get("error") or item.get("msg"))
    else:
        message = item.get("msg", "valor inválido")

    return f"{FIELD_LABELS.get(field, field)}: {message}"


def save_persona(
    persona_id: str,
    data: dict[str, Any],
    *,
    avatar_image: str | None = None,
    create: bool = False,
) -> PersonaEntry:
    """Cria ou atualiza uma persona. Para as embutidas, grava uma versão editada."""

    existing = get_persona(persona_id)

    if create and existing:
        raise PersonaError(f"Já existe uma persona com o ID '{persona_id}'")

    if not create and not existing:
        raise KeyError(persona_id)

    image = decode_avatar(avatar_image) if avatar_image else None

    if image:
        data = {**data, "avatar": CUSTOM_AVATAR}

    persona = _build(persona_id, data)

    if persona.avatar == CUSTOM_AVATAR and not image and not avatar_file(persona_id):
        raise PersonaError("Envie uma imagem para usar um avatar próprio")

    if image:
        _remove_avatar(persona_id)
        write_config_bytes(f"{AVATARS_DIR}/{persona_id}.{image[0]}", image[1])
    elif persona.avatar != CUSTOM_AVATAR:
        _remove_avatar(persona_id)

    write_config_file(f"{PERSONAS_DIR}/{persona_id}.yaml", _persona_yaml(persona))

    entry = get_persona(persona_id)
    assert entry is not None
    return entry


def delete_persona(persona_id: str) -> str:
    """Exclui uma persona própria ou restaura o padrão de uma embutida.

    Devolve "deleted" ou "reset". KeyError se não houver o que remover.
    """

    entry = get_persona(persona_id)

    if entry is None or (entry.builtin and not entry.customized):
        raise KeyError(persona_id)

    (_user_dir() / f"{persona_id}.yaml").unlink(missing_ok=True)
    _remove_avatar(persona_id)

    if entry.builtin:
        return "reset"

    channels = load_settings().get("channels", {})
    orphaned = {channel: None for channel, value in channels.items() if value == persona_id}

    if orphaned:
        set_channels(orphaned)

    return "deleted"


# ---------------------------------------------------------------- canais


def load_settings() -> dict[str, Any]:
    path = _settings_path()

    if not path.is_file():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        print(f"[personas] Ignorando {path}: {error}", flush=True)
        return {}

    return data if isinstance(data, dict) else {}


def channel_personas() -> dict[str, str]:
    """Persona efetiva de cada canal (com fallback para a padrão)."""

    configured = load_settings().get("channels") or {}
    available = {entry.id for entry in list_personas()}
    fallback = DEFAULT_PERSONA_ID if DEFAULT_PERSONA_ID in available else sorted(available)[0]

    return {
        channel: configured.get(channel) if configured.get(channel) in available else fallback
        for channel in CHANNELS
    }


def set_channels(updates: dict[str, str | None]) -> dict[str, str]:
    """Define a persona de cada canal. None volta para a padrão."""

    available = {entry.id for entry in list_personas()}
    settings = load_settings()
    channels = dict(settings.get("channels") or {})

    for channel, persona_id in updates.items():
        if channel not in CHANNELS:
            raise PersonaError(f"Canal desconhecido: {channel}")

        if persona_id is None:
            channels.pop(channel, None)
        elif persona_id not in available:
            raise PersonaError(f"Persona desconhecida: {persona_id}")
        else:
            channels[channel] = persona_id

    settings["channels"] = channels
    write_config_file(
        SETTINGS_FILE,
        yaml.safe_dump(settings, allow_unicode=True, sort_keys=False),
    )

    return channel_personas()


def resolve_persona(persona_id: str | None = None, *, channel: str = "web") -> Persona:
    """Persona que vai responder: a pedida, senão a do canal, senão a padrão."""

    try:
        entries = {entry.id: entry.persona for entry in list_personas()}

        if persona_id and persona_id in entries:
            return entries[persona_id]

        return entries[channel_personas().get(channel, DEFAULT_PERSONA_ID)]
    except Exception as error:  # nunca impedir uma resposta por causa da persona
        print(f"[personas] Usando a persona de emergência: {error}", flush=True)
        return FALLBACK_PERSONA
