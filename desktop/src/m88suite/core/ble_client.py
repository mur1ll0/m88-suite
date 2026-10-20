"""Conexao BLE com o M88 pelo adaptador Bluetooth do PC (bleak / WinRT)."""
import asyncio

from bleak import BleakClient, BleakScanner

from .stock import keepfit as protocol
from .eventlog import event


async def scan(timeout: float = 8.0, name_hint: str = "M88"):
    event("BLE", f"escaneando {timeout:.0f}s por dispositivos BLE...")
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    results = []
    for device, adv in found.values():
        name = device.name or adv.local_name or ""
        is_m88 = name_hint.lower() in name.lower() or protocol.SERVICE_UUID in (adv.service_uuids or [])
        results.append((device, adv, is_m88))
    results.sort(key=lambda r: (not r[2], -(r[1].rssi or -999)))
    for device, adv, is_m88 in results:
        if is_m88 or adv.rssi > -75:
            event(
                "BLE",
                f"{'M88 ' if is_m88 else ''}{device.address} nome='{device.name or adv.local_name}' rssi={adv.rssi} "
                f"servicos={adv.service_uuids}",
                address=device.address, is_m88=is_m88,
            )
    return [r for r in results if r[2]]


class M88Ble:
    """Sessao BLE: conecta, assina todas as notificacoes e envia frames 0x54."""

    def __init__(self, address: str | None = None):
        self.address = address
        self.client: BleakClient | None = None
        self.notifications: list[tuple[str, bytes]] = []
        self._waiters: list[tuple[callable, asyncio.Future]] = []
        self.auto_reconnect = False
        self.on_notify = None  # callback(uuid, bytes) para telemetria
        self.on_link = None  # callback(bool conectado)
        self._closing = False

    async def connect(self, scan_timeout: float = 10.0):
        if not self.address:
            event("BLE", "procurando M88...")
            device = await BleakScanner.find_device_by_filter(
                lambda d, adv: "m88" in (d.name or adv.local_name or "").lower()
                or protocol.SERVICE_UUID in (adv.service_uuids or []),
                timeout=scan_timeout,
            )
            if device is None:
                raise RuntimeError(
                    "M88 nao encontrado por BLE. Ligue o oculos, feche o WheatAI/app Android "
                    "(o BLE aceita uma conexao por vez) e tente de novo."
                )
            self.address = device.address
        event("BLE", f"conectando em {self.address}...")
        self.client = BleakClient(self.address, disconnected_callback=self._on_disconnect)
        await self.client.connect(timeout=20.0)
        event("BLE", f"conectado={self.client.is_connected} mtu={self.client.mtu_size}")
        await self._subscribe_all()

    def _on_disconnect(self, _client):
        event("BLE", "desconectado pelo oculos ou pelo Windows")
        if self.on_link:
            self.on_link(False)
        if self.auto_reconnect and not self._closing:
            asyncio.get_event_loop().create_task(self._reconnect())

    async def _reconnect(self):
        for attempt in range(1, 6):
            await asyncio.sleep(1.0)
            try:
                event("BLE", f"reconectando (tentativa {attempt})...")
                self.client = BleakClient(self.address, disconnected_callback=self._on_disconnect)
                await self.client.connect(timeout=15.0)
                await self._subscribe_all(verbose=False)
                event("BLE", "reconectado")
                if self.on_link:
                    self.on_link(True)
                return
            except Exception as e:
                event("BLE", f"reconexao falhou: {e}")

    @property
    def connected(self) -> bool:
        return bool(self.client and self.client.is_connected)

    async def keepalive(self, interval: float = 3.0):
        """Envia consulta de estado periodica para manter o link BLE/AP vivo."""
        while not self._closing:
            await asyncio.sleep(interval)
            if self.connected:
                try:
                    await self.send(protocol.frame(protocol.CMD_WIFI_STATE, 0x01), "keepalive")
                except Exception as e:
                    event("BLE", f"keepalive falhou: {e}")

    async def _subscribe_all(self, verbose: bool = True):
        for service in self.client.services:
            if verbose:
                event("GATT", f"servico {service.uuid}")
            for ch in service.characteristics:
                if verbose:
                    event("GATT", f"  char {ch.uuid} props={','.join(ch.properties)}")
                if "notify" in ch.properties or "indicate" in ch.properties:
                    try:
                        await self.client.start_notify(ch, self._make_handler(ch.uuid))
                        if verbose:
                            event("GATT", f"  notify ativo em {ch.uuid}")
                    except Exception as e:  # algumas chars exigem pareamento
                        event("GATT", f"  notify falhou em {ch.uuid}: {e}")

    def _make_handler(self, uuid: str):
        def handler(_sender, data: bytearray):
            data = bytes(data)
            self.notifications.append((uuid, data))
            del self.notifications[:-200]
            if self.on_notify:
                self.on_notify(uuid, data)
            event("RX", f"{uuid[4:8]} {data.hex().upper()} -> {protocol.decode(data)}", uuid=uuid, hex=data.hex())
            for predicate, fut in list(self._waiters):
                if not fut.done() and predicate(data):
                    fut.set_result(data)
        return handler

    async def send(self, data: bytes, label: str = ""):
        protocol.check_safe(data)
        ch = self.client.services.get_characteristic(protocol.TX_UUID)
        if ch is None:
            raise RuntimeError(f"caracteristica TX {protocol.TX_UUID} ausente; veja o dump GATT")
        with_response = "write" in ch.properties
        await self.client.write_gatt_char(ch, data, response=with_response)
        event("TX", f"{label} {data.hex().upper()}", hex=data.hex(), label=label)

    async def restart_device(self):
        """Reinicia o oculos (mesmo frame do botao Reiniciar do WheatAI)."""
        data = protocol.RESTART_FRAME
        assert data[:9] == bytes.fromhex("0E123456789ABCDEF0") and not any(data[9:])
        ch = self.client.services.get_characteristic(protocol.TX_UUID)
        await self.client.write_gatt_char(ch, data, response="write" in ch.properties)
        event("TX", f"restart {data.hex().upper()}", hex=data.hex(), label="restart")

    async def command(self, name: str):
        cmd, mode = protocol.NAMED[name]
        await self.send(protocol.frame(cmd, mode), name)

    async def wait_for(self, predicate, timeout: float):
        for _, data in self.notifications:
            if predicate(data):
                return data
        fut = asyncio.get_running_loop().create_future()
        entry = (predicate, fut)
        self._waiters.append(entry)
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._waiters.remove(entry)

    async def disconnect(self):
        self._closing = True
        if self.client and self.client.is_connected:
            await self.client.disconnect()


def is_ap_ready(data: bytes) -> bool:
    ap_active = data[:2] == b"\x54\x13" and len(data) > 2 and data[2] == 0x02
    has_ip = data[:7] == bytes.fromhex("540402c0a83001")
    return ap_active or has_ip
