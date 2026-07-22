from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ... import Command
from ...batoceraPaths import CACHE, CONFIGS, SAVES
from ..Generator import Generator
from .aresPaths import ARES_BIN, ARES_SYSTEM_NAMES

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ...config import SystemConfig
    from ...controller import Controllers
    from ...Emulator import Emulator
    from ...gun import Guns
    from ...types import DeviceInfoMapping, HotkeysContext, Resolution


class AresGenerator(Generator):
    """
    ares (https://ares-emu.net), a higan/bsnes-descended multi-system
    emulator, registered as an extra opt-in emulator for several systems that
    already have a different default here - see ADD-ARES.md. A direct
    Generator subclass: unlike MAME's many-system MESS branch, ares has no
    existing batocera generator to share code with.

    Known open items, not yet confirmed against a real launch (see
    ADD-ARES.md): whether the XDG_* redirection below actually lands ares'
    settings/saves under batocera's own CONFIGS/SAVES tree (vs. ares' own
    nall-based path resolution using something else entirely), and how
    firmware/BIOS files for Mega CD/32X/PC Engine CD need to be placed for
    ares specifically - ares uses its own per-system "System" firmware
    folder layout (inherited from higan), not a single shared BIOS file
    convention.
    """

    def getHotkeysContext(self) -> HotkeysContext:
        return {
            "name": "ares",
            "keys": { "exit": ["KEY_LEFTALT", "KEY_F4"] }
        }

    def generate(
        self,
        system: Emulator,
        rom: Path,
        playersControllers: Controllers,
        metadata: Mapping[str, str],
        guns: Guns,
        wheels: DeviceInfoMapping,
        gameResolution: Resolution,
    ) -> Command.Command:
        commandArray: list[str | Path] = [ARES_BIN]

        if aresSystemName := ARES_SYSTEM_NAMES.get(system.name):
            commandArray += ["--system", aresSystemName]

        commandArray += ["--no-file-prompt", "--fullscreen", rom]

        return Command.Command(
            array=commandArray,
            env={
                "XDG_CONFIG_HOME": CONFIGS,
                "XDG_DATA_HOME": SAVES,
                "XDG_CACHE_HOME": CACHE,
            }
        )

    def supportsInternalBezels(self) -> bool:
        return False
