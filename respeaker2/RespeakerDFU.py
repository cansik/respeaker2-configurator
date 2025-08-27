from __future__ import annotations

import io
import os
import threading
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import BinaryIO

import usb.core
import usb.util


class DFUError(Exception):
    pass


class DeviceNotFoundError(DFUError):
    pass


class MultipleDevicesFoundError(DFUError):
    pass


class NotConnectedError(DFUError):
    pass


class DFUStatusError(DFUError):
    def __init__(self, code: int, description: str):
        super().__init__(f"DFU status {code}: {description}")
        self.code = code
        self.description = description


class _USBConsts:
    TIMEOUT_MS = 120000

    # Standard DFU class requests
    DFU_DETACH = 0
    DFU_DNLOAD = 1
    DFU_UPLOAD = 2
    DFU_GETSTATUS = 3
    DFU_CLRSTATUS = 4
    DFU_GETSTATE = 5
    DFU_ABORT = 6

    # XMOS vendor extensions
    XMOS_DFU_RESETDEVICE = 0xF0
    XMOS_DFU_REVERTFACTORY = 0xF1
    XMOS_DFU_RESETINTODFU = 0xF2
    XMOS_DFU_RESETFROMDFU = 0xF3
    XMOS_DFU_SAVESTATE = 0xF5
    XMOS_DFU_RESTORESTATE = 0xF6

    # USB class and subclass for DFU
    USB_CLASS_APP_SPECIFIC = 0xFE
    USB_SUBCLASS_DFU = 0x01

    # USB control flags
    CTRL_OUT_CLASS_IFACE = (
            usb.util.CTRL_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE
    )
    CTRL_IN_CLASS_IFACE = (
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE
    )


class DFUState(IntEnum):
    app_idle = 0
    app_detach = 1
    dfu_idle = 2
    dfu_dnload_sync = 3
    dfu_dn_busy = 4
    dfu_dnload_idle = 5
    dfu_manifest_sync = 6
    dfu_manifest = 7
    dfu_manifest_wait_reset = 8
    dfu_upload_idle = 9
    dfu_error = 10


_DFU_STATUS_DESCRIPTIONS: dict[int, str] = {
    0x00: "No error.",
    0x01: "File is not targeted for this device.",
    0x02: "File fails vendor specific verification.",
    0x03: "Device is unable to write memory.",
    0x04: "Memory erase failed.",
    0x05: "Memory erase check failed.",
    0x06: "Program memory function failed.",
    0x07: "Programmed memory failed verification.",
    0x08: "Address out of range.",
    0x09: "Received DNLOAD with wLength=0 but device expects more.",
    0x0A: "Firmware is corrupt. Cannot return to runtime.",
    0x0B: "Vendor specific error string.",
    0x0C: "Unexpected USB reset detected.",
    0x0D: "Unexpected power on reset detected.",
    0x0E: "Unknown error.",
    0x0F: "Unexpected request stalled.",
}


@dataclass(frozen=True)
class DFUStatus:
    status_code: int
    poll_timeout_ms: int
    state: DFUState
    i_status_str: int
    description: str


@dataclass(frozen=True)
class DFUDeviceInfo:
    device: usb.core.Device
    interface_number: int
    num_interfaces: int


def _hw_locked(method):
    def wrapper(self: "RespeakerDFU", *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    return wrapper


class RespeakerDFU:
    VENDOR_ID = 0x2886
    PRODUCT_ID = 0x0018

    def __init__(self) -> None:
        self._device: usb.core.Device | None = None
        self._iface_number: int | None = None
        self._num_interfaces: int = 0
        self._lock = threading.Lock()

    # discovery

    @classmethod
    def is_available(cls) -> bool:
        return usb.core.find(idVendor=cls.VENDOR_ID, idProduct=cls.PRODUCT_ID) is not None

    @classmethod
    def find_devices(cls) -> list[DFUDeviceInfo]:
        out: list[DFUDeviceInfo] = []
        for dev in usb.core.find(find_all=True, idVendor=cls.VENDOR_ID, idProduct=cls.PRODUCT_ID):
            cfg = dev.get_active_configuration()
            for intf in cfg:
                if (
                        intf.bInterfaceClass == _USBConsts.USB_CLASS_APP_SPECIFIC
                        and intf.bInterfaceSubClass == _USBConsts.USB_SUBCLASS_DFU
                ):
                    out.append(DFUDeviceInfo(dev, intf.bInterfaceNumber, cfg.bNumInterfaces))
                    break
        return out

    # connection lifecycle

    @_hw_locked
    def connect(self, require_dfu_mode: bool = True, detach_kernel_drivers: bool = True) -> None:
        """
        Connect to a single DFU interface. If the device is in runtime
        mode (multiple interfaces) and require_dfu_mode is True, this
        will trigger an XMOS reset into DFU and wait for reenumeration.
        """
        if self._device is not None:
            return

        infos = self.find_devices()
        if not infos:
            raise DeviceNotFoundError("No DFU interface found for ReSpeaker2")
        if len(infos) > 1:
            raise MultipleDevicesFoundError("Multiple DFU interfaces found")

        info = infos[0]

        # If device exposes more than one interface, it is likely in runtime mode
        if info.num_interfaces > 1 and require_dfu_mode:
            # temporary attach to send vendor reset into DFU
            self._device = info.device
            self._iface_number = info.interface_number
            self._num_interfaces = info.num_interfaces
            self._claim_interface(detach_kernel_drivers)
            try:
                self._vendor_reset_into_dfu()
            finally:
                self._release_interface()
                self._clear_handles()

            # wait for single interface DFU reenumeration
            self._wait_for_reenumeration(expected_num_ifaces=1)

            # discover again and attach
            infos = self.find_devices()
            if not infos:
                raise DeviceNotFoundError("DFU device did not reenumerate")
            info = infos[0]

        self._device = info.device
        self._iface_number = info.interface_number
        self._num_interfaces = info.num_interfaces
        self._claim_interface(detach_kernel_drivers)

    @_hw_locked
    def disconnect(self) -> None:
        """
        Release interface and clear handles. Does not force a reboot.
        """
        if self._device is None:
            return
        try:
            usb.util.dispose_resources(self._device)
        finally:
            self._clear_handles()

    def __enter__(self) -> "RespeakerDFU":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # properties

    @property
    def is_connected(self) -> bool:
        return self._device is not None

    @property
    def interface_number(self) -> int | None:
        return self._iface_number

    @property
    def num_interfaces(self) -> int:
        return self._num_interfaces

    # high level actions

    @_hw_locked
    def enter_dfu_mode(self, timeout_s: float = 20.0) -> None:
        """
        Request a runtime device to enter DFU, then wait for a 1 interface DFU.
        If already in DFU, this is a no-op.
        """
        if self._device is None:
            raise NotConnectedError("Not connected")
        if self._num_interfaces == 1:
            return
        self._vendor_reset_into_dfu()
        self._release_interface()
        self._clear_handles()
        self._wait_for_reenumeration(expected_num_ifaces=1, timeout_s=timeout_s)
        infos = self.find_devices()
        if not infos:
            raise DeviceNotFoundError("DFU device did not reenumerate")
        info = infos[0]
        self._device = info.device
        self._iface_number = info.interface_number
        self._num_interfaces = info.num_interfaces
        self._claim_interface(detach_kernel_drivers=True)

    @_hw_locked
    def leave_dfu_and_reboot(self) -> None:
        """
        Leave DFU and reboot back to runtime firmware.
        """
        self._ensure_connected()
        self._out_request(_USBConsts.XMOS_DFU_RESETFROMDFU)

    @_hw_locked
    def revert_to_factory(self) -> None:
        """
        Ask device to revert to factory image.
        """
        self._ensure_connected()
        self._out_request(_USBConsts.XMOS_DFU_REVERTFACTORY)

    @_hw_locked
    def reset_device(self) -> None:
        """
        XMOS generic reset.
        """
        self._ensure_connected()
        self._out_request(_USBConsts.XMOS_DFU_RESETDEVICE)

    @_hw_locked
    def save_state(self) -> None:
        self._ensure_connected()
        self._out_request(_USBConsts.XMOS_DFU_SAVESTATE)

    @_hw_locked
    def restore_state(self) -> None:
        self._ensure_connected()
        self._out_request(_USBConsts.XMOS_DFU_RESTORESTATE)

    # firmware transfer

    @_hw_locked
    def download_firmware(
            self,
            firmware: str | os.PathLike[str] | bytes | BinaryIO,
            block_size: int = 64,
            progress: callable | None = None,
    ) -> None:
        """
        Download firmware to the device using DFU_DNLOAD.
        The caller is responsible for leaving DFU and rebooting after success.

        firmware:
          - path to a file
          - bytes object
          - open binary file object
        """
        self._ensure_connected()

        stream: BinaryIO
        must_close = False

        if isinstance(firmware, (str, os.PathLike)):
            stream = open(firmware, "rb")
            must_close = True
        elif isinstance(firmware, bytes):
            stream = io.BytesIO(firmware)
        elif hasattr(firmware, "read"):
            stream = firmware  # type: ignore[assignment]
        else:
            raise TypeError("firmware must be path, bytes, or BinaryIO")

        try:
            block_num = 0
            while True:
                chunk = stream.read(block_size)
                self._download_block(block_num, chunk)
                status = self.get_status()
                if status.status_code != 0:
                    raise DFUStatusError(status.status_code, status.description)
                if progress is not None:
                    progress(block_num, len(chunk) if chunk else 0)
                block_num += 1
                if not chunk:
                    break
        finally:
            if must_close:
                stream.close()

    # DFU primitives

    @_hw_locked
    def abort_transfer(self) -> None:
        self._ensure_connected()
        self._out_request(_USBConsts.DFU_ABORT)

    @_hw_locked
    def clear_status(self) -> None:
        self._ensure_connected()
        self._out_request(_USBConsts.DFU_CLRSTATUS)

    @_hw_locked
    def get_state(self) -> DFUState:
        self._ensure_connected()
        raw = self._in_request(_USBConsts.DFU_GETSTATE, 1)[0]
        try:
            return DFUState(raw)
        except ValueError:
            return DFUState.dfu_error

    @_hw_locked
    def get_status(self) -> DFUStatus:
        self._ensure_connected()
        data = self._in_request(_USBConsts.DFU_GETSTATUS, 6)
        if len(data) != 6:
            raise DFUError("GETSTATUS returned invalid length")

        status_code = data[0]
        poll_timeout_ms = (data[1] | (data[2] << 8) | (data[3] << 16)) & 0xFFFFFF
        state_val = data[4]
        i_status_str = data[5]

        try:
            state = DFUState(state_val)
        except ValueError:
            state = DFUState.dfu_error

        desc = _DFU_STATUS_DESCRIPTIONS.get(status_code, "Unknown DFU status")
        return DFUStatus(
            status_code=status_code,
            poll_timeout_ms=poll_timeout_ms,
            state=state,
            i_status_str=i_status_str,
            description=desc,
        )

    @staticmethod
    def wait_for_runtime_device(wait_s: float = 20.0):
        """Waits for runtime device visible as USB interface."""
        RespeakerDFU._wait_for_reenumeration(expected_num_ifaces=5, timeout_s=wait_s)

    @staticmethod
    def wait_for_dfu_device(wait_s: float = 20.0):
        """Waits for dfu device visible as USB interface."""
        RespeakerDFU._wait_for_reenumeration(expected_num_ifaces=1, timeout_s=wait_s)

    # low level helpers

    def _ensure_connected(self) -> None:
        if self._device is None or self._iface_number is None:
            raise NotConnectedError("Not connected")

    def _claim_interface(self, detach_kernel_drivers: bool) -> None:
        assert self._device is not None
        assert self._iface_number is not None
        if detach_kernel_drivers:
            try:
                if self._device.is_kernel_driver_active(self._iface_number):
                    self._device.detach_kernel_driver(self._iface_number)
            except Exception:
                # Some platforms do not implement this
                pass
        usb.util.claim_interface(self._device, self._iface_number)

    def _release_interface(self) -> None:
        if self._device is not None and self._iface_number is not None:
            try:
                usb.util.release_interface(self._device, self._iface_number)
            except Exception:
                pass
            try:
                usb.util.dispose_resources(self._device)
            except Exception:
                pass

    def _clear_handles(self) -> None:
        self._device = None
        self._iface_number = None
        self._num_interfaces = 0

    @staticmethod
    def _wait_for_reenumeration(expected_num_ifaces: int, timeout_s: float = 20.0,
                                interval_s: float = 0.5) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(interval_s)
            infos = RespeakerDFU.find_devices()
            if infos and infos[0].num_interfaces == expected_num_ifaces:
                return
        raise DeviceNotFoundError("Timed out waiting for reenumeration")

    def _vendor_reset_into_dfu(self) -> None:
        self._out_request(_USBConsts.XMOS_DFU_RESETINTODFU)

    def _download_block(self, block_number: int, data: bytes | None) -> None:
        if data is None:
            data = b""
        self._out_request(_USBConsts.DFU_DNLOAD, value=block_number, data=data)

    def _out_request(self, request: int, value: int = 0, data: bytes | None = None):
        self._ensure_connected()
        return self._device.ctrl_transfer(  # type: ignore[union-attr]
            _USBConsts.CTRL_OUT_CLASS_IFACE,
            request,
            value,
            self._iface_number,  # type: ignore[arg-type]
            data,
            _USBConsts.TIMEOUT_MS,
        )

    def _in_request(self, request: int, length: int) -> bytes:
        self._ensure_connected()
        return self._device.ctrl_transfer(  # type: ignore[union-attr]
            _USBConsts.CTRL_IN_CLASS_IFACE,
            request,
            0,
            self._iface_number,  # type: ignore[arg-type]
            length,
            _USBConsts.TIMEOUT_MS,
        )
