# Copilot — personas e modelo (contrato da API)

Atualizado em 2026-10-31. Backend pronto; a interface ainda não usa estes
endpoints. Este documento é o contrato para quem for construir a tela.

## Conceito

Uma **persona** define o nome, o avatar e o tom do Copilot ("a Lontraz").
As regras sobre fatos (usar só os dados coletados, não inventar números,
destacar alertas) ficam fixas no prompt (`otterpilot/copilot/service.py`) e
valem para todas as personas: a persona muda só o jeito de falar.

- **Embutidas** (`builtin: true`): vêm com o pacote, em
  `otterpilot/copilot/personas/*.yaml`. Hoje: `lontraz` (lontra ranzinza)
  e `unicornio` (unicórnio bobão). Não podem ser excluídas; editar grava uma
  versão à parte (`customized: true`) que pode ser desfeita.
- **Próprias** (`builtin: false`): criadas pelo usuário. Podem ser excluídas.
- **Canais**: cada canal tem uma persona padrão. `web` é o chat da interface;
  `mqtt` é quem responde em `otterpilot/request` (Home Assistant). `voice` é o
  aparelho de mesa: as respostas são faladas, então saem **curtas** (no máximo 2
  frases e ~190 caracteres, ver `otterpilot/copilot/voice.py`), com contexto
  reduzido e a geração do LLM interrompida assim que já há o bastante. Se a
  persona de um canal deixar de existir, o canal volta para `lontraz`.
- **Humores do avatar**: `ok`, `warn`, `crit`, `thinking`. A sugestão é
  usar o status geral de `GET /api/system` (`overall_status`):
  `healthy → ok`, `degraded → warn`, `critical → crit`, e `thinking`
  enquanto espera a resposta do LLM.

Trocar ou editar persona **não reinicia nada**: o Copilot relê os arquivos a
cada pergunta. Mudar o **modelo** reinicia os serviços (grava no `.env`).

## Onde fica

| Caminho | Conteúdo |
|---|---|
| `otterpilot/copilot/personas/*.yaml` | personas embutidas (pacote) |
| `otterpilot/copilot/avatars/<avatar>-<humor>.svg` | avatares embutidos, 4 humores cada (pacote; arte provisória, pode ser substituída mantendo os nomes) |
| `<config>/copilot/personas/<id>.yaml` | personas próprias e versões editadas das embutidas |
| `<config>/copilot/avatars/<id>.<ext>` | imagem enviada para uma persona |
| `<config>/copilot/settings.yaml` | persona de cada canal |

`<config>` é `/etc/otterpilot/config` em produção. A pasta `copilot/` fica
fora do `watch_config`, que só observa `config/*.yaml`.

## Modelo de persona

| Campo | Tipo | Regras |
|---|---|---|
| `id` | string | `^[a-z0-9][a-z0-9_-]{0,39}$`; definido na criação, imutável |
| `name` | string | obrigatório, até 40 caracteres |
| `description` | string | até 200 |
| `avatar` | string | `otter`, `unicorn` ou `custom` |
| `color` | string | `#rrggbb` (sugestão: contorno do avatar, destaque) |
| `temperature` | número ou `null` | 0 a 1,5; `null` usa o padrão do modelo |
| `greeting` | string | até 200 (sugestão: conversa vazia) |
| `personality` | string | obrigatório, até 4000; texto livre que vai para o prompt |

Espaços nas pontas são removidos antes de validar.

## Endpoints

Todos exigem sessão (cookie `otterpilot_session`, o mesmo da interface).
Sem sessão: `401`. O esquema dos corpos está em `GET /openapi.json`.

### `GET /api/copilot/config`

Tudo o que a tela precisa de uma vez.

```json
{
  "channels": {"web": "lontraz", "mqtt": "lontraz", "voice": "lontraz"},
  "channel_labels": {"web": "Chat web", "mqtt": "Home Assistant (MQTT)", "voice": "Voz (aparelho de mesa)"},
  "personas": [
    {
      "id": "lontraz",
      "name": "Lontraz",
      "description": "Lontra ranzinza, sarcástica e tecnicamente impecável.",
      "avatar": "otter",
      "color": "#0f7c86",
      "temperature": null,
      "greeting": "Fala. O que quebrou dessa vez?",
      "personality": "Você é uma lontra ranzinza que já viu servidor demais cair...",
      "builtin": true,
      "customized": false,
      "avatar_urls": {
        "ok": "/api/copilot/avatars/otter-ok.svg",
        "warn": "/api/copilot/avatars/otter-warn.svg",
        "crit": "/api/copilot/avatars/otter-crit.svg",
        "thinking": "/api/copilot/avatars/otter-thinking.svg"
      },
      "channels": ["web", "mqtt", "voice"]
    }
  ],
  "avatars": [
    {"id": "otter", "name": "Lontra ranzinza"},
    {"id": "unicorn", "name": "Unicórnio bobão"}
  ],
  "max_avatar_kb": 256,
  "model": {
    "ollama_configured": true,
    "model": null,
    "default_model": "qwen3.5:9b",
    "num_ctx": null,
    "timeout_seconds": null,
    "default_timeout_seconds": 120
  }
}
```

- `personas` vem ordenada: embutidas primeiro (`lontraz`, `unicornio`),
  depois as próprias por nome.
- `persona.channels`: em quais canais ela é a padrão.
- `avatar_urls`: use direto em `<img src>`. Para `avatar: "custom"` os quatro
  humores apontam para a mesma imagem
  (`/api/copilot/personas/<id>/avatar?v=<versão>`; o `v` muda quando a
  imagem muda).
- `model.model: null` significa "padrão" (`default_model`); o mesmo vale para
  `timeout_seconds`. `num_ctx: null` usa o padrão do Ollama.

### `PUT /api/copilot/channels`

```json
{"channels": {"mqtt": "unicornio"}}
```

Só os canais enviados mudam; `null` volta para a padrão. Responde com o mesmo
corpo de `GET /api/copilot/config`. `422` para canal ou persona desconhecidos
(`"Persona desconhecida: nada"`).

### `POST /api/copilot/personas` — criar

```json
{
  "id": "gato",
  "name": "Gato Preguiçoso",
  "description": "Responde com preguiça, mas certo.",
  "avatar": "otter",
  "color": "#aa7733",
  "temperature": null,
  "greeting": "Hmm?",
  "personality": "Responda com preguiça, mas sem errar os fatos.",
  "avatar_image": null
}
```

Responde com a persona no formato de `config.personas[]`. `422` se o `id`
já existir ou algum campo for inválido. O `id` é escolha do cliente: o
protótipo gerava um slug do nome (sem acentos, minúsculo, `-`) com sufixo
`-2`, `-3`… até ficar único.

### `PUT /api/copilot/personas/{id}` — editar

Mesmo corpo, sem `id`. Para uma embutida, grava a versão editada
(`customized: true`). `404` se a persona não existir.

### `DELETE /api/copilot/personas/{id}`

- Própria: exclui (inclusive a imagem). Canais que a usavam voltam para a padrão.
- Embutida editada: restaura o padrão.
- Embutida sem edição: `404` (`"Nada para excluir ou restaurar"`).

Responde `{"result": "deleted" | "reset", ...config}`.

### Avatar próprio

Envie a imagem em `avatar_image`, no POST ou no PUT, como **data URL**
(o resultado de `FileReader.readAsDataURL`):

```text
data:image/png;base64,iVBORw0KGgo...
```

- Formatos: PNG, JPEG, WebP ou SVG; até `max_avatar_kb` (256 KB) depois de
  decodificar. O conteúdo é conferido (não basta o tipo declarado).
- Com `avatar_image`, o `avatar` vira `custom` automaticamente.
- Para manter a imagem atual ao editar: `avatar: "custom"` sem `avatar_image`.
- Trocar para `otter`/`unicorn` apaga a imagem enviada.
- `avatar: "custom"` sem imagem nova nem anterior: `422`.
- Ao duplicar uma persona com imagem própria, o cliente precisa baixar a
  imagem (`avatar_urls.ok`) e reenviá-la como data URL.

### `GET /api/copilot/personas/{id}/avatar`

A imagem enviada. Vem com `Content-Security-Policy: ...; sandbox` e
`nosniff`: use em `<img>`, nunca injete o SVG no DOM. `404` se não houver.

### `GET /api/copilot/avatars/{avatar}-{humor}.svg`

Avatares embutidos, ex.: `/api/copilot/avatars/unicorn-thinking.svg`. `404`
para nomes fora de `avatars[] × {ok, warn, crit, thinking}`.

### `GET /api/copilot/models`

Modelos instalados no Ollama, para sugerir no campo de modelo. Nunca falha:

```json
{
  "available": true,
  "models": [
    {"name": "qwen3.5:9b", "size_gb": 6.6, "parameter_size": "9.0B",
     "quantization": "Q4_K_M", "family": "qwen35"}
  ],
  "error": null
}
```

Com Ollama fora do ar ou sem URL: `available: false` e `error` com o motivo.
Pode levar até 5 s; carregue em paralelo com o resto da tela.

### `PUT /api/copilot/model`

```json
{"model": "qwen3.5:9b", "num_ctx": 8192, "timeout_seconds": 120}
```

- Envie os três campos: o que vier `null` (ou igual ao padrão) volta ao padrão.
- `model`: `^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,199}$`; `num_ctx`: 512 a
  1048576; `timeout_seconds`: 10 a 900.
- Grava `OLLAMA_MODEL`, `OLLAMA_NUM_CTX` e `OLLAMA_TIMEOUT_SECONDS` no `.env`,
  **as mesmas chaves do formulário Integrações › Ollama** (que continua
  funcionando). Os serviços reiniciam em alguns segundos. O mesmo modelo é o
  monitorado pela capability `llm_runtime`.
- Responde com o corpo de `GET /api/copilot/config`.

### `POST /api/copilot/query` (alterado)

```json
{"question": "O DNS está ok?", "persona": "unicornio"}
```

`persona` é opcional: sem ela (ou com um ID desconhecido) responde a persona
do canal `web`. A resposta ganhou `persona`:

```json
{
  "request_id": "…", "timestamp": "…", "question": "…", "answer": "…",
  "ok": true, "model": "qwen3.5:9b", "duration_ms": 5585,
  "persona": {"id": "unicornio", "name": "Unicórnio Bobão"}
}
```

## Erros

- Validação de persona e de canais: `422` com `detail` em texto, já em
  português e pronto para mostrar, campos separados por `;`:
  `"Cor: use o formato #rrggbb; Temperatura: máximo 1,5; Personalidade: obrigatório"`.
- Corpo malformado (campo faltando, tipo errado, padrão de `model`): `422`
  padrão do FastAPI, com `detail` como lista de `{loc, msg, type}` (em inglês),
  igual aos demais endpoints. O `request()` atual da interface já trata as
  duas formas.

## MQTT

A resposta publicada em `otterpilot/response` (e no tópico legado) ganhou o
campo `persona` com o **nome** de quem respondeu. É aditivo: automações que
não o conhecem continuam funcionando.

## Referência

Houve um protótipo de interface (página "Configurações › Personas" e chat com
avatar e seletor de persona) que foi descartado; a tela fica com o agente de
interface. Os testes do contrato estão em `tests/test_personas.py`.
