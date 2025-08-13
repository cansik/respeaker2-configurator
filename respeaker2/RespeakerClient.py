from __future__ import annotations

import atexit
import functools
import struct
import threading

import usb.core
import usb.util

from respeaker2.PixelRing import PixelRing


class ReSpeaker2Error(Exception):
    """Base exception for ReSpeaker2 client errors."""
    pass


class DeviceNotFoundError(ReSpeaker2Error):
    """Raised when the ReSpeaker2 device cannot be found."""
    pass


class ParameterAccessError(ReSpeaker2Error):
    """Raised when trying to write to a read-only parameter."""
    pass


class ParameterRangeError(ReSpeaker2Error):
    """Raised when a parameter value is outside its allowed range."""
    pass


def _hardware_locked(method):
    """
    Decorator to serialize access to hardware-related methods.
    Acquires _hardware_lock before invoking the method.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._hardware_lock:
            return method(self, *args, **kwargs)

    return wrapper


class RespeakerClient:
    """
    Client for interacting with the ReSpeaker v2 device over USB.

    Use properties for configuration; use get_ methods for read-only statuses.
    """

    _VENDOR_ID = 0x2886
    _PRODUCT_ID = 0x0018
    _TIMEOUT = 100000

    # Internal parameter metadata: id, offset, type, max, min, access
    _PARAMETERS = {
        'AECFREEZEONOFF': (18, 7, 'int', 1, 0, 'rw'),
        'AECNORM': (18, 19, 'float', 16, 0.25, 'rw'),
        'AECPATHCHANGE': (18, 25, 'int', 1, 0, 'ro'),
        'RT60': (18, 26, 'float', 0.9, 0.25, 'ro'),
        'HPFONOFF': (18, 27, 'int', 3, 0, 'rw'),
        'RT60ONOFF': (18, 28, 'int', 1, 0, 'rw'),
        'AECSILENCELEVEL': (18, 30, 'float', 1, 1e-9, 'rw'),
        'AECSILENCEMODE': (18, 31, 'int', 1, 0, 'ro'),
        'AGCONOFF': (19, 0, 'int', 1, 0, 'rw'),
        'AGCMAXGAIN': (19, 1, 'float', 1000, 1, 'rw'),
        'AGCDESIREDLEVEL': (19, 2, 'float', 0.99, 1e-8, 'rw'),
        'AGCGAIN': (19, 3, 'float', 1000, 1, 'rw'),
        'AGCTIME': (19, 4, 'float', 1, 0.1, 'rw'),
        'CNIONOFF': (19, 5, 'int', 1, 0, 'rw'),
        'FREEZEONOFF': (19, 6, 'int', 1, 0, 'rw'),
        'STATNOISEONOFF': (19, 8, 'int', 1, 0, 'rw'),
        'GAMMA_NS': (19, 9, 'float', 3, 0, 'rw'),
        'MIN_NS': (19, 10, 'float', 1, 0, 'rw'),
        'NONSTATNOISEONOFF': (19, 11, 'int', 1, 0, 'rw'),
        'GAMMA_NN': (19, 12, 'float', 3, 0, 'rw'),
        'MIN_NN': (19, 13, 'float', 1, 0, 'rw'),
        'ECHOONOFF': (19, 14, 'int', 1, 0, 'rw'),
        'GAMMA_E': (19, 15, 'float', 3, 0, 'rw'),
        'GAMMA_ETAIL': (19, 16, 'float', 3, 0, 'rw'),
        'GAMMA_ENL': (19, 17, 'float', 5, 0, 'rw'),
        'NLATTENONOFF': (19, 18, 'int', 1, 0, 'rw'),
        'NLAEC_MODE': (19, 20, 'int', 2, 0, 'rw'),
        'SPEECHDETECTED': (19, 22, 'int', 1, 0, 'ro'),
        'FSBUPDATED': (19, 23, 'int', 1, 0, 'ro'),
        'FSBPATHCHANGE': (19, 24, 'int', 1, 0, 'ro'),
        'TRANSIENTONOFF': (19, 29, 'int', 1, 0, 'rw'),
        'VOICEACTIVITY': (19, 32, 'int', 1, 0, 'ro'),
        'STATNOISEONOFF_SR': (19, 33, 'int', 1, 0, 'rw'),
        'NONSTATNOISEONOFF_SR': (19, 34, 'int', 1, 0, 'rw'),
        'GAMMA_NS_SR': (19, 35, 'float', 3, 0, 'rw'),
        'GAMMA_NN_SR': (19, 36, 'float', 3, 0, 'rw'),
        'MIN_NS_SR': (19, 37, 'float', 1, 0, 'rw'),
        'MIN_NN_SR': (19, 38, 'float', 1, 0, 'rw'),
        'GAMMAVAD_SR': (19, 39, 'float', 1000, 0, 'rw'),
        'DOAANGLE': (21, 0, 'int', 359, 0, 'ro'),
    }

    def __init__(self) -> None:
        self._hardware_lock = threading.Lock()

        self._dev: usb.Device | None = None
        self._pixel_ring: PixelRing | None = None

        # register a disconnect handler if python shuts down
        atexit.register(self.disconnect)

    @classmethod
    def is_available(cls) -> bool:
        """True if a ReSpeaker2 is plugged in."""
        return usb.core.find(idVendor=cls._VENDOR_ID, idProduct=cls._PRODUCT_ID) is not None

    @_hardware_locked
    def connect(self) -> None:
        """Open USB connection, detach kernel drivers if needed."""
        if self._dev:
            return
        dev = usb.core.find(idVendor=self._VENDOR_ID, idProduct=self._PRODUCT_ID)
        if not dev:
            raise DeviceNotFoundError("ReSpeaker2 device not found")
        for cfg in dev:
            for intf in cfg:
                try:
                    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                        dev.detach_kernel_driver(intf.bInterfaceNumber)
                except Exception:
                    pass
        self._dev = dev
        self._pixel_ring = PixelRing(self._dev, self._TIMEOUT)

    @property
    def is_connected(self) -> bool:
        """True if currently connected."""
        return self._dev is not None

    @_hardware_locked
    def disconnect(self) -> None:
        """Release USB resources."""
        if self._dev:
            usb.util.dispose_resources(self._dev)
            self._dev = None
        if self._pixel_ring:
            self._pixel_ring = None

    def _write_parameter(self, key: str, value: int | float) -> None:
        _id, offset, ptype, pmax, pmin, access = self._PARAMETERS[key]
        if access == "ro":
            raise ParameterAccessError(f"{key} is read only")
        if not (pmin <= value <= pmax):
            raise ParameterRangeError(f"{key}={value} outside [{pmin}..{pmax}]")
        self.write_value(_id, offset, ptype, value)

    def _read_parameter(self, key: str) -> int | float:
        _id, offset, ptype, *_ = self._PARAMETERS[key]
        return self.read_value(_id, offset, ptype)

    @_hardware_locked
    def write_value(self, pid: int, offset: int, typ: str, value: int | float) -> None:
        """Low level write of one value."""
        if not self._dev:
            raise DeviceNotFoundError("Not connected")
        if typ == "int":
            payload = struct.pack("iii", offset, int(value), 1)
        else:
            payload = struct.pack("ifi", offset, float(value), 0)
        self._dev.ctrl_transfer(
            usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, 0, pid, payload, self._TIMEOUT
        )

    @_hardware_locked
    def read_value(self, pid: int, offset: int, typ: str) -> int | float:
        """Low level read of one value."""
        if not self._dev:
            raise DeviceNotFoundError("Not connected")
        cmd = 0x80 | offset
        if typ == "int":
            cmd |= 0x40
        resp = self._dev.ctrl_transfer(
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, cmd, pid, 8, self._TIMEOUT
        )
        hi, lo = struct.unpack("ii", bytes(resp))
        return hi if typ == "int" else hi * (2 ** lo)

    @property
    def device(self) -> usb.Device | None:
        return self._dev

    @property
    def pixel_ring(self) -> PixelRing | None:
        return self._pixel_ring

    # Read/Write properties
    @property
    def aec_freeze_enabled(self) -> bool:
        """Adaptive Echo Canceler freeze: True=freeze, False=enabled."""
        return bool(self._read_parameter('AECFREEZEONOFF'))

    @aec_freeze_enabled.setter
    def aec_freeze_enabled(self, v: bool) -> None:
        self._write_parameter('AECFREEZEONOFF', int(v))

    @property
    def aec_norm(self) -> float:
        """Limit on AEC filter norm (0.25..16)."""
        return self._read_parameter('AECNORM')

    @aec_norm.setter
    def aec_norm(self, v: float) -> None:
        self._write_parameter('AECNORM', v)

    @property
    def high_pass_filter(self) -> int:
        """HPF setting (0=off,1=70Hz,2=125Hz,3=180Hz)."""
        return self._read_parameter('HPFONOFF')

    @high_pass_filter.setter
    def high_pass_filter(self, v: int) -> None:
        self._write_parameter('HPFONOFF', v)

    @property
    def rt60_enabled(self) -> bool:
        """RT60 estimation toggle: True=on, False=off."""
        return bool(self._read_parameter('RT60ONOFF'))

    @rt60_enabled.setter
    def rt60_enabled(self, v: bool) -> None:
        self._write_parameter('RT60ONOFF', int(v))

    @property
    def aec_silence_threshold(self) -> float:
        """AEC silence detection threshold (1e-9..1)."""
        return self._read_parameter('AECSILENCELEVEL')

    @aec_silence_threshold.setter
    def aec_silence_threshold(self, v: float) -> None:
        self._write_parameter('AECSILENCELEVEL', v)

    @property
    def agc_enabled(self) -> bool:
        """AGC toggle: True=on, False=off."""
        return bool(self._read_parameter('AGCONOFF'))

    @agc_enabled.setter
    def agc_enabled(self, v: bool) -> None:
        self._write_parameter('AGCONOFF', int(v))

    @property
    def agc_max_gain_db(self) -> float:
        """AGC max gain in dB (1..1000)."""
        return self._read_parameter('AGCMAXGAIN')

    @agc_max_gain_db.setter
    def agc_max_gain_db(self, v: float) -> None:
        self._write_parameter('AGCMAXGAIN', v)

    @property
    def agc_desired_level_db(self) -> float:
        """AGC target level in dBov (1e-8..0.99)."""
        return self._read_parameter('AGCDESIREDLEVEL')

    @agc_desired_level_db.setter
    def agc_desired_level_db(self, v: float) -> None:
        self._write_parameter('AGCDESIREDLEVEL', v)

    @property
    def agc_gain_db(self) -> float:
        """Current AGC gain in dB (1..1000)."""
        return self._read_parameter('AGCGAIN')

    @agc_gain_db.setter
    def agc_gain_db(self, v: float) -> None:
        self._write_parameter('AGCGAIN', v)

    @property
    def agc_time(self) -> float:
        """AGC time constant in seconds (0.1..1)."""
        return self._read_parameter('AGCTIME')

    @agc_time.setter
    def agc_time(self, v: float) -> None:
        self._write_parameter('AGCTIME', v)

    @property
    def comfort_noise_enabled(self) -> bool:
        """Comfort Noise Insertion toggle: True=on, False=off."""
        return bool(self._read_parameter('CNIONOFF'))

    @comfort_noise_enabled.setter
    def comfort_noise_enabled(self, v: bool) -> None:
        self._write_parameter('CNIONOFF', int(v))

    @property
    def beamforming_freeze_enabled(self) -> bool:
        """Beamformer adaptation toggle: True=freeze, False=enabled."""
        return bool(self._read_parameter('FREEZEONOFF'))

    @beamforming_freeze_enabled.setter
    def beamforming_freeze_enabled(self, v: bool) -> None:
        self._write_parameter('FREEZEONOFF', int(v))

    @property
    def stationary_noise_enabled(self) -> bool:
        """Stationary noise suppression toggle: True=on, False=off."""
        return bool(self._read_parameter('STATNOISEONOFF'))

    @stationary_noise_enabled.setter
    def stationary_noise_enabled(self, v: bool) -> None:
        self._write_parameter('STATNOISEONOFF', int(v))

    @property
    def over_subtraction_ns(self) -> float:
        """Over-subtraction factor for stationary noise (0..3)."""
        return self._read_parameter('GAMMA_NS')

    @over_subtraction_ns.setter
    def over_subtraction_ns(self, v: float) -> None:
        self._write_parameter('GAMMA_NS', v)

    @property
    def noise_floor_ns_db(self) -> float:
        """Gain-floor for stationary noise suppression [-inf..0] dB."""
        return self._read_parameter('MIN_NS')

    @noise_floor_ns_db.setter
    def noise_floor_ns_db(self, v: float) -> None:
        self._write_parameter('MIN_NS', v)

    @property
    def non_stationary_noise_enabled(self) -> bool:
        """Non-stationary noise suppression toggle: True=on, False=off."""
        return bool(self._read_parameter('NONSTATNOISEONOFF'))

    @non_stationary_noise_enabled.setter
    def non_stationary_noise_enabled(self, v: bool) -> None:
        self._write_parameter('NONSTATNOISEONOFF', int(v))

    # Read-only getters
    def get_path_change(self) -> bool:
        """True if AEC path change detected."""
        return bool(self._read_parameter('AECPATHCHANGE'))

    def get_rt60(self) -> float:
        """Current RT60 estimate in seconds (0.25..0.9)."""
        return self._read_parameter('RT60')

    def get_aec_silence_mode(self) -> bool:
        """True if AEC far-end silence detected."""
        return bool(self._read_parameter('AECSILENCEMODE'))

    def get_speech_detected(self) -> bool:
        """True if speech currently detected."""
        return bool(self._read_parameter('SPEECHDETECTED'))

    def get_fsb_updated(self) -> bool:
        """True if FSB was updated."""
        return bool(self._read_parameter('FSBUPDATED'))

    def get_fsb_path_change(self) -> bool:
        """True if FSB path change detected."""
        return bool(self._read_parameter('FSBPATHCHANGE'))

    def get_voice_activity(self) -> bool:
        """True if voice activity detected."""
        return bool(self._read_parameter('VOICEACTIVITY'))

    def get_direction_of_arrival(self) -> int:
        """DOA angle in degrees (0..359)."""
        return int(self._read_parameter('DOAANGLE'))

    def close(self) -> None:
        """Alias for disconnect()."""
        self.disconnect()
