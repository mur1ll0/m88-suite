# M88 Suite — Android

App de controle do óculos M88 com o **firmware de fábrica** (Android 13+).

## Instalar
```
adb install -r app/build/outputs/apk/release/app-release.apk
```
Se um APK de debug estiver instalado, desinstale antes (assinaturas diferentes).

## Compilar
- Testes do núcleo: `gradlew.bat :core:test`
- Debug: `gradlew.bat :app:assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk`
- Release (R8 + assinatura): `gradlew.bat :app:assembleRelease` → `app/build/outputs/apk/release/app-release.apk`

A assinatura de release usa `android/keystore.properties`, que fica **fora do git**:
```
storeFile=keystore/m88suite-release.jks
storePassword=...
keyAlias=m88suite
keyPassword=...
```
Sem esse arquivo o release é gerado sem assinatura. Guarde uma cópia da chave (`keystore/*.jks`) e do
`keystore.properties`: sem eles, versões futuras não conseguem atualizar o app instalado.

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

## Problemas conhecidos

**"O Bluetooth do celular está sem vagas para conexões"** — o Android aceita no máximo 32 clientes
Bluetooth LE ao mesmo tempo, e alguns apps vazam esses registros até esgotar o limite (no aparelho de
testes, o app da operadora Claro, `com.nvt.cs`, ocupava 29 vagas). Nenhum app consegue se conectar a
dispositivos BLE enquanto isso dura.

1. Retire a permissão **Dispositivos próximos** do app que está vazando
   (Configurações → Apps → <app> → Permissões).
2. **Reinicie o celular.** Desligar e ligar o Bluetooth só resolve se a "Busca por Bluetooth"
   (Configurações → Localização → Serviços de localização) estiver desativada; com ela ativada a
   parte BLE continua ligada e as vagas presas sobrevivem.

Para descobrir o app culpado (com o celular em depuração USB):
```
adb shell dumpsys bluetooth_manager | grep "appName:" | sort | uniq -c | sort -rn
```

**O vídeo ou a sincronização não começam** — na primeira vez o Android mostra o diálogo
"Conectar ao dispositivo M88-522B"; é preciso tocar em **Conectar**. Se o diálogo sumir (por exemplo,
ao trocar de app), espere o botão voltar e tente de novo.

## Estrutura
- `:core` — Kotlin puro: M88P, BLE de fábrica, doorbell, montagem de quadros, SPS/PPS, backoff
  (testado contra `../protocol/vectors.json`).
- `:app` — `device/` (GATT, Wi‑Fi, vídeo, FTP, DeviceManager) e `ui/` (Compose).
