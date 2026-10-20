# Atualização e backup de firmware — o que é possível

Investigação de 2026-10-20 sobre o firmware V189 (decifrado em `SmartGlassApp/firmware/oem/`),
o app WheatAI decompilado e a documentação do BK7258 (`bk_idk/docs/bk7258`).

## Resumo

| Caminho | Instalar firmware | Ler/salvar firmware atual | Evidência |
|---|---|---|---|
| **Bluetooth (SUOTA, como o WheatAI)** | ✅ provável, sem abrir o óculos | ❌ só grava | strings `BLE_SUOTA_OPCODE_START_UPDATE`, `OTA Download Finish,Now Reboot system`; serviço `fef5` anunciado |
| **USB‑C** | ❌ no firmware de fábrica | ❌ | único descritor USB = Mass Storage (classe 08/06/50); expõe só o cartão |
| **Arquivo no cartão** (`OTA_CHECK_TYPE_FILE`) | ❓ não confirmado | ❌ | o motor OTA aceita arquivo, mas não foi achado gatilho nem nome de arquivo |
| **FTP / Wi‑Fi** | ❌ | ❌ | FTP serve só o cartão |
| **Serial DL_UART0 (CP2102)** | ✅ (bootloader `l_bootloader`) | ✅ (BKFIL lê a flash inteira) | docs BK7258 |

**Backup da V191:** não encontrado em lugar nenhum. O servidor do fabricante
(`download.keeprapid.com/apps/smartband/keepfit/fwupdater/<idioma>/0039000B/update.json`) só oferece a
**V189** (`fwrelease/0039000B/V189.bin`, md5 `EBD9A90AEEC159AB1D6163DE77E1393B`); V190–V192 dão 404,
a listagem do diretório é proibida e o Internet Archive não tem cópias. Buscas na web sem resultado.
Única forma de salvar a V191: ler a flash pela serial.

**Restauração sem serial:** a V189 oficial pode ser reinstalada pelo Bluetooth **enquanto o firmware
instalado mantiver a atualização SUOTA funcionando**.

## Formato do pacote (V189.bin)

```
0x00  cabeçalho OEM 64 B: 70 61 FF FF | tamanho do corpo | crc32 do corpo | "1.226" | …
      | 0x00206B58 | … | produto 0x0039000B | 0x40 (tamanho do cabeçalho)
0x40  preenchimento FF
0xA4  cabeçalho RBL Beken (96 B): "RBL", algo 0x0102 (gzip + AES‑256‑CBC), partição "app",
      tamanho original 3 299 488, comprimido 2 124 496, crc32 do corpo, crc32 do cabeçalho
0x104 corpo: AES‑256‑CBC (chave "0123456789ABCDEF0123456789ABCDEF", IV "0123456789ABCDEF",
      padrão do SDK) sobre gzip da imagem "app" (base 0x02010000)
```
Nenhuma assinatura digital encontrada — só CRCs.

## Como a atualização acontece no aparelho

1. O app (WheatAI) envia `firmware.bin` por SUOTA (protocolo Dialog: `MEM_DEV`, `PATCH_LEN`,
   `PATCH_DATA` em blocos de 240 B + byte XOR no fim) no serviço `fef5`.
2. O firmware em execução grava o pacote na partição de download e confere CRC32/formato
   (`D[OTA]entry[%d] start check crc32…`).
3. Reinicia; o **`up_bootloader`** decifra/descomprime e copia para a partição `app`.

Consequências:
- Pacote corrompido na transmissão é rejeitado pela verificação (não deve brickar).
- **Firmware válido porém defeituoso** (não liga, ou liga sem BLE/OTA) **não tem volta pelo
  Bluetooth**: só pela serial. O bootloader não é tocado pela OTA, então a gravação pela serial
  continua disponível nesse caso (desde que secure boot esteja desligado, o que é coerente com o
  pacote sem assinatura, mas não foi verificado no eFuse).

## Regras para o firmware M88 Suite

1. Todo firmware nosso **mantém o serviço SUOTA `fef5` compatível** — sempre dá para voltar à V189.
2. Primeira gravação de teste = **reinstalar a V189 oficial** com a nossa ferramenta (valida a cadeia
   inteira sem código novo). Exige autorização explícita do usuário.
3. Bateria > 80 %, carregador na tomada (não no PC — USB conectada muda o modo do aparelho), óculos
   a < 1 m, nada mais usando o Bluetooth.
4. Antes do primeiro firmware próprio, ter um caminho de serial (ver abaixo).

## Serial na placa JY_5BG_V4

A placa tem pads dourados redondos perto do texto `JY_5BG_V4` e do botão. Eles **não têm legenda**;
podem ser UART, USB (D+/D‑) ou alimentação. Identificação com multímetro, óculos ligado:
- GND: continuidade com o negativo da bateria (medir desligado).
- TX do BK7258: ~3,3 V com oscilação no boot (log a 115200).
- RX: ~3,3 V estável.
- D+/D‑ do USB: continuidade com os pinos do conector USB‑C (descarta como UART).

Candidatos marcados em `docs/img/pads_candidatos.jpg`: pads **1–4** (dois pares de pontos de teste
redondos na lateral direita, ao lado do LED e do texto `JY_5BG_V4`) e pad **5** (isolado, perto da
antena). A foto não permite saber a função de cada um — não há legenda e as trilhas passam por baixo.

### Pinagem do chip (datasheet oficial)

Datasheet Beken **DS‑BK7258‑E13 V2.2**, tabela 3‑4 "BK7258QN6868 QFN68 Pin Descriptions"
(variante exata do óculos):

| Pino | Nome | Função |
|---|---|---|
| 41 | P10 | **DL_UART_RX** — gravação/serial (entrada do chip) |
| 42 | P11 | **DL_UART_TX** — gravação/serial (saída, log a 115200) |
| 29 | USB_DP | USB D+ |
| 30 | USB_DN | USB D− |
| 34 | CEN | chip enable (reset), ativo em alto |

QFN68 visto de cima com pino 1 no canto superior esquerdo: 1–17 lateral esquerda (descendo),
18–34 lateral de baixo, 35–51 lateral direita (subindo), 52–68 topo. Na foto, isso põe 41/42 na
lateral direita do chip e 29/30 na lateral de baixo — ver `docs/img/pads_pinagem_bk7258.jpg`.
A posição é **estimada**: confirmar a marca do pino 1 no chip.

**Método mais seguro:** óculos desligado, multímetro em continuidade, uma ponta em cada pad 1–4 e a
outra (ponta fina) encostada na lateral exposta dos pinos 41, 42, 29 e 30 do QFN. O pad que apitar
com o 42 é o TX; com o 41, o RX.

Roteiro com multímetro (anote o valor de cada pad 1–4):
1. **Desligado, modo continuidade:** ponta preta no negativo da bateria; teste 1–4. Algum com bipe = GND.
2. **Desligado, continuidade com o conector USB‑C:** se 2 pads tiverem continuidade com os pinos
   D+/D‑ do conector (A6/A7), esse par é USB — não é a serial.
3. **Ligado, tensão DC (preta no negativo da bateria):** o par restante deve dar ~3,3 V. Ligando o
   óculos e observando no primeiro segundo: o pad cuja tensão **oscila** durante o boot é o **TX**;
   o que fica **estável em ~3,3 V** é o **RX**.
4. Só então: CP2102 **RX → TX** do óculos e **GND → GND**; abrir o terminal a 115200 baud e ligar o
   óculos. Se aparecer texto, a identificação está certa.

Formas de conectar sem prática de micro‑solda:
- **Assistência técnica de celular**: soldar 3 fios finos (30 AWG) em pads é serviço rotineiro e barato.
- **Pontas pogo / garra de teste** apoiadas nos pads só durante a leitura.
- Fio esmaltado fino + fita Kapton para segurar enquanto lê o log/faz o backup.

Ligação: GND↔GND, RX do adaptador ↔ TX do óculos (primeiro só escutar), depois TX↔RX para o BKFIL.
**Nunca** ligar o VCC do adaptador.
