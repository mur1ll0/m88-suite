# Roadmap

Legenda: ✅ feito · 🟡 em andamento · ⬜ pendente · 🔒 exige hardware (UART/CP2102)

## Fase 1 — Apps funcionando com o firmware de fábrica
- ✅ Protocolos de fábrica documentados e validados no dispositivo (BLE 0x54, boarding, doorbell, FTP)
- ✅ App Windows: conexão BLE+Wi‑Fi, painel de estado, stream H.264/UDP, reconexão automática,
  sincronização de fotos, reinício remoto, webcam virtual (via OBS Virtual Camera)
- ✅ App Android: `:core` testado contra os vetores; GATT, Wi‑Fi, vídeo H.264 (MediaCodec), mídia, reconexão
- ✅ Formato do pacote OTA documentado (OEM + RBL Beken, chave padrão); ferramenta de empacotar: pendente

## Fase 2 — Base do firmware próprio
- 🔒 Backup completo da flash por UART (pré‑requisito para qualquer gravação) — pinagem e roteiro em `docs/FIRMWARE_UPDATE.md`
- 🔒 Log de boot: partições, secure boot, GPIOs (botões, LED, lanterna, sensor, áudio)
- ⬜ Compilar `bk_avdk` doorbell para BK7258 no Docker, sem alterações
- ⬜ Mapear pinagem da placa JY_5BG_V4 a partir do binário V189 + log de boot
- ⬜ Primeira imagem própria = doorbell oficial + ajustes de placa; gravar por UART (com backup)

## Fase 3 — Firmware M88 Suite
- ⬜ Componente C `m88proto` (frames, TLV, CRC, despacho) — referência pronta em Python e Kotlin, testada contra `protocol/vectors.json`
- ⬜ Serviço GATT M88P + TCP 7200
- ⬜ Vídeo: H.264 com bitrate/fps configuráveis, keyframe sob demanda, UDP com FEC
- ⬜ Wi‑Fi: desativar power‑save durante stream, canal fixo menos congestionado, potência TX máxima
- ⬜ Botões configuráveis (tabela gesto→ação em flash)
- ⬜ Telemetria (bateria, LED, lanterna, câmera, rádios) por evento
- ⬜ OTA pelo próprio protocolo (com verificação e rollback A/B)
- ⬜ USB: CDC (controle) + UVC (webcam) + UAC (microfone) — webcam sem depender do Wi‑Fi

## Limites conhecidos do hardware
- Sensor GC2145 (2 MP, DVP): qualidade boa só com luz; alvo realista 720p.
- Wi‑Fi 2.4 GHz, 1 antena de fio: alcance útil ~3 m medido; ver `docs/HARDWARE.md`.
- No firmware de fábrica, USB conectada bloqueia a câmera.
