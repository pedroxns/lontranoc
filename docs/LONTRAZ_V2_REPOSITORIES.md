# LontraZ v2 + OtterPilot — arquitetura-alvo, reconstrução seletiva e plano de execução

> **Decisão atual do projeto (2026-11-02):** executar uma **modernização arquitetural abrangente** de LontraZ v2 + OtterPilot. O objetivo NÃO é somente copiar o repositório antigo, e também NÃO é reescrever às cegas todos os componentes. **Redesenhar a organização e os contratos; reescrever módulos problemáticos; preservar, portar ou adaptar drivers, animações, integrações, assets e algoritmos comprovadamente funcionais.**
>
> Este documento substitui a orientação anterior de "somente separar repositórios". **Cinco etapas macro** definidas pelo proprietário, sem subdividir em novos projetos/fases macro:
> 1. Reorganização do repositório
> 2. Testes de conectividade entre as placas
> 3. Planejamento da migração S3 + P4
> 4. Migração total
> 5. Resolução de problemas

## 0. Resultado pretendido

LontraZ v2 será um dispositivo distribuído com **dois microcontroladores**, preservando a AMOLED instalada; OtterPilot será a plataforma de inteligência e gerenciamento, independente da marca/modelo de placa.

- **Waveshare ESP32-S3-Touch-AMOLED-1.75 (sem -G)**: rosto AMOLED redondo 466×466 CO5300/QSPI, avatar/animador, touch CST9217, IMU QMI8658, captura contínua I²S/DMA dos **dois microfones** via ES7210 e cliente do link local. Reações a toque/IMU precisam permanecer locais e não bloqueantes. S3 permanece operando enquanto tela está apagada; standby visual ≠ deep sleep.
- **Guition JC-ESP32P4-M3-DEV (P4 + C6)**: cérebro embarcado, recepção de PCM, buffering, WakeNet/VAD/AFE (quando suportados e validados), conexão com OtterPilot, orquestração de estados, configuração/OTA/telemetria. A Guition é **hardware de teste inicial**, não necessariamente a PCB final.
- **OtterPilot**: raciocínio com Ollama/Qwen, integração Home Assistant/Proxmox/Frigate, personas, contexto, dashboard, APIs, STT/TTS no servidor conforme pipeline final. Deve operar mesmo com nenhuma LontraZ conectada.

**Requisito essencial:** o S3 anima e reage sem depender de chamadas remotas; o P4 processa voz e orquestra; o OtterPilot fornece inteligência de nível superior. Nenhuma decisão de IA deve bloquear atualização do avatar.

## 1. Origem real do código e restrições

### Fontes verificadas

- Backend funcional: [pedroxns/lontranoc](https://github.com/pedroxns/lontranoc), branch **refactor/otterpilot**. A \`main\` é antiga; nunca tomar seu estado como arquitetura atual.
- Projeto histórico da Guition: [pedroxns/tela-esp32p4---rack](https://github.com/pedroxns/tela-esp32p4---rack), monitor de rack P4+C6, **não firmware LontraZ**. Usar apenas drivers e pinout pertinentes com compatibilidade verificada.
- O firmware atualmente em execução na Waveshare S3 e o serviço legado \`lontraz.py\` **ainda não foram encontrados nos repositórios públicos examinados**. Localizar fontes locais, configs, assets e histórico antes de reimplementar. Registrar caminhos reais; nunca inventar um firmware como substituto do original.

### Preservação de produção

- Não editar ou apagar os repositórios históricos; não usar force push.
- Não fazer deploy automático para LXC de produção nem gravar nenhuma das placas nesta etapa sem testes e rollback.
- Preservar as funcionalidades atuais: personagens e expressões, touch, IMU, áudio, personas e vozes, HA, APIs/telemetria do OtterPilot.
- Antes de migrar repos, auditar segredos **também no histórico Git**; publicar em modo privado por padrão.
- Registrar baseline com SHA, versão da toolchain, partições, GPIOs, RAM/PSRAM, FPS, estados e funcionamento real. Quando não houver medição, marcar **não aferido**.

## 2. Estrutura de repositórios (uma plataforma, três códigos)

| Repositório | Domínio e propriedade | Não deve conter |
|---|---|---|
| \`pedroxns/otterpilot\` | Backend, APIs, IA, personas, memória/contexto, conectores, dashboard, registry e telemetria agregada | Dependências de uma placa/GPIO ou drivers ESP-IDF |
| \`pedroxns/lontraz-display-s3\` | Firmware visual, assets/estados de avatar, touch, IMU, captura dos microfones, interface link, OTA/diagnóstico local | LLM, credenciais de servidor, integrações Home Assistant |
| \`pedroxns/lontraz-core-p4\` | Firmware P4/C6, link de áudio e controle, buffers/AFE/WakeNet/VAD, máquina de estados central, networking, cliente OtterPilot, OTA/telemetria | Implementação gráfica da AMOLED, integrações de homelab |

**Contrato compartilhado:** módulo \`protocol/\` versionado dentro de \`lontraz-core-p4\` inicialmente, com structs/IDL e testes de compatibilidade usados pelo S3. Se a distribuição ficar difícil, promover a componente independente **apenas após necessidade comprovada**. Dependências devem ser fixadas por tag/commit, não copiadas manualmente sem controle.

### Esqueleto de módulos sugerido, não obrigação de nomes exatos

\`\`\`text
otterpilot/
  otterpilot/{api,core,copilot,integrations,devices,telemetry}
  tests/{unit,integration,contracts}
  docs/{architecture,adr,operations}
  deploy/
lontraz-display-s3/
  components/{board_s3,avatar,display,touch,imu,mic_capture,link,health,ota}
  main/
  assets/
  tests/{unit,integration}
  docs/{hardware,adr}
lontraz-core-p4/
  components/{board_guition,link,pcm_receiver,ring_buffer,afe,wakeword,
              dialogue,otterpilot_client,telemetry,ota}
  protocol/{include,tests}
  main/
  tests/{unit,integration}
  docs/{hardware,adr}
\`\`\`

Utilizar **ESP-IDF + FreeRTOS** no firmware, com componentes isolados por interface. Preferir SDK oficial da Espressif e drivers comprovados; adaptar LVGL já existente no S3; evitar dependência de frameworks diferentes sem justificativa. No backend, preservar Python/FastAPI e os subsistemas atuais que funcionam, refatorando por módulo.

## 3. Critérios de engenharia e qualidade

1. **Clareza antes de volume:** arquitetura por responsabilidades, interfaces pequenas, coesão alta, acoplamento baixo; SOLID quando útil, sem abstrações gratuitas. KISS/DRY/YAGNI.
2. **Core desacoplado de hardware:** BSPs isolam GPIO, codec e buses. Nunca espalhar pinagem pelo código; configuração por board/profile.
3. **Controle de concorrência:** tarefas FreeRTOS com prioridades explícitas, filas com capacidade conhecida, ring buffers DMA, timeout, watchdog, tratamento de backpressure, nenhuma alocação dinâmica desnecessária em caminhos críticos.
4. **Estado central definido:** máquinas de estados tipadas para \`idle/listening/thinking/talking/standby/error\`; transições e eventos versionados, S3 com fallback visual local.
5. **Contratos antes da integração:** API OtterPilot↔P4 e protocolo P4↔S3 possuem versões, schemas, testes, compatibilidade retroativa e mensagens de erro legíveis.
6. **Observabilidade e performance:** registrar por componente FPS p50/p95, tempo de render, CPU/tarefa quando mensurável, heap livre/min, largest block, PSRAM, perdas PCM, jitter, VAD/wake word, latências STT/LLM/TTS e primeira resposta audível. Comparar baseline e v2, não inventar números.
7. **Qualidade automatizada:** formatação, lint, testes unitários, integração e contratos, builds CI para P4/S3 e testes de backend. Hardware-in-the-loop na bancada; testes de falhas e recuperação.
8. **Segurança:** credenciais fora do Git, tokens de serviço com escopo, configuração NVS protegida conforme suporte da placa, autenticação OtterPilot, OTA assinada/verificada e rollback por partição, logs sem segredos.
9. **Arquitetura documentada:** READMEs instaláveis, ADRs para decisões relevantes, esquemas/pinout verificados, BOM mínimo, matriz de features, diagramas de sequência e troubleshooting.
10. **Sem otimizações não demonstradas:** antes/depois por medição. Não prometer que P4 processará a palavra personalizada \`LontraZ\` sem modelo e teste.

## 4. Contratos preliminares

### P4 ↔ S3 (UART 3,3 V para prova inicial)

- **Pinagem: verificar esquemático exato da Guition e da Waveshare S3 antes da fiação.** A Guition não compartilha necessariamente os mesmos GPIOs das Waveshare P4-WIFI6-DB. TX→RX cruzado, GND comum; alimentar as duas placas separadamente por USB durante testes. **Não unir 5 V ou 3,3 V** entre placas.
- Frames com versão, tipo, tamanho, sequência, integridade CRC, ACK/NACK onde necessário, timeout e ressincronização. Reservar prioridade para controle; áudio não pode bloquear \`SET_AVATAR_STATE\`.
- Eventos iniciais: \`HELLO/CAPABILITIES\`, \`HEARTBEAT\`, \`SET_AVATAR_STATE\`, \`TOUCH_EVENT\`, \`IMU_EVENT\`, \`AUDIO_START/FRAME/STOP\`, \`ERROR/COUNTERS\`.
- Captura PCM estéreo 16 kHz, 16-bit: 64 kB/s de payload; UART 921600 8N1 ≈92 kB/s brutos antes dos frames, portanto **projetar e medir taxas ≥2 Mbaud** ou considerar SPI se necessário. Não enviar framebuffers.
- Capacidade de buffers por cálculo de tempo de tolerância a jitter; timestamp de áudio, sequência e contagem de overflow.
- Não usar Wi-Fi da S3 como caminho obrigatório de controle após concluir a migração; manter recuperação bem definida.

### P4 ↔ OtterPilot

- Usar os contratos reais existentes no código: \`POST /api/copilot/voice\` (NDJSON streaming), \`GET /api/copilot/voice/persona\`, tokens com escopo. Conferir implementações; **o legado \`lontraz.py\` precisa ser localizado** para migração de \`/api/device/*\`.
- Separar os transportes de voz (captura/stream, STT remoto, resposta textual, TTS) e manter responsividade do avatar durante as chamadas.
- Áudio de reprodução e AEC: **decisão pendente baseada em teste**. Se o alto-falante migrar ao P4, providenciar referência sincronizada de playback para AEC/barge-in; não supor que o ES7210 da S3 fornece referência válida do novo alto-falante.
- Implementar OTA coordenado porém **independente por chip**, com compatibilidade de protocolo no upgrade/rollback.

## 5. Execução nas cinco etapas combinadas

### 1. Reorganização do repositório

**Meta:** estabelecer a base técnica v2, não apenas mudar nomes de diretórios.

- Inventariar arquivos/repositórios/branches, dependências, código duplicado, legado, segredos, build e runtime.
- Localizar o firmware S3 original e \`lontraz.py\` antes de declarar inventário completo. Registrar riscos e componentes a **preservar, portar, refatorar ou substituir** com justificativa.
- Definir diagramas de componentes, boundaries, interfaces públicas, matriz de responsabilidades, diretórios e ADRs. Criar os três novos repositórios **privados**, preservar histórico do backend e fontes originais como referência.
- **ATENÇÃO**: \`tools/split_lontraz_repos.ps1\` é apenas ferramenta de bootstrap/migração de histórico. **Não executar \`-Apply\` automaticamente**: primeiro revisar o desenho v2, segurança de histórico, origem real dos códigos e o plano de commits. O script não implementa a arquitetura v2.
- Criar scaffolds compiláveis mínimos somente onde servirem como novos componentes, sem mascarar falta do firmware original.
- Adicionar padrões de código, README, contribuições, .gitignore, CI base, testes e perfil de hardware, com decisões documentadas.
- **Aceite:** repositórios versionados, mapa de migração claro, fontes reais localizadas (ou lacuna demonstrada), ambiente reproduzível, baseline preservado e aprovação das interfaces.

### 2. Testes de conectividade entre as placas

**Meta:** uma conexão robusta e instrumentada antes de distribuir a inteligência.

- Guition P4+C6 ↔ Waveshare S3 AMOLED existente. Confirmar pinout por esquema, usar UART dedicada 3,3 V e GND comum, conexões seguras.
- Implementar primeiro \`HELLO\`, comandos de avatar, heartbeat e eventos de touch/IMU, com CRC/versão/timeout e reconexão.
- Transmitir áudio de **dois microfones continuamente**, inicialmente com gravação e checksum no P4; testar mono vs estéreo, 16 kHz e áudio real. Dimensionar buffers e testar com animações.
- Benchmarks de FPS/jitter/CPU/heap/PSRAM/erros de UART, resets de cada placa, áudio ininterrupto e fallback.
- **Aceite:** comandos e eventos confiáveis, áudio sem perda sustentada, nenhum travamento do avatar, métricas e logs reproduzíveis. Se a UART não sustentar áudio, reprojetar transporte com evidência, sem insistir por preferência.

### 3. Planejamento da migração S3 + P4

**Meta:** fechar desenhos e critérios de validação para migração total.

- Formalizar ADRs de pipeline completo: microfones ES7210→I²S/DMA S3→P4 AFE/WakeNet/VAD→STT→OtterPilot/Qwen→TTS→amplificador; onde ficam codec de saída e AEC.
- Confirmar slots/taxa TDM/I²S lendo o firmware original; converter corretamente para o formato esperado pelo AFE. Verificar recursos do ESP-SR para o ESP32-P4/C6 e modelo de wake word português/personalizado; palavra padrão até treinamento validado.
- Definir gerenciamento de energia/standby, Wi-Fi/provisioning, mDNS, OTA, rollback, watchdog, recovery, endpoint de dispositivo, telemetria/dashboard e especificação de estado do avatar.
- Definir compatibilidade de protocolo entre firmwares e versão do backend; contratos, testes HIL, cenários de falha e linha-base de comparação.
- **Aceite:** especificação implementável com pinagens e perfis reais, testes/limites definidos e dependências sem ambiguidade.

### 4. Migração total

**Meta:** implementar v2 real, não uma maquete.

- Reestruturar e integrar módulos aproveitáveis do código existente; reescrever exclusivamente os que comprometem limites arquiteturais e desempenho.
- S3 implementa interface visual independente, entradas físicas locais, captura contínua dos dois microfones, protocolo e monitoramento; avatar e áudio não bloqueiam um ao outro.
- P4 implementa streaming PCM, AFE/WakeNet/VAD, máquinas de estados, integração segura com OtterPilot, canal de voz, gerenciamento de rede, telemetria e OTA.
- OtterPilot implementa/adapta registry de dispositivos, endpoints de telemetria, dashboard central e integração da LontraZ sem regressões em HA/Proxmox/Frigate/LLM.
- OTA independente de cada placa, instalação em ordem segura, rollback e compatibilidade de protocolos. Preservar expressões, personas, TTS, vozes e dados/configs históricos.
- **Aceite:** ambos firmwares compilam e executam, serviço do OtterPilot testado, pipeline ponta a ponta, recursos atuais preservados, regressão automatizada e rollback demonstrado.

### 5. Resolução de problemas

**Meta:** robustez e performance contínuas, não só "passou no boot".

- Stress e soak test com avatar animando, dois mics contínuos, WakeNet/VAD, touch, reconexões, OTA e diálogo.
- Injetar perdas UART, boot em ordem invertida, frame truncado/CRC ruim, falta de Wi-Fi, P4 desconectado, servidor offline, buffers cheios e falha de atualização.
- Comparar desempenho real com baseline; otimizar somente gargalos medidos, registrar trade-offs e atualizar ADRs.
- **Aceite:** relatórios de FPS, latência p95, áudio e consumo, runbooks de diagnóstico, falhas tratadas e release \`v2.0.0\` reproduzível quando as evidências sustentarem.

## 6. Fluxo de execução e reporte para Claude

- Trabalho no próprio repositório/host correto; confirmar contexto antes de comandos destrutivos.
- Commits pequenos e testáveis por responsabilidade; branches e PRs; revisão para merge; preservar produção até migração.
- Não substituir arquivos funcionais por versões mínimas vazias; não apagar assets. Para testes faltando hardware, registrar \`não executado\` e fornecer comando, nunca inventar sucesso.
- Reportar em português de forma **objetiva**: \`mudanças\`, \`arquivos\`, \`testes executados e resultado\`, \`métricas\`, \`bloqueios\`, \`próxima ação\`. Sem textos promocionais ou longos relatórios em cada interação.
- Pode seguir autonomamente dentro da etapa e produzir PRs; exigir validação técnica para gravações, pinagem e mudanças de produção com risco irreversível.
