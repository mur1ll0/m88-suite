# M88 Suite — Android

App de controle do óculos M88 com o **firmware de fábrica** (Android 13+).

## Instalar
APK de teste: `app/build/outputs/apk/debug/app-debug.apk`
```
adb install -r app/build/outputs/apk/debug/app-debug.apk
```
Compilar: `gradlew.bat :app:assembleDebug` · testes do núcleo: `gradlew.bat :core:test`.

Na primeira abertura o app pede Bluetooth e "dispositivos Wi‑Fi próximos". Ao ligar vídeo ou
sincronizar, o Android pergunta se pode conectar na rede **M88-522B** — confirme. Só os sockets do
óculos usam essa rede; o resto do celular continua com internet.

## Telas
| Aba | O que faz |
|---|---|
| Painel | Bluetooth, bateria, Wi‑Fi, câmera, nº de arquivos, estado; conectar e reiniciar o óculos |
| Câmera | Vídeo ao vivo (H.264/UDP decodificado por hardware, ou JPEG) com fps e banda |
| Mídia | Copia fotos/vídeos novos para a galeria (Imagens/M88, Filmes/M88) |
| Mais | Áudio (headset Bluetooth do sistema), eventos de botões, informações de firmware |

Mesma lógica de reconexão do app Windows: BLE com backoff; vídeo congelado → reinicia o óculos e
retoma (até 3 vezes). Limitação do Android: apps não podem publicar uma "câmera virtual" para outros
apps sem root, então a câmera do óculos é vista dentro do app.

## Estrutura
- `:core` — Kotlin puro: M88P, BLE de fábrica, doorbell, montagem de quadros, SPS/PPS, backoff
  (testado contra `../protocol/vectors.json`).
- `:app` — `device/` (GATT, Wi‑Fi, vídeo, FTP, DeviceManager) e `ui/` (Compose).
