import os
import sys
from datetime import datetime
from multiprocessing import freeze_support
from typing import Optional

from duit.annotation.AnnotationFinder import AnnotationFinder

from respeaker2.RespeakerParam import RespeakerParam

# suppress stdout/stderr and macOS in frozen builds
if sys.stdout is None or sys.stderr is None:
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")
freeze_support()

from duit.model.DataField import DataField  # noqa: E402
from duit.ui.nicegui.NiceGUIPropertyPanel import NiceGUIPropertyPanel  # noqa: E402
from duit.ui.nicegui.NiceGUIPropertyRegistry import init_nicegui_registry  # noqa: E402
from nicegui import app, ui  # noqa: E402

from respeaker2.RespeakerConfig import RespeakerConfig  # noqa: E402
from respeaker2.RespeakerService import RespeakerService  # noqa: E402


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
        self._reset_button: Optional[ui.button] = None

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

    def _on_reset_pressed(self):
        default_config = RespeakerConfig()

        finder = AnnotationFinder(RespeakerParam)
        defaults = finder.find(default_config)
        currents = finder.find(self.config)

        # collect matching pairs by name
        matches = {}
        for name, (df_default, anno_default) in defaults.items():
            if name in currents:
                df_current, anno_current = currents[name]
                matches[name] = (df_default, df_current)

        # now you can update all df
        for name, (df_default, df_current) in matches.items():
            df_current.value = df_default.value

        # update all df
        ui.notify("Configuration has been reset!", color="positive")

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

        with ui.row(align_items="center"):
            self._reset_button = ui.button("Reset Config", on_click=self._on_reset_pressed)

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

    def on_window_closed(self):
        # cleanup
        self.service.close()

    def run(self) -> None:
        @ui.page("/")
        def index_page():
            self.create_ui()
            self.apply_status()

        app.on_startup(self.on_startup)
        app.on_connect(self.on_window_opened)
        app.on_shutdown(self.on_window_closed)

        ui.run(
            title="ReSpeaker2 Configurator",
            native=True,
            window_size=(600, 800),
            reload=False,
            show_welcome_message=False
        )


def main():
    App().run()


if __name__ == "__main__":
    main()
