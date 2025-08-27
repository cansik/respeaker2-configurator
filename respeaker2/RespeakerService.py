import threading
import time
from typing import Optional

from duit.event.Event import Event
from duit.model.DataField import DataField

from respeaker2.RespeakerClient import RespeakerClient
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
    polling and write back of parameter changes.
    Exposes Events for connection, disconnection, and errors.
    """

    POLL_INTERVAL = 0.250  # seconds

    def __init__(self) -> None:
        self._client = RespeakerClient()

        self._registry = []
        self._polling = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # events
        self.on_connected = Event["RespeakerService"]()
        self.on_disconnected = Event["RespeakerService"]()
        self.on_error = Event[str]()
        self.on_poll = Event["RespeakerService"]()

    @property
    def connected(self) -> bool:
        """Read only connection state."""
        return self._client.is_connected

    def connect(self) -> None:
        """Connect via RespeakerClient, verify responsiveness, then start polling."""
        try:
            self._client.connect()
        except Exception as ex:
            raise RuntimeError(str(ex)) from ex

        # verify device responds by reading one registered param
        if self._registry:
            test = self._registry[0]
            try:
                _ = self._read_registration(test)
            except Exception:
                self.on_error("Error reading device, maybe plug it in and out again!")
                self._client.disconnect()
                return

        self.on_connected(self)

        if self._registry and not self._polling.is_set():
            self.start_polling()

    def disconnect(self) -> None:
        """Stop polling and release the device."""
        if self._polling.is_set():
            self.stop_polling()

        if self._client.is_connected:
            self._client.disconnect()

        self.on_disconnected(self)

    def register(self, model: object) -> None:
        """Scan model for annotated DataFields, hook change handlers, and start polling if connected."""
        from duit.annotation.AnnotationFinder import AnnotationFinder

        finder = AnnotationFinder(RespeakerParam)
        for _field_name, (df, anno) in finder.find(model).items():
            reg = RespeakerRegistration(df, anno)
            self._registry.append(reg)
            if anno.rw == "rw":
                df.on_changed += self._make_writer(reg)
        if self._client.is_connected and not self._polling.is_set():
            self.start_polling()

    def _read_registration(self, reg: RespeakerRegistration):
        try:
            return self._client.read_value(reg.anno.pid, reg.anno.offset, reg.anno.typ)
        except Exception as e:
            self.on_error(str(e))
            raise

    def _write_registration(self, reg: RespeakerRegistration, value) -> None:
        try:
            self._client.write_value(reg.anno.pid, reg.anno.offset, reg.anno.typ, value)
        except Exception as e:
            self.on_error(str(e))

    def _make_writer(self, reg: RespeakerRegistration):
        def writer(value):
            if not self._client.is_connected or reg.silent:
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
        if not self._client.is_connected or self._polling.is_set():
            return
        if interval is None:
            interval = self.POLL_INTERVAL

        self._polling.set()

        def poll_loop():
            while self._polling.is_set():
                for reg in self._registry:
                    if not self._client.is_connected:
                        break

                    val = self._read_param(reg)
                    if val is None:
                        self.on_error("Device lost during polling, stopping polling thread.")
                        self._polling.clear()
                        continue
                    reg.silent = True
                    reg.field.value = val
                    reg.silent = False
                self.on_poll(self)

                try:
                    time.sleep(interval)
                except KeyboardInterrupt:
                    break

        self._thread = threading.Thread(target=poll_loop, daemon=True)
        self._thread.start()

    def stop_polling(self) -> None:
        """Stop the polling loop; daemon thread will exit on next iteration."""
        if self._polling.is_set():
            self._polling.clear()

        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=5.0)

    def close(self) -> None:
        """Disconnect and cleanup."""
        self.disconnect()
