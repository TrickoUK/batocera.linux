from __future__ import annotations

from typing import TYPE_CHECKING

from ... import Command
from ...controller import generate_sdl_game_controller_config
from ..Generator import Generator
from . import gopher64Config
from .gopher64Paths import GOPHER64_BIN, GOPHER64_CACHE_HOME, GOPHER64_CONFIG_HOME, GOPHER64_DATA_HOME

if TYPE_CHECKING:
    from pathlib import Path

    from ...types import HotkeysContext


class Gopher64Generator(Generator):

    # Main entry of the module
    # Configure gopher64 and return a command
    def generate(self, system, rom, playersControllers, metadata, guns, wheels, gameResolution):
        gopher64Config.writeRetroAchievements(system)

        commandArray: list[str | Path] = [GOPHER64_BIN, rom, "--fullscreen"]

        if system.config.get_bool("gopher64_widescreen"):
            commandArray.append("--widescreen")

        if system.config.get_bool("gopher64_overclock"):
            commandArray.append("--overclock")

        if system.config.get_bool("gopher64_disable_expansion_pak"):
            commandArray.append("--disable-expansion-pak")

        # Note: gopher64's --load-state takes a numeric slot (0-9), not a
        # path, unlike batocera's usual `state_filename` (a full save-state
        # file path) - the two aren't compatible, so batocera's savestate
        # resume feature isn't wired up here.

        environment = {
            "XDG_CONFIG_HOME": GOPHER64_CONFIG_HOME,
            "XDG_DATA_HOME": GOPHER64_DATA_HOME,
            "XDG_CACHE_HOME": GOPHER64_CACHE_HOME,
            "SDL_GAMECONTROLLERCONFIG": generate_sdl_game_controller_config(playersControllers),
        }

        return Command.Command(array=commandArray, env=environment)

    def getHotkeysContext(self) -> HotkeysContext:
        return {
            "name": "gopher64",
            "keys": { "exit": ["KEY_LEFTALT", "KEY_F4"] }
        }
