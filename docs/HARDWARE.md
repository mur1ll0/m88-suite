# Hardware — melhorias práticas

## 1. Lado do PC (mais fácil e provavelmente o maior ganho)

A placa do PC (MediaTek Wi‑Fi 6/6E + Bluetooth) usa **o mesmo rádio de 2.4 GHz para Wi‑Fi e
Bluetooth**. Durante o stream o PC mantém BLE com o óculos e Wi‑Fi com o AP dele ao mesmo tempo,
e o rádio alterna entre os dois (coexistência), o que causa perda de pacotes.

- **Use um adaptador Wi‑Fi USB 2.4 GHz separado** (de preferência com antena externa) só para a
  rede `M88-522B`, ou um adaptador **Bluetooth USB** separado. Barato e sem risco.
- Deixe o adaptador/antena do PC com visada para o óculos e longe de portas USB 3.0
  (que geram ruído em 2.4 GHz).

## 2. Antena do óculos (o fio de cobre na haste)

O fio soldado na placa e que corre pela haste é, muito provavelmente, a antena monopolo de 2.4 GHz
(compartilhada por Wi‑Fi e Bluetooth).

Referência: um monopolo de ¼ de onda em 2.45 GHz mede **≈ 30 mm** no ar (λ/4 = 30,6 mm);
dentro de plástico o comprimento ideal fica um pouco menor (≈ 27–29 mm).

Cuidados que costumam ajudar (sem garantia, faça com o óculos desligado):
- **Não deixe o fio enrolado, dobrado em "U" ou encostado na bateria** ou em partes metálicas
  (dobradiça, parafusos, blindagem). Metal e a bateria desafinam e absorvem o sinal.
- Mantenha o fio **reto**, ao longo da haste, o mais longe possível da bateria e da placa.
- Meça o comprimento livre (do ponto de solda até a ponta). Se for muito diferente de ~30 mm,
  anote antes de qualquer mudança — cortar é irreversível; prefira primeiro só reposicionar.
- Ao usar no rosto, a cabeça absorve 2.4 GHz: o PC do lado da haste com a antena funciona melhor.

Medir antes e depois: rode `m88ctl.py live --fresh --udp --h264 --seconds 30` na mesma posição e
compare fps e "descartados".

## 3. Firmware (fase 3)

Ganhos esperados com firmware próprio: desligar power‑save do Wi‑Fi durante o stream, fixar canal
pouco usado, potência TX máxima, bitrate adaptativo e FEC. Webcam por **USB (UVC)** elimina o
rádio do caminho.
