# Protocolos

## 1. Firmware de fábrica (V189/V191) — validado em 2026-10-20

### BLE (serviço `000056ff`, TX `33f3` write, RX `33f4` notify)
Frame de 20 bytes `54 <cmd> <arg> 00…`.

| Cmd | Função | Resposta |
|---|---|---|
| `11` | estado do sistema | `54 12 <estado>` (bitmask 1 vídeo, 2 áudio, 4 IA, 8 transferência) |
| `13 01` | abrir Wi‑Fi AP `M88-522B` / `12345678` | `54 13 01`, depois `54 13 02 02` quando um cliente associa |
| `04 01` | estado Wi‑Fi | `54 04 02 C0 A8 30 01` (IP 192.168.48.1) |
| `05` | contagem de arquivos | `54 06 <qtd>` |
| `08` | scan Wi‑Fi | fragmentos de SSID |
| — | espontâneo | `0B <bateria %>`, `03/13 <epoch LE>` |

Reinício: `0E 12 34 56 78 9A BC DE F0` (setDeviceMode 3). **Nunca** enviar modo 1 (OTA)
ou 4 (`0E 12 34 12 34 12 34 12 34`, reset de fábrica).

### BLE boarding Beken (serviço `fa00`, escrita `ea02`, notify `ea01`)
`[opcode u16 LE][len u16 LE][dados]`. Usados: `03` serviço de vídeo UDP, `04` serviço de vídeo TCP.
O serviço de vídeo abre **uma vez por boot**.

### Vídeo (doorbell `bk_avdk`)
- TCP 7100 comandos; imagem TCP 7150 ou UDP 7180; áudio 7140/7170.
- Transporte `db_trans_head_t` (16 B, little‑endian): `magic F0D5 | flags(bit0=CRC) | ts u32 |
  seq u16 | len u16 | crc8 (init 0xFF) | 3 reservados`.
- Comando: `opcode u32 | param u32 | len u16 | payload`. Evento: `opcode u32 | status u8 |
  flags u16 | len u16 | dados`.
- `3` lista câmeras (`{"name":"DVP","id":"1"}`), `7` liga câmera (`param=1`, payload
  `w,h,fmt(0 JPEG/1 H.264),protocol,rotate` u16), `8` desliga.
- Pacote de imagem: transporte + `{id, eof, cnt, total}` + pedaço.
- UDP: o óculos envia para o endereço do último pacote recebido em 7180 (mandar "hello").

### Mídia
FTP 21, `bk7258` / `123456`, modo passivo. USB‑C: pen drive (bloqueia a câmera enquanto conectado).

## 2. M88P v1 — protocolo do firmware M88 Suite (proposto)

Mesmo formato em BLE (GATT), TCP 7200 e USB CDC.

### Frame
```
off  tam  campo
0    2    magic 0x4D 0x38 ("M8")
2    1    versão (1)
3    1    tipo: 0 REQ, 1 RSP, 2 EVT
4    2    seq (LE)  — RSP repete o seq do REQ
6    2    cmd (LE)
8    2    len (LE)  — tamanho do payload
10   len  payload: lista TLV {tag u8, len u8, valor}
10+len 2  CRC‑16/CCITT‑FALSE (LE) sobre bytes 0..10+len‑1
```
Em BLE o frame é fragmentado pelo MTU; o receptor remonta pelo `len`.

### Comandos
| cmd | nome | payload REQ | payload RSP |
|---|---|---|---|
| 0x0001 | GET_INFO | — | fw_version, hw, mac, capabilities |
| 0x0002 | GET_STATUS | — | battery, charging, led, flashlight, wifi, bt, camera, storage_free |
| 0x0003 | SET_CONFIG | tag/valor | status |
| 0x0010 | CAMERA_START | codec, width, height, fps, bitrate_kbps, transport | status, stream_port |
| 0x0011 | CAMERA_STOP | — | status |
| 0x0012 | CAMERA_KEYFRAME | — | status |
| 0x0020 | PHOTO | — | file |
| 0x0021 | RECORD_START / 0x0022 RECORD_STOP | — | file |
| 0x0030 | BUTTONS_GET / 0x0031 BUTTONS_SET | lista {gesto, ação} | status |
| 0x0040 | FILE_LIST / 0x0041 FILE_READ / 0x0042 FILE_DELETE | caminho, offset | dados |
| 0x0050 | OTA_BEGIN / 0x0051 OTA_DATA / 0x0052 OTA_END | tamanho, crc32 / offset, bloco | status |
| 0x0060 | AUDIO_ROUTE | entrada/saída | status |
| 0x00F0 | REBOOT | — | status |

Eventos (`tipo=2`): `0x8001 STATUS_CHANGED`, `0x8002 BUTTON`, `0x8003 MEDIA_ADDED`,
`0x8004 STREAM_STATS`, `0x80FF ERROR`.

### Tags TLV (subconjunto)
| tag | campo | tipo |
|---|---|---|
| 0x01 | battery | u8 % |
| 0x02 | charging | u8 bool |
| 0x03 | led | u8 |
| 0x04 | flashlight | u8 |
| 0x05 | wifi | u8 (0 off, 1 AP, 2 STA) |
| 0x06 | bt | u8 bits (1 BLE, 2 A2DP, 4 HFP) |
| 0x07 | camera | u8 (0 off, 1 stream, 2 gravando) |
| 0x10 | codec | u8 (0 JPEG, 1 H.264) |
| 0x11 | width | u16 |
| 0x12 | height | u16 |
| 0x13 | fps | u8 |
| 0x14 | bitrate_kbps | u16 |
| 0x15 | transport | u8 (0 UDP, 1 TCP, 2 USB) |
| 0x20 | status | u8 (0 ok) |
| 0x21 | fw_version | string |
| 0x30 | gesture | u8 (ver docs/FIRMWARE.md) |
| 0x31 | action | u8 |

### Vídeo M88P (UDP 7280)
`magic 'MV' | frame_id u16 | pkt_idx u16 | pkt_count u16 | flags u8 (bit0 keyframe, bit1 FEC)
| reserved u8 | dados`. FEC XOR a cada N pacotes; o receptor pede keyframe (CAMERA_KEYFRAME)
quando perde um quadro de referência.

Vetores de teste: `protocol/vectors.json`.
