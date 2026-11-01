# Canal de voz do Copilot (contrato da API)

Atualizado em 2026-10-31. Usado pelo aparelho de mesa (a Lontraz): a pergunta
vem da voz, a resposta volta como texto **curto** para ser falada.

## Princípios

- **Resposta curta.** Fala custa tempo: cada caractere vira áudio sintetizado.
  No canal de voz a resposta tem no máximo **2 frases e ~190 caracteres**, sempre
  terminando em fim de frase (`otterpilot/copilot/voice.py`). O chat web e o MQTT
  não mudam.
- **O jeito é o da persona do canal.** Hoje a lontra rabugenta (`lontraz`), como
  nos outros canais; a persona é escolhida em `personas.CHANNELS["voice"]`.
- **Contexto reduzido.** O prompt leva o status geral, até 5 problemas e só os
  recursos das áreas citadas na pergunta (por palavra-chave), não o ambiente todo.
- **Streaming com parada antecipada.** O LLM é interrompido assim que já há o
  bastante (fechar a conexão faz o Ollama abortar a geração). O texto parcial
  sai pelo endpoint, para o cliente sintetizar a 1ª frase antes do fim.

## Autenticação: tokens de serviço

Máquinas não usam a senha da interface. Cada uma tem um **token de serviço**,
com escopo e revogável:

```bash
sudo otterpilot token create aparelho      # mostra o token UMA vez (escopo copilot:voice)
sudo otterpilot token list                 # nome, escopos e data (nunca o valor)
sudo otterpilot token revoke aparelho
```

- O token é `otp_` + 256 bits aleatórios. Em `auth.json` fica só o hash (SHA-256);
  perdeu o token, revoga e cria outro.
- Escopos conhecidos: `copilot:voice`. Um token só serve para o que o escopo diz.
- Revogar um token não mexe na senha nem nos outros tokens.
- Tokens inválidos contam como tentativa falha, com o mesmo limite do login
  (10 em 5 minutos por IP, depois `429`).

## `POST /api/copilot/voice`

Aceita **token de serviço** (`Authorization: Bearer otp_...`) com o escopo
`copilot:voice` **ou** a sessão da interface (para testar pelo navegador).

Corpo:

```json
{"question": "como está o nobreak?", "persona": null}
```

`question`: 1 a 500 caracteres. `persona`: opcional (padrão: a do canal `voice`).

Resposta: `200`, `application/x-ndjson`, uma linha JSON por evento:

```json
{"type": "text", "text": "Ah, o nobreak está em 100%, droga."}
{"type": "text", "text": "Ah, o nobreak está em 100%, droga. Pode relaxar."}
{"type": "done", "ok": true, "answer": "Ah, o nobreak está em 100%, droga. Pode relaxar.",
 "persona": {"id": "lontraz", "name": "Lontraz"}, "model": "qwen3.5:9b",
 "request_id": "...", "duration_ms": 1480, "question": "como está o nobreak?"}
```

- `text`: o texto **acumulado** até agora, já cortado pelas regras de voz (não
  repete o mesmo texto duas vezes seguidas). O cliente pode começar a falar a
  1ª frase assim que ela estiver fechada. Atenção: o texto pode **encolher** no
  fim. Se uma 2ª frase começou a aparecer e passaria do limite de caracteres, ela
  é descartada, e o último `text` volta a ter só a 1ª frase. A resposta final
  é sempre a do evento `done`; use o `text` apenas para adiantar trabalho.
- `done`: sempre o último evento de uma resposta normal. `ok: false` quando o
  Copilot não está configurado ou o LLM falhou (o `answer` explica).
- `error`: falha inesperada do servidor (último evento).
- Erros de HTTP: `401` sem token válido, `422` corpo inválido, `429` muitas
  tentativas.

Teste rápido:

```bash
curl -N -X POST http://HOST:8470/api/copilot/voice \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "como está o ambiente?"}'
```

## `GET /api/copilot/voice/persona`

Para o aparelho de mesa saber **quem ele é agora**. Mesma autenticação do endpoint
de voz (token com o escopo `copilot:voice` ou sessão). Devolve a persona escolhida
para o canal `voice`:

```json
{"id": "lontra-unicornio", "name": "Lontraz Unicórnio", "personality": "Você é Lontraz, ...",
 "temperature": null, "greeting": "Oi. Sim, estou de fantasia...", "voice": "lontraz",
 "device_avatar": "unicorn", "family_friendly": true}
```

- `device_avatar`: qual avatar o aparelho mostra (`otter` ou `unicorn`). O aparelho
  troca ao vivo, sem reiniciar nem regravar, entre os avatares que o firmware tem.
- `voice`: nome da referência de voz que o servidor de TTS usa.
- `personality`: só o tom; as regras de fatos continuam fixas no Copilot.
- `family_friendly`: o aparelho deve aplicar o mesmo filtro de linguagem às respostas
  que gerar localmente.

**Trocar de avatar é trocar a persona do canal de voz**: na página, "Avatar:
unicórnio" = `PUT /api/copilot/channels` com `{"channels": {"voice": "lontra-unicornio"}}`.
O aparelho consulta a cada ~15 s, então a mudança aparece em até esse tempo.

## O que ainda não está aqui

- O aparelho (`/api/device/*`: voz, fala, estado, eventos) ainda é servido pelo
  `lontraz.py`; ele passará a chamar este endpoint para perguntas sobre o ambiente.
- Escopos para outras máquinas (alertas, agente do PC) entram quando esses
  módulos migrarem.
