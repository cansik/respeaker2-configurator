import os
import sys

# redirect stdout and stderr
# fixes https://github.com/huggingface/diffusers/issues/3290
if sys.stdout is None or sys.stderr is None:
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

# macOS packaging support
from multiprocessing import freeze_support  # noqa

freeze_support()  # noqa

from duit.ui.nicegui.NiceGUIPropertyPanel import NiceGUIPropertyPanel
from duit.ui.nicegui.NiceGUIPropertyRegistry import init_nicegui_registry
from nicegui import ui

from respeaker2.RespeakerConfig import RespeakerConfig
from respeaker2.RespeakerService import RespeakerService


def main():
    init_nicegui_registry()
    config = RespeakerConfig()

    service = RespeakerService()
    service.register(config)
    service.start_polling()

    @ui.page("/")
    def index_page():
        ui.markdown("## ReSpeaker2 Configurator")
        panel = NiceGUIPropertyPanel().classes("w-full")
        panel.data_context = config

    ui.run(title="ReSpeaker2 Configurator",
           native=True,
           window_size=(600, 800),
           reload=False,
           show_welcome_message=False
           )
    service.stop_polling()


if __name__ in {"__main__"}:
    main()
