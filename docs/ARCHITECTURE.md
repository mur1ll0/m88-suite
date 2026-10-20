# Arquitetura — M88 Suite

## Objetivo

Controlar o óculos M88 (SoC Beken BK7258) a partir de Windows e Android: câmera como webcam,
áudio (fone/microfone), fotos e vídeos com sincronização automática, configuração de botões,
atualização de firmware e telemetria (bateria, LED/lanterna, câmera, Wi‑Fi, BT).

## Visão geral

```
┌──────────────────────── Óculos M88 (BK7258) ────────────────────────┐
│ Firmware de fábrica (V191)          │ Firmware M88 Suite (futuro)    │
│  • BLE 0x54 (estado, AP, mídia)     │  • BLE GATT "M88P" (controle)  │
│  • BLE boarding fa00 (serviço vídeo)│  • TCP 7200 controle M88P      │
│  • TCP 7100/7150, UDP 7180 (vídeo)  │  • UDP 7280 vídeo (H.264+FEC)  │
│  • FTP 21 (mídia)                   │  • USB: CDC (controle) + UVC/UAC│
│  • BT clássico A2DP/HFP (áudio)     │  • BT clássico A2DP/HFP        │
└───────────────────────────┬─────────┴──────────────┬─────────────────┘
                            │                        │
                 ┌──────────▼─────────┐   ┌──────────▼─────────┐
                 │ Driver "stock"     │   │ Driver "m88p"      │
                 └──────────┬─────────┘   └──────────┬─────────┘
                            └────────┬───────────────┘
                          Interface única `Device` (capacidades)
                 ┌───────────────────┴───────────────────┐
          Windows (Python + PySide6)              Android (Kotlin + Compose)
```

A interface `Device` expõe **capacidades** (ex.: `camera.stream`, `buttons.remap`, `ota`).
O driver *stock* implementa o que o firmware de fábrica permite; o driver *m88p* implementa o
protocolo próprio. A UI só mostra o que o dispositivo conectado suporta. Assim os apps são úteis
**hoje** e ganham recursos quando o firmware novo for instalado, sem reescrever a UI.

## Escolhas de tecnologia

| Parte | Tecnologia | Motivo |
|---|---|---|
| Firmware | C sobre `bekencorp/bk_avdk` (FreeRTOS, BK7258) | SDK oficial do chip; contém doorbell, H.264/JPEG HW, BLE, Wi‑Fi, USB (CherryUSB UVC/UAC/CDC) |
| Protocolo no firmware | componente C portável `m88proto` (sem dependência do SDK) | testável no PC (Docker gcc) |
| Windows | Python 3.13 + PySide6 (Qt) | BLE nativo via `bleak`/WinRT, decodificação H.264 com PyAV, UI moderna; já validado com o óculos |
| Webcam no Windows | `pyvirtualcam` (backend OBS Virtual Camera) | aparece como câmera em Meet/Zoom/Teams |
| Android | Kotlin + Jetpack Compose, módulo `:core` em Kotlin puro | stack do app existente; `:core` testável na JVM |
| Contrato entre implementações | `protocol/vectors.json` | mesmos vetores de teste em C, Python e Kotlin |

## Áudio (fone e microfone)

O firmware de fábrica já é um headset Bluetooth clássico (A2DP + HFP, pilha EtherMind no BK7258).
Windows e Android usam o óculos como alto‑falante e microfone **pelo sistema operacional**, sem
driver próprio. Os apps de controle detectam o pareamento, mostram o estado e atalhos para as
configurações de áudio. Microfone via Wi‑Fi/USB (UAC) fica para o firmware M88 Suite.

## Robustez de conexão

Cada transporte (BLE, Wi‑Fi, vídeo) tem um *watchdog*:

- BLE caiu → reconecta com backoff (1, 2, 4, 8 s…), reassina notificações.
- Wi‑Fi do óculos caiu → reenvia `ap-on` pelo BLE e reassocia.
- Vídeo sem quadros por N s → no firmware de fábrica: desliga/liga a câmera; se falhar,
  reinicia o óculos (`setDeviceMode(3)`), porque o serviço de vídeo só abre uma vez por boot.

Os estados ficam visíveis na UI (Conectado / Reconectando / Desconectado) e os recursos retomam
sozinhos.

## Estrutura do repositório

```
docs/        arquitetura, protocolo, roadmap, hardware, firmware
protocol/    vetores de teste compartilhados
firmware/    componente m88proto (C), app bk_avdk, ferramentas (OTA pack/unpack)
desktop/     app Windows (Python/PySide6)
android/     app Android (Kotlin/Compose)
```
