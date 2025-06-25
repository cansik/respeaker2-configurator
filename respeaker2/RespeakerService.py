import struct
import threading
import time
from typing import List

import usb.core
import usb.util
from duit.annotation.AnnotationFinder import AnnotationFinder
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
    POLL_INTERVAL = 0.250  # seconds

    def __init__(self, vid: int = 0x2886, pid: int = 0x0018):
        self.dev = usb.core.find(idVendor=vid, idProduct=pid)
        if not self.dev:
            raise RuntimeError("ReSpeaker device not found")
        # detach kernel driver if needed
        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except Exception:
            pass
        self.registry: List[RespeakerRegistration] = []
        self._polling = False
        self._thread: threading.Thread = None  # type: ignore

    def register(self, model: object) -> None:
        """Scan model for DataFields annotated with RespeakerParam and wire change handlers."""
        finder = AnnotationFinder(RespeakerParam)
        for name, (df, anno) in finder.find(model).items():
            reg = RespeakerRegistration(df, anno)
            self.registry.append(reg)
            # on change, write
            if anno.rw == 'rw':
                df.on_changed += self._make_writer(reg)

    def _make_writer(self, reg: RespeakerRegistration):
        def writer(value):
            if reg.silent:
                return
            # build payload
            if reg.anno.typ == 'int':
                payload = struct.pack('iii', reg.anno.offset, int(value), 1)
                cmd = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
                self.dev.ctrl_transfer(cmd, 0, 0, reg.anno.pid, payload)
            else:
                payload = struct.pack('ifi', reg.anno.offset, float(value), 0)
                cmd = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
                self.dev.ctrl_transfer(cmd, 0, 0, reg.anno.pid, payload)

        return writer

    def _read_param(self, reg: RespeakerRegistration):
        # build read command
        offset = reg.anno.offset
        cmd = 0x80 | offset
        if reg.anno.typ == 'int':
            cmd |= 0x40
        length = 8
        data = self.dev.ctrl_transfer(
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, cmd, reg.anno.pid, length
        )
        hi, lo = struct.unpack('ii', data.tobytes())
        if reg.anno.typ == 'int':
            return hi
        else:
            return hi * (2. ** lo)

    def start_polling(self, interval: float = None) -> None:
        if interval is None:
            interval = self.POLL_INTERVAL
        if self._polling:
            return
        self._polling = True

        def poll_loop():
            while self._polling:
                for reg in self.registry:
                    # always read regardless of rw, update df
                    try:
                        val = self._read_param(reg)
                        # silence writes
                        reg.silent = True
                        reg.field.value = val
                        reg.silent = False
                    except Exception:
                        pass
                time.sleep(interval)

        self._thread = threading.Thread(target=poll_loop, daemon=True)
        self._thread.start()

    def stop_polling(self) -> None:
        """Stop polling loop and join thread (with timeout to avoid blocking)."""
        self._polling = False
        if self._thread and self._thread.is_alive():
            try:
                # wait only up to one interval to avoid blocking
                self._thread.join(timeout=self.POLL_INTERVAL)
            except KeyboardInterrupt:
                # swallow interrupt during join
                pass

    def close(self) -> None:
        self.stop_polling()
        usb.util.dispose_resources(self.dev)
