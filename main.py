import os
import sys
from datetime import datetime
from multiprocessing import freeze_support
from typing import Optional

# suppress stdout/stderr and macOS in frozen builds
if sys.stdout is None or sys.stderr is None:
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")
freeze_support()

from duit.model.DataField import DataField
from duit.ui.nicegui.NiceGUIPropertyPanel import NiceGUIPropertyPanel
from duit.ui.nicegui.NiceGUIPropertyRegistry import init_nicegui_registry
from nicegui import app, ui

from respeaker2.RespeakerConfig import RespeakerConfig
from respeaker2.RespeakerService import RespeakerService


class App:

    def __init__(self) -> None:
        # UI registry
        init_nicegui_registry()

        # Model + service
        self.config = RespeakerConfig()
        self.service = RespeakerService()
        self.service.register(self.config)

        # Connection state DataField
        self.is_connected = DataField(self.service.connected)
        self.is_connected.on_changed += lambda _: self.apply_status()

        self.service.on_connected += self._on_connected
        self.service.on_disconnected += self._on_disconnected
        self.service.on_error += self._on_error
        self.service.on_poll += self.on_poll

        # create a hidden container for notifications
        # any UI actions inside this `with` block will be attached to the page slot
        self._notify_slot: Optional[ui.column] = None
        self._last_updated_label: Optional[ui.label] = None
        self._status_label: Optional[ui.label] = None
        self._status_icon: Optional[ui.icon] = None

        self.is_first_run = True

    def _on_connected(self, _):
        self.is_connected.value = True
        self.notify_ui("Device connected!", type="positive")

    def _on_disconnected(self, _):
        self.is_connected.value = False
        self.notify_ui("Device disconnected!", type="info")

    def _on_error(self, message: str) -> None:
        """Schedule a notify on the UI thread to avoid background‐thread UI calls."""
        sys.stderr.write(f"Error: {message}\n")
        self.notify_ui(f"Error: {message}", type="negative")

    def apply_status(self):
        if self.is_connected.value:
            self._status_label.text = "Connected"
            self._status_icon.name = "usb"
            self._status_icon.classes("text-green-700")
        else:
            self._status_label.text = "Disconnected"
            self._status_icon.name = "usb_off"
            self._status_icon.classes("text-red-700")

    def on_poll(self, _):
        date_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._last_updated_label.text = f"Updated: {date_str}"

    def notify_ui(self, message: str, *args, **kwargs):
        with self._notify_slot:
            ui.notify(message, *args, **kwargs)

    def create_ui(self) -> None:
        self._notify_slot = ui.column().style("display: none")

        ui.markdown("### ReSpeaker2 Configurator")

        # Connection Panel
        with ui.row(align_items="center"):
            self._status_label = ui.label("-").classes("text-lg")
            self._status_icon = ui.icon("-").classes("text-lg")

        with ui.row(align_items="center"):
            self._last_updated_label = ui.label("-").classes("text-sm")

        ui.separator().classes("my-1")

        # Parameters panel
        panel = NiceGUIPropertyPanel().classes("w-full")
        panel.data_context = self.config

    def on_startup(self):
        pass

    def on_window_opened(self):
        if not self.is_first_run:
            return
        self.is_first_run = False
        self.service.connect()

    def run(self) -> None:
        @ui.page("/")
        def index_page():
            self.create_ui()
            self.apply_status()

        app.on_startup(self.on_startup)
        app.on_connect(self.on_window_opened)

        ui.run(
            title="ReSpeaker2 Configurator",
            native=True,
            window_size=(600, 800),
            reload=False,
            show_welcome_message=False,
        )

        # cleanup
        self.service.close()


def main():
    App().run()


if __name__ == "__main__":
    main()
