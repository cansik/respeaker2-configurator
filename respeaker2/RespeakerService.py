import threading
import time
from typing import Optional

from duit.model.DataField import DataField

from respeaker2.RespeakerParam import RespeakerParam


class RespeakerRegistration:
    def __init__(self, field: DataField, anno: RespeakerParam):
        self.field = field
        self.anno = anno
        self.silent = False

    def __repr__(self):
        return f"{self.field.name}: pid={self.anno.pid}, off={self.anno.offset}"


class RespeakerService:
    """
    Service to manage connection to a ReSpeaker device, parameter registration,
    polling and write-back of parameter changes.
    Exposes Events for connection, disconnection, and errors.
    """

    POLL_INTERVAL = 0.250  # seconds

    def __init__(self, vid: int = 0x2886, pid: int = 0x0018) -> None:
        from duit.event.Event import Event

        self._vid = vid
        self._pid = pid
        self._dev = None
        self._registry = []
        self._polling = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False

        # events
        self.on_connected = Event["RespeakerService"]()
        self.on_disconnected = Event["RespeakerService"]()
        self.on_error = Event[str]()

    @property
    def connected(self) -> bool:
        """Read-only connection state."""
        return self._connected

    def connect(self) -> None:
        """Find and initialize the USB device, verify responsiveness, then start polling."""
        import usb.util

        dev = usb.core.find(idVendor=self._vid, idProduct=self._pid)
        if not dev:
            raise RuntimeError("ReSpeaker device not found")
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except Exception:
            pass

        # verify device responds by reading one registered param
        self._dev = dev
        if self._registry:
            test = self._registry[0]
            # will raise if not responding
            try:
                _ = self._read_registration(test)
            except Exception as ex:
                self.on_error("Error reading device, maybe plug it in and out again!")
                return

        self._connected = True
        self.on_connected(self)
        if self._registry and not self._polling:
            self.start_polling()

    def disconnect(self) -> None:
        """Stop polling and release the USB device."""
        import usb.util

        if self._polling:
            self.stop_polling()
        if self._dev:
            usb.util.dispose_resources(self._dev)
            self._dev = None
        self._connected = False
        self.on_disconnected(self)

    def register(self, model: object) -> None:
        """Scan model for annotated DataFields, hook change handlers, and start polling if connected."""
        from duit.annotation.AnnotationFinder import AnnotationFinder
        from respeaker2.RespeakerParam import RespeakerParam

        finder = AnnotationFinder(RespeakerParam)
        for name, (df, anno) in finder.find(model).items():
            reg = RespeakerRegistration(df, anno)
            self._registry.append(reg)
            if anno.rw == 'rw':
                df.on_changed += self._make_writer(reg)
        if self._connected and not self._polling:
            self.start_polling()

    def _read_param_raw(self, pid: int, offset: int, typ: str):
        """Low-level read of one parameter."""
        import usb.util, struct
        cmd = 0x80 | offset
        if typ == 'int':
            cmd |= 0x40
        data = self._dev.ctrl_transfer(
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, cmd, pid, 8
        )
        hi, lo = struct.unpack('ii', data.tobytes())
        return hi if typ == 'int' else hi * (2. ** lo)

    def _write_param_raw(self, pid: int, offset: int, typ: str, value) -> None:
        """Low-level write of one parameter."""
        import usb.util, struct
        if typ == 'int':
            payload = struct.pack('iii', offset, int(value), 1)
        else:
            payload = struct.pack('ifi', offset, float(value), 0)
        cmd = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
        self._dev.ctrl_transfer(cmd, 0, 0, pid, payload)

    def _read_registration(self, reg: RespeakerRegistration):
        try:
            return self._read_param_raw(reg.anno.pid, reg.anno.offset, reg.anno.typ)
        except Exception as e:
            self.on_error(str(e))
            raise

    def _write_registration(self, reg: RespeakerRegistration, value) -> None:
        try:
            self._write_param_raw(reg.anno.pid, reg.anno.offset, reg.anno.typ, value)
        except Exception as e:
            self.on_error(str(e))

    def _make_writer(self, reg: RespeakerRegistration):
        def writer(value):
            if not self._connected or reg.silent:
                return
            self._write_registration(reg, value)

        return writer

    def _read_param(self, reg: RespeakerRegistration):
        """Used by polling."""
        try:
            return self._read_registration(reg)
        except Exception:
            return None

    def start_polling(self, interval: float = None) -> None:
        """Begin background polling of registered parameters."""
        if not self._connected or self._polling:
            return
        if interval is None:
            interval = self.POLL_INTERVAL
        self._polling = True

        def poll_loop():
            while self._polling:
                if not self._connected:
                    break
                for reg in self._registry:
                    val = self._read_param(reg)
                    if val is None:
                        self.on_error('Device lost during polling, disconnecting.')
                        self.disconnect()
                        return
                    reg.silent = True
                    reg.field.value = val
                    reg.silent = False
                time.sleep(interval)

        self._thread = threading.Thread(target=poll_loop, daemon=True)
        self._thread.start()

    def stop_polling(self) -> None:
        """Stop the polling loop; daemon thread will exit on next iteration."""
        self._polling = False

    def close(self) -> None:
        """Disconnect and cleanup."""
        self.disconnect()
