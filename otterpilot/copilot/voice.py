"""Respostas faladas do Copilot: curtas, para caber no pipeline de voz sem atraso.

Pedidos que chegam pelo canal `voice` (o aparelho de mesa) têm um orçamento
apertado de tempo: o texto precisa virar áudio frase a frase, e cada caractere
a mais é síntese e espera a mais. Por isso a resposta falada é limitada a
poucas frases, o contexto do ambiente é reduzido ao que a pergunta pede e a
geração do LLM é interrompida assim que já há o bastante.

A persona não muda: continua sendo a lontra rabugenta. Só o tamanho muda.
"""

from __future__ import annotations

import re
import unicodedata

MAX_SENTENCES = 2
MAX_CHARS = 190
# Teto duro de tokens gerados; o corte normal vem de `voice_enough`.
NUM_PREDICT = 120
# Contexto reduzido (o do chat web lista todos os recursos).
MAX_PROBLEMS = 5
MAX_RESOURCE_LINES = 8
MAX_HISTORY_CHARS = 1200

VOICE_RULES = (
    "Esta resposta será FALADA em voz alta por um alto-falante: no máximo DUAS frases "
    "curtas (cerca de 150 caracteres no total), sem listas, sem markdown e sem rodeios. "
    "Mantenha o seu jeito, mas vá direto ao fato essencial e, havendo problema, ao "
    "próximo passo."
)

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
_WHITESPACE = re.compile(r"\s+")

# Palavras da pergunta -> capabilities cujo estado vale incluir no contexto.
TOPICS: dict[str, tuple[str, ...]] = {
    "virtualization": ("vm", "vms", "lxc", "container", "containers", "proxmox", "maquina", "maquinas", "workload"),
    "host_health": ("servidor", "servidores", "host", "hosts", "cpu", "memoria", "disco", "uptime", "proxmox"),
    "dns": ("dns", "adguard", "bloqueio", "bloqueado", "bloqueados", "dominio"),
    "camera_health": ("camera", "cameras", "frigate", "fps"),
    "object_detection": ("deteccao", "detectou", "pessoa", "cachorro", "movimento"),
    "zigbee_health": ("zigbee", "z2m", "sensor", "sensores", "lampada", "lampadas"),
    "llm_runtime": ("llm", "ollama", "modelo", "gpu", "vram", "latencia", "qwen"),
    "ups": ("ups", "nobreak", "bateria", "energia"),
    "environment_health": ("temperatura", "calor", "rack", "ambiente"),
    "vehicle": ("carro", "veiculo", "combustivel", "pneu", "pneus", "porta", "trancado", "revisao"),
}


def _flatten(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def trim_voice(text: str, max_sentences: int = MAX_SENTENCES, max_chars: int = MAX_CHARS) -> str:
    """Corta a resposta em `max_sentences` frases e `max_chars` caracteres, sempre em fim de frase."""

    flat = _flatten(text)
    out = ""

    for sentence in _SENTENCE_END.split(flat)[:max_sentences]:
        candidate = f"{out} {sentence}".strip()

        if len(candidate) > max_chars:
            if not out:
                # A primeira frase sozinha estoura: corta numa pausa (vírgula, ponto
                # e vírgula, dois pontos) ou num espaço e fecha com ponto.
                window = candidate[:max_chars]
                cut = max(window.rfind(", "), window.rfind("; "), window.rfind(": "))

                if cut < max_chars // 2:
                    cut = window.rfind(" ")

                out = window[: cut if cut > 0 else max_chars].rstrip(",;: ") + "."

            break

        out = candidate

    return out or flat[:max_chars]


def voice_enough(text: str, max_sentences: int = MAX_SENTENCES, max_chars: int = MAX_CHARS) -> bool:
    """Já há texto suficiente para a resposta falada? Então o streaming pode parar."""

    flat = _flatten(text)

    return len(_SENTENCE_END.split(flat)) > max_sentences or len(flat) >= max_chars + 40


def relevant_capabilities(question: str) -> set[str]:
    """Capabilities que a pergunta menciona (por palavras-chave, sem acento)."""

    words = set(re.findall(r"[a-z0-9]+", _normalize(question)))

    return {capability for capability, keywords in TOPICS.items() if words & set(keywords)}
