# Claude Code — instruções do projeto LontraZ v2 + OtterPilot

> **Instrução prioritária (02/11/2026):** construir a **LontraZ v2 + OtterPilot** com arquitetura modular, interfaces explícitas, testes e desempenho mensurado. **Substitui** a instrução anterior de apenas dividir repositórios ou evitar toda reescrita.

## Missão

Atue como arquiteto de software e engenheiro embarcado sênior responsável por **desenhar, refatorar, implementar, testar e integrar** a v2, com foco em qualidade, latência baixa, responsividade de interface, confiabilidade e manutenção.

Faça **refatoração profunda e reescrita seletiva** onde a arquitetura atual exigir. Preserve e adapte o que já está validado: drivers, assets, expressões do avatar, integrações, personas, voz e funções operacionais. **Não faça uma reescrita cega**, não recrie um sistema que funcione sem avaliar sua qualidade, não mantenha código ruim por apego ao legado.

Leia primeiro: `docs/LONTRAZ_V2_REPOSITORIES.md`. Esse documento define a arquitetura-alvo, contratos, testes, salvaguardas e critérios de aceite. Em caso de conflito, prevalece a decisão mais recente de **LontraZ v2 + OtterPilot**, não os textos anteriores de split-only.

## Escopo: uma plataforma, três repositórios

1. `pedroxns/otterpilot`: backend Python/FastAPI, IA via Ollama, personas, APIs/streaming, observabilidade, serviços de voz, dashboard e integrações.
2. `pedroxns/lontraz-display-s3`: firmware ESP32-S3 da Waveshare AMOLED 1.75, rosto e animações, touch, IMU, captura I²S/DMA dos dois microfones e link serial.
3. `pedroxns/lontraz-core-p4`: firmware Guition ESP32-P4 + C6, controle central embarcado, processamento PCM, AFE/WakeNet/VAD, rede e cliente OtterPilot, OTA e telemetria.

Definir contratos versionados entre os componentes; protocolo inicialmente no repo P4, reutilizado pelo S3 com versão fixada. Não criar serviços/repos extras sem necessidade demonstrável.

## As CINCO etapas macro, nesta ordem

1. **Reorganização do repositório:** inventário e recuperação das fontes reais, arquitetura-alvo/ADRs, classificação por preservar/portar/refatorar/substituir, criação dos repositórios, histórico e CI/testes mínimos.
2. **Testes de conectividade entre as placas:** UART 3,3 V bidirecional, comando de avatar/touch/IMU/heartbeat, integridade, fallback e streaming contínuo dos dois microfones com benchmark real.
3. **Planejamento da migração S3 + P4:** fechar interfaces, pipeline de voz e estados, referência AEC, OTA, compatibilidade de versões, segurança, testes e tolerância a falhas.
4. **Migração total:** reconstruir o necessário com módulos novos, aproveitar código validado, integrar S3/P4/OtterPilot, garantir regressões e recuperação.
5. **Resolução de problemas:** testes sob carga, falha/reconexão, OTA/rollback, otimização medida, documentação e release.

Não inventar etapas macro extras; pode decompor tecnicamente as tarefas dentro de cada uma. **Não pare a implementação apenas para gerar longas propostas teóricas**: produza código e testes concretos quando o ambiente permitir.

## Fontes e histórico conhecidos

- Backend: `pedroxns/lontranoc`, branch **refactor/otterpilot** (a `main` é antiga). Fonte atual do OtterPilot; deve ser preservada até migração validada.
- Projeto Guition anterior: `pedroxns/tela-esp32p4---rack`, monitor de rack JC-ESP32P4-M3-DEV P4+C6. **Referência de hardware/driver**, não substituto do novo firmware.
- Firmware da Waveshare ESP32-S3-Touch-AMOLED-1.75 (sem -G) e serviço legado `lontraz.py`: **ainda não localizados no GitHub examinado**. Investigar pasta local, backups e eventuais remotes antes de importar. Não declarar integração completa sem encontrá-los.
- PR #3 é preparação da arquitetura e script; os três repositórios ainda **não estão comprovadamente criados**.
- `tools/split_lontraz_repos.ps1` é ferramenta de bootstrap/histórico, não migração funcional v2. **Revisar plano e segredos antes de usar `-Apply`**. Não fazer push/merge/deploy de produção desnecessários.

## Diretrizes de implementação

- Firmware: ESP-IDF + FreeRTOS, componentes separados por BSP, link, drivers, máquina de estados, renderização, DMA, pipeline de áudio, OTA e telemetria. Definir prioridades, afinidade, buffers, watchdog, tempo de execução e não bloquear avatar com rede/IA.
- P4: receber PCM dos dois mics capturados no S3; usar ESP-SR/AFE/WakeNet/VAD somente após conferir versão e compatibilidade real. A palavra personalizada "LontraZ" exige validação; usar modelo suportado em prova inicial.
- S3: manter AMOLED redonda CO5300/QSPI, CST9217, QMI8658, ES7210 e assets existentes; reações locais sem dependência de servidor. Tela em standby pode apagar, mas não assumir deep sleep com microfones transmitindo.
- Hardware: pinagem **da Guition específica**, nunca copiar cegamente pinos da Waveshare P4-WIFI6-DB. UART 3,3 V TX/RX cruzados + GND comum, alimentação inicial individual por USB; nunca unir trilhos de alimentação sem projeto elétrico.
- Contratos: API OtterPilot↔P4 e protocolo P4↔S3 versionados, schemas, timeouts, CRC, sequence numbers, backpressure, heartbeat, compatibilidade retroativa, recovery.
- Backend: preservar APIs `POST /api/copilot/voice` (streaming NDJSON) e `GET /api/copilot/voice/persona` conforme contrato existente, exceto migração versionada e coberta por testes. Evitar regressões de Home Assistant, Frigate, Proxmox.
- Qualidade: princípios SOLID/KISS/DRY quando apropriados, tipagem, testes unitários/contratos/integração, CI, lint, format, documentação de decisões (ADR) e nenhuma dependência nova sem justificativa.
- Desempenho: estabelecer baseline e aferir FPS p50/p95, tempo de render, RAM/PSRAM disponível, CPU por tarefa quando possível, perdas de áudio, jitter, wake word e latências STT/LLM/TTS. **Não inventar resultados.**
- Segurança e operações: repo privado inicialmente, remover segredos de código e revisar histórico, tokens com escopo, OTA segura com rollback, operações reversíveis, PRs pequenos, backup, sem `force push`.

## Autonomia e reportes

Execute as tarefas reais dentro da etapa atual sem pedir aprovação a cada microdecisão técnica. Pare somente diante de risco de sobrescrever fonte, gravar hardware, alterar produção, exposição de segredos ou dependência essencial não localizada.

Responda em português, conciso, com:
- **Alterado:** arquivos/commits/PRs concretos.
- **Validado:** testes executados, resultado e métricas.
- **Pendente/bloqueado:** o que falta, sem presumir.
- **Próxima ação:** comando/arquivo/host exato.

Não use textos genéricos, não diga que fez o que não foi executado e não substitua firmware funcional por código de exemplo.
