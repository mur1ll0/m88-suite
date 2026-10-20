# M88 Suite — Windows

App de controle do óculos M88 com o **firmware de fábrica**.

## Usar

- **Versão pronta:** extraia `M88Suite-<versão>-windows.zip` e abra `M88Suite.exe`.
- **Do código‑fonte:** dois cliques em `M88Suite.bat` (na primeira vez cria o ambiente e instala as
  dependências; requer Python 3.11+).

Requisitos: Windows 10/11 com Bluetooth LE e Wi‑Fi ligados; óculos ligado e **sem** o Bluetooth do
celular conectado nele. Webcam virtual: [OBS Studio](https://obsproject.com/) instalado (fechado).

## Páginas

| Página | O que faz |
|---|---|
| Painel | Bluetooth, bateria, Wi‑Fi, câmera, nº de arquivos, estado do óculos; conectar/desconectar; reiniciar o óculos |
| Câmera | Vídeo ao vivo (H.264/UDP recomendado), fps/banda/descartes, webcam virtual (OBS Virtual Camera) |
| Fotos e vídeos | Copia os arquivos novos do cartão para `Imagens\M88` (opcional: automático ao conectar) |
| Áudio | Atalhos para usar o óculos como fone/microfone Bluetooth do Windows |
| Botões / Firmware | Informações; remapeamento e atualização chegam com o firmware M88 Suite |
| Configurações | Endereço Bluetooth do óculos, conectar ao abrir |

Reconexão: o Bluetooth reconecta sozinho (espera crescente de 1 a 20 s). Se o vídeo parar por 4 s,
o app reinicia o óculos e retoma o stream (até 3 tentativas).

Logs e autoteste: `%USERPROFILE%\M88Suite\logs`.

## Desenvolvimento

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m m88suite.app            :: abre o app
.venv\Scripts\python -m m88suite.app --selftest :: verifica dependências e UI sem o óculos
```

### Gerar o EXE

```bat
.venv\Scripts\python -m pip install pyinstaller==6.11.1
packaging\build.bat
```

Saída: `dist\M88Suite\M88Suite.exe` e `dist\M88Suite-<versão>-windows.zip` (anexe o ZIP a um
*release* do GitHub). Confira o build com `dist\M88Suite\M88Suite.exe --selftest` (resultado em
`%USERPROFILE%\M88Suite\logs\selftest.txt`).

## Código

```
src/m88suite/
  app.py              ponto de entrada (+ --selftest)
  core/
    manager.py        DeviceManager: BLE, Wi‑Fi, vídeo com watchdog, mídia (loop asyncio próprio)
    device.py         estados e telemetria
    ble_client.py     cliente BLE (bleak)
    wifi.py           Wi‑Fi do PC no AP do óculos (netsh)
    m88p.py           protocolo do firmware futuro (referência)
    stock/            protocolos do firmware de fábrica (BLE, doorbell, vídeo, FTP)
  ui/                 PySide6: tema, ícones SVG, páginas, decodificador e webcam virtual
packaging/            PyInstaller (spec, ícone, build.bat)
tests/                testes do núcleo
```
