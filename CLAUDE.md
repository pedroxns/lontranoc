# Claude handoff — LontraZ 2.0

## Objective
Split the projects safely, then build S3↔P4 connectivity and complete the staged migration, **without rewriting working firmware or breaking the OtterPilot production runtime**.

Read **docs/LONTRAZ_V2_REPOSITORIES.md** first; it is the authoritative technical handoff. The only five macro stages are:
1. Reorganização do repositório
2. Testes de conectividade entre as placas
3. Planejamento da migração S3 + P4
4. Migração total
5. Resolução de problemas

## Verified GitHub sources
- `pedroxns/lontranoc`, **refactor/otterpilot**, is the actual OtterPilot backend. `main` is outdated.
- `pedroxns/tela-esp32p4---rack` is an **older rack dashboard** for Guition JC-ESP32P4-M3-DEV, P4+C6. Reference BSP only.
- Current Waveshare ESP32-S3-Touch-AMOLED-1.75 firmware and `lontraz.py` are **not found** in the public repository branches scanned. Locate the current authoritative local sources before importing or changing them.
- GitHub PR #3 holds the migration documentation and script. This branch is NOT proof that all three destination repositories already exist.

## Immediate work: repository split
1. On a workstation with `git`, `gh`, and SSH GitHub permissions, inspect `tools/split_lontraz_repos.ps1` and run without flags for preflight. `-Apply` creates **private** `pedroxns/otterpilot`, `pedroxns/lontraz-display-s3`, and `pedroxns/lontraz-core-p4`. It aborts if a destination already exists, to avoid overwrites.
2. Check for credentials or accidentally tracked runtime configuration **including historical commits**, not only current files, before exposing any repository publicly.
3. Import actual S3 source; do not replace it with generated scaffolding. Trace historical Guition source and preserve it separately.
4. Verify builds and register exact source SHAs, toolchain versions, submodules, partitions, and hardware pinouts.
5. Do not delete old repositories or change production deployments during split.

## Hardware boundary
- S3: AMOLED CO5300 466×466, CST9217 touch, QMI8658 IMU, ES7210 dual microphones via I2S/DMA; graphics and microphone capture.
- Guition P4 + C6: receive two-channel PCM, run WakeNet/VAD/AFE, own the network/LLM coordination, send avatar state events, track heartbeat.
- Initial interconnect: UART 3.3V TX/RX crossed + common GND. **Pin numbers must be verified against Guition schematic and S3 exact board revision**, not inferred from the unrelated Waveshare P4-WIFI6-DB pinout.
- Keep both boards separately powered by USB-C for bench testing; do not short power rails. Do not claim WakeNet recognizes custom "LontraZ" until validated.

## Reporting
In Portuguese, return only: concrete changed files, reproducible commands, measured results, blockers, and the next action. State plainly if a repository/firmware is still missing.
