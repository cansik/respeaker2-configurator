import usb


class PixelRing:
    """
    Controller for the ReSpeaker v2 Pixel Ring LEDs via USB.
    """

    def __init__(self, dev: usb.core.Device, timeout: int = 10000) -> None:
        """Initialize with a connected USB device."""
        self._dev = dev
        self._timeout = timeout

    def trace(self) -> None:
        """Display the trace pattern."""
        self._write(0)

    def mono(self, color: int) -> None:
        """Set all LEDs to a single RGB color."""
        rgb = [(color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF, 0]
        self._write(1, rgb)

    def set_color(self, rgb: tuple[int, int, int] | None = None, r: int = 0, g: int = 0, b: int = 0) -> None:
        """Set color by RGB tuple or individual components."""
        if rgb:
            self.mono((rgb[0] << 16) | (rgb[1] << 8) | rgb[2])
        else:
            self._write(1, [r, g, b, 0])

    def off(self) -> None:
        """Turn off all LEDs."""
        self.mono(0)

    def listen(self, direction: int | None = None) -> None:
        """Display listen animation (optionally with direction)."""
        self._write(2)

    def speak(self) -> None:
        """Display speak animation."""
        self._write(3)

    def think(self) -> None:
        """Display think animation."""
        self._write(4)

    def spin(self) -> None:
        """Display spin animation."""
        self._write(5)

    def show(self, data: list[int]) -> None:
        """Display raw LED data list."""
        self._write(6, data)

    def set_brightness(self, brightness: int) -> None:
        """Set LED brightness (0..255)."""
        self._write(0x20, [brightness])

    def set_color_palette(self, first: int, second: int) -> None:
        """Define two-color palette for animations."""
        a = [(first >> 16) & 0xFF, (first >> 8) & 0xFF, first & 0xFF, 0]
        b = [(second >> 16) & 0xFF, (second >> 8) & 0xFF, second & 0xFF, 0]
        self._write(0x21, a + b)

    def set_vad_led(self, state: bool) -> None:
        """Enable or disable VAD LED indicator."""
        self._write(0x22, [int(state)])

    def set_volume(self, volume: int) -> None:
        """Set volume LED indicator level (0..255)."""
        self._write(0x23, [volume])

    def _write(self, cmd: int, data: list[int] | None = None) -> None:
        """
        Send a control transfer to the Pixel Ring.

        :param cmd: command code
        :param data: list of data bytes
        """
        payload = data if data is not None else [0]
        self._dev.ctrl_transfer(
            usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, cmd, 0x1C, payload, self._timeout
        )
