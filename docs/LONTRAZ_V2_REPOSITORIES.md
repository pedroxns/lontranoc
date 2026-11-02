# LontraZ 2.0 — separação de repositórios e plano de migração

> Documento de handoff para Claude. **Não reescrever o sistema do zero.** Preservar os firmwares que já funcionam e o histórico Git. As cinco etapas abaixo são as **únicas etapas macro** do projeto.

## Fontes existentes verificadas

- Backend: [pedroxns/lontranoc](https://github.com/pedroxns/lontranoc), branch **refactor/otterpilot**. A branch main está defasada. Usar refactor/otterpilot como origem, não main.
- Projeto histórico da Guition: [pedroxns/tela-esp32p4---rack](https://github.com/pedroxns/tela-esp32p4---rack). É um monitor de rack para Guition JC-ESP32P4-M3-DEV (P4 + C6), **não** o firmware LontraZ P4. Não mover nem apagar.
- Firmware atual da Waveshare ESP32-S3-Touch-AMOLED-1.75 (sem -G): **origem ainda não localizada em um repositório público do usuário**. Solicitar ao operador/Codex a pasta local ou URL exata antes de importar. Jamais substituir esse firmware por exemplo vazio.
- O antigo backend de aparelho lontraz.py não está no repositório OtterPilot analisado; localizar sua origem local antes de declarar a integração concluída.

## Repositórios de destino

1. **pedroxns/otterpilot**: backend, APIs, persona, voz, histórico, telemetria, dashboard. Criar a partir do histórico da branch refactor/otterpilot; preservar árvore e histórico. NÃO apagar pedroxns/lontranoc.
2. **pedroxns/lontraz-display-s3**: firmware S3, display AMOLED CO5300/QSPI 466x466, LVGL/arte, touch CST9217, IMU QMI8658, captura de dois microfones ES7210 por I2S/DMA, telemetria do S3, cliente do protocolo S3↔P4. Importar o código real assim que for localizado; inicialmente o repositório pode conter apenas README.
3. **pedroxns/lontraz-core-p4**: firmware Guition P4 + C6, recepção PCM estéreo, filas/ring buffers, AFE/WakeNet/VAD, rede, conexão OtterPilot, API de estados do avatar, monitoramento, atualização OTA e gerenciamento. Não transplantar o firmware de monitor de rack inteiro; usar apenas como referência de BSP/pinagem verificada.

Manter o **contrato UART versionado no repositório lontraz-core-p4**, com header/IDL compartilhado importado ou gerado no S3; evitar um quarto repositório até surgir necessidade real.

## As cinco etapas acordadas

### 1. Reorganização do repositório

- Criar os três repositórios de destino. Script auxiliar em tools/split_lontraz_repos.ps1; requer Git e GitHub CLI com permissão de criar repositórios.
- Migrar o backend com histórico de refactor/otterpilot → otterpilot/main, **sem force push**.
- Criar scaffolds não-funcionais S3/P4, claramente identificados. Não declarar "firmware migrado" até importar fonte original.
- Localizar origem real do S3 (e do backend lontraz.py, se aplicável), importar sem perder referências, licenças e histórico possível.
- Verificar ausência de credenciais, segredos, sdkconfig local e binários grandes antes de publicar código.
- Atualizar documentação de dependências entre projetos. Nenhuma modificação do deploy de produção nesta etapa.
- Gate: 3 repos criados, backend completo versionado, S3/P4 identificados com origem e build conhecido ou lacuna explicitamente registrada.

### 2. Testes de conectividade entre as placas

- Hardware inicial **Guition JC-ESP32P4-M3-DEV** + **Waveshare ESP32-S3-Touch-AMOLED-1.75 já montada**.
- Revisar o esquemático e pinout exatos, especialmente do conector JP1 da Guition; **não aceitar GPIOs presumidos da Waveshare P4-WIFI6-DB** para a Guition. Escolher UART TX/RX livres nos dois lados, 3,3 V, GND comum. TX→RX cruzado. Alimentar inicialmente cada placa pelo próprio USB-C; **não interligar 5 V/3V3 entre placas**.
- UART bidirecional com pacotes versionados e limites explícitos; começar em 115200 para comandos; medir e subir até taxa que suporte PCM, idealmente ≥2 Mbaud se estabilidade elétrica e firmware permitirem.
- Mensagens mínimas: HELLO/capabilities, HEARTBEAT, SET_AVATAR_STATE, TOUCH_EVENT, IMU_EVENT, AUDIO_START/FRAME/STOP, ERROR/COUNTERS. CRC e sequence number. Separar planos de controle e áudio com prioridades e backpressure.
- Primeira prova sem áudio: pelo P4 alternar estados do rosto; touch e IMU do S3 retornam eventos; reiniciar cada placa e validar reconexão.
- Segunda prova: S3 captura dois microfones via I2S/DMA e envia PCM ininterruptamente ao P4. **PCM mono 16 kHz/16-bit = 32 kB/s; estéreo = 64 kB/s**. UART 921600 8N1 ≈92 kB/s brutos, margem limitada. Preferir ≥2 Mbaud ou interface mais rápida se medições indicarem perda. Não transmitir buffers de framebuffer.
- Medir perda de frames, jitter, overflow, latência ponta-a-ponta, uso CPU, heap e PSRAM, FPS com/sem stream.
- Gate: estabilidade real com avatar ativo e áudio estéreo, sem underruns/overruns persistentes.

### 3. Planejamento de migração S3 + P4

- P4: cérebro embarcado, conexão com OtterPilot, WakeNet/VAD/AFE, ring buffer e estados de conversação; S3: renderização, toque/IMU e **somente captura DMA** dos microfones enquanto não migrados.
- Confirmar topologia de áudio do S3 (ES7210, slots, canais, taxa, conversão 24→16 kHz se necessário) lendo firmware real e datasheets. Não assumir formato de saída TDM.
- Definir referência de reprodução para AEC/barge-in: se alto-falante for no P4, a referência deve vir do fluxo de reprodução do P4; sincronismo exige projeto específico.
- Validar suporte efetivo da versão selecionada do ESP-SR ao P4 e à palavra de ativação "LontraZ"; **não presumir modelo personalizado disponível**. Usar palavra suportada durante prova inicial.
- Preservar endpoints e personas atuais em OtterPilot (POST /api/copilot/voice, GET /api/copilot/voice/persona), com token de serviço; localizar lontraz.py legado antes de desligar.
- Definir versões de firmware, rollback, watchdog, boot e modo degradado se um chip falhar.
- Gate: arquitetura e contrato aprovados por revisão técnica, com documentação de pinagem real, perfis de CPU/RAM e testes reproduzíveis.

### 4. Migração total

- Substituir controle por Wi-Fi direto do S3 pelo fluxo P4→UART→S3 quando validado, preservando modo de recuperação.
- Implementar S3 como UI independente com animações locais; comandos pequenos, nenhuma transmissão de vídeo/framebuffer.
- Implementar P4 como receptor de PCM e processador wake word/VAD; encaminhar fala para STT remoto, OtterPilot (Qwen), TTS e reprodução. Escolher local do alto-falante após testes. Preservar o áudio atual até novo áudio comprovadamente melhor.
- OTA independente para S3 e P4, sem aplicar dois firmwares simultaneamente; telemetria separada com agregação por dispositivo.
- Garantir usuário não perca a configuração original, assets/expressões, integração HA, personas e fontes de voz.
- Gate: build reproduzível dos dois firmwares, pipeline completo, recuperação a falha e upgrade/rollback validados.

### 5. Resolução de problemas

- Testar boot em ordem inversa, perda UART, reboot no meio do áudio, perda Wi-Fi, token inválido, ocupação do ring buffer, fragmentação de heap e reboot sob áudio+FPS.
- Soak test em operação contínua com wake word, tela em standby/despertar, touch, telemetria e perguntas ao OtterPilot.
- Registrar medições **antes/depois**: FPS p50/p95, memória mínima, pior latência, perdas UART, detecções e falsos positivos de wake word, tempo de primeira resposta audível.
- Entregar relatório final e atualizar documentação; manter ponto de rollback operacional.

## Política de mudanças

- Trabalho em branches/PRs; não realizar push direto em main ou refactor/otterpilot existente.
- Não realizar force push, delete, rename destrutivo, nem mexer no host/serviços operacionais sem plano de rollback.
- Não substituir projeto real por scaffolding.
- Antes de programar GPIO, checar hardware exato; a Guition e a Waveshare ESP32-P4-WIFI6-DB **não são a mesma placa**.
- Em cada etapa, retornar somente: arquivos alterados, comandos para testar, resultado real, bloqueios e próxima ação. Evitar discussões genéricas.
