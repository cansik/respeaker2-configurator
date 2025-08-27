from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, Optional, Literal

from duit.event.Event import Event
from usb.core import Device

from respeaker2.RespeakerDFU import RespeakerDFU, DFUDeviceInfo

Mode = Literal["runtime", "dfu"]


@dataclass(frozen=True)
class DeviceKey:
    vid: int
    pid: int
    bus: int
    address: int
    interface_number: int

    @classmethod
    def from_info(cls, info: DFUDeviceInfo) -> DeviceKey:
        dev = info.device
        return cls(
            vid=dev.idVendor,
            pid=dev.idProduct,
            bus=getattr(dev, "bus", 0),
            address=getattr(dev, "address", 0),
            interface_number=info.interface_number,
        )


@dataclass(frozen=True)
class DiscoveredDevice:
    key: DeviceKey
    device: Device
    mode: Mode
    num_interfaces: int


class RespeakerDiscovery:
    def __init__(self, poll_interval_s: float = 0.5) -> None:
        self.on_device_discovered: Event[DiscoveredDevice] = Event()
        self.on_device_removed: Event[DeviceKey] = Event()

        self._poll_interval_s = poll_interval_s
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()
        self._lock = threading.Lock()
        self._known: Dict[DeviceKey, DiscoveredDevice] = {}

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_evt.clear()
            self._thread = threading.Thread(target=self._run, name="RespeakerDiscovery", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()

    def join(self, timeout: Optional[float] = None) -> None:
        t = self._thread
        if t:
            t.join(timeout)

    def snapshot(self) -> Dict[DeviceKey, DiscoveredDevice]:
        with self._lock:
            return dict(self._known)

    # internal

    def _run(self) -> None:
        try:
            current = self._scan_now()
        except Exception:
            current = {}

        with self._lock:
            self._known = current

        for item in current.values():
            self._safe_fire_discovered(item)

        while not self._stop_evt.wait(self._poll_interval_s):
            try:
                next_scan = self._scan_now()
            except Exception:
                continue

            added = next_scan.keys() - self._known.keys()
            removed = self._known.keys() - next_scan.keys()

            for k in added:
                self._known[k] = next_scan[k]
                self._safe_fire_discovered(next_scan[k])

            for k in removed:
                self._known.pop(k, None)
                self._safe_fire_removed(k)

    def _scan_now(self) -> Dict[DeviceKey, DiscoveredDevice]:
        table: Dict[DeviceKey, DiscoveredDevice] = {}
        for info in RespeakerDFU.find_devices():
            key = DeviceKey.from_info(info)
            mode: Mode = "dfu" if info.num_interfaces == 1 else "runtime"
            table[key] = DiscoveredDevice(
                key=key,
                device=info.device,
                mode=mode,
                num_interfaces=info.num_interfaces,
            )
        return table

    def _safe_fire_discovered(self, item: DiscoveredDevice) -> None:
        try:
            self.on_device_discovered(item)
        except Exception:
            pass

    def _safe_fire_removed(self, key: DeviceKey) -> None:
        try:
            self.on_device_removed(key)
        except Exception:
            pass
