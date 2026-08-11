from __future__ import annotations

from typing import TYPE_CHECKING

from ... import Command
from ...batoceraPaths import ensure_parents_and_open, mkdir_if_not_exists
from ...exceptions import BatoceraException
from ..Generator import Generator
from .aresControllers import generate_all_virtualpad_bindings
from .aresPaths import ARES_CONFIG_DIR, ARES_SAVES_DIR, ARES_SETTINGS_FILE

if TYPE_CHECKING:
    from ...types import HotkeysContext

# ares' own display name for each system (desktop-ui --system flag, and the
# information.name each core registers - see ares/n64/system/system.cpp,
# ares/sfc/system/system.cpp).
_ARES_SYSTEM_NAME = {
    'n64': 'Nintendo 64',
    'snes': 'Super Famicom',
}


def _write_bml_section(lines: list[str], name: str, values: dict[str, str], /) -> None:
    if not values:
        return
    lines.append(name)
    for key, value in values.items():
        lines.append(f'  {key}: {value}')


class AresGenerator(Generator):

    def getHotkeysContext(self) -> HotkeysContext:
        return {
            "name": "ares",
            "keys": {
                "exit": ["KEY_LEFTALT", "KEY_F4"],
                "save_state": "KEY_F2",
                "restore_state": "KEY_F1",
                "menu": "KEY_F7",
            }
        }

    def generate(self, system, rom, playersControllers, metadata, guns, wheels, gameResolution):
        ares_system = _ARES_SYSTEM_NAME.get(system.name)
        if ares_system is None:
            raise BatoceraException(f"ares: unsupported system '{system.name}'")

        mkdir_if_not_exists(ARES_CONFIG_DIR)
        mkdir_if_not_exists(ARES_SAVES_DIR)

        lines: list[str] = []

        _write_bml_section(lines, 'Video', {
            'Driver': 'OpenGL 3.2',
            'Shader': 'None',
            # "Scale" = aspect-correct best-fit (desktop-ui/program/platform.cpp's
            # Program::video()) - fills as much of the screen as the game's own
            # aspect ratio allows, only ever bordering a single axis. Set
            # explicitly rather than relying on Settings' own struct default
            # (also "Scale") to rule it out as the cause of any letterboxing
            # that doesn't match this - if a game still shows borders on
            # every side at once, that's real aspect mismatch (or the status
            # bar reserving space), not "Integer" mode's whole-number-only
            # scaling silently being in effect.
            'Output': 'Scale',
        })

        _write_bml_section(lines, 'General', {
            'NoFilePrompt': 'true',
            # ares' own overlay (game name / fps, at the bottom of the
            # window) isn't wanted for a frontend-launched game and reserves
            # vertical space that would otherwise go to the video output.
            'ShowStatusBar': 'false',
        })

        _write_bml_section(lines, 'Paths', {
            'Saves': str(ARES_SAVES_DIR) + '/',
        })

        for player_number, bindings in generate_all_virtualpad_bindings(playersControllers).items():
            _write_bml_section(lines, f'VirtualPad{player_number}', bindings)

        with ensure_parents_and_open(ARES_SETTINGS_FILE, 'w') as settingsFile:
            settingsFile.write('\n'.join(lines) + '\n')

        commandArray = [
            '/usr/bin/ares',
            '--fullscreen',
            '--no-file-prompt',
            '--system', ares_system,
            '--settings-file', ARES_SETTINGS_FILE,
            rom,
        ]

        return Command.Command(array=commandArray)
