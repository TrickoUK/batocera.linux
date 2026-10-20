# This file is part of The Batocera Linux Distribution (https://batocera.org).
# Copyright (c) 2026 The Batocera Team.
#
# The Batocera Linux Distribution is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# The Batocera Linux Distribution is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with The Batocera Linux Distribution. If not, see
# <https://www.gnu.org/licenses/>.
#
# YOU MUST RETAIN THE LICENSE AND COPYRIGHT NOTICES ABOVE IN ANY
# REDISTRIBUTED VERSION OF THIS FILE.

from __future__ import annotations

from typing import TYPE_CHECKING

from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_launch import Emulator, HotkeysContext, SpecialDecorationsMixin
from batocera_launch_mame_common import (
    MameControlScheme,
    MessSystemInfo,
    load_all_mame_control_mappings,
    load_mame_control_scheme,
)
from batocera_launch_mame_common.paths import MAME_BIN_DIR, MAMEPathsMixin

if TYPE_CHECKING:
    from pathlib import Path


@cached_dataclass
class MAMEBase(MAMEPathsMixin, SpecialDecorationsMixin, Emulator):  # pyright: ignore[reportIncompatibleVariableOverride]
    @property
    def handles_bezels(self) -> bool:
        return True

    @property
    def execution_path(self) -> Path | None:
        # Change directory to MAME folder (allows data plugin to load properly)
        return MAME_BIN_DIR

    @cached_property
    def hotkeygen_context(self) -> HotkeysContext:
        return {
            'name': 'mame',
            'keys': {
                'exit': 'KEY_ESC',
                'menu': 'KEY_TAB',
                'pause': 'KEY_F5',
                'reset': 'KEY_F3',
                'coin': 'KEY_5',
                'fastforward': 'KEY_PAGEDOWN',
                'save_state': ['KEY_LEFTSHIFT', 'KEY_F6'],
                'restore_state': ['KEY_LEFTSHIFT', 'KEY_F7'],
            },
        }

    @cached_property
    def mess_system_info(self) -> MessSystemInfo | None:
        return MessSystemInfo.load(self.system)

    @cached_property
    def bezel_set(self) -> str | None:
        bezel_set = self.config.get_str('bezel') or None

        if self.config.get_bool('forceNoBezel'):
            bezel_set = None

        return bezel_set

    @cached_property
    def use_mouse(self) -> bool:
        mess_system = self.mess_system_info
        return self.config.get_bool('use_mouse') or not (mess_system is None or not mess_system.name)

    @cached_property
    def mame_control_scheme(self) -> MameControlScheme:
        return load_mame_control_scheme(self.config.get_str('altlayout', 'auto'), self.rom.stem)

    @property
    def split_pump(self) -> bool:
        return self.config.get_bool('sinden_split_pump')

    @cached_property
    def all_mame_control_mappings(self) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        control_mapping, gun_mapping, mouse_mapping = load_all_mame_control_mappings(
            self.mame_control_scheme, self.config.use_guns, self.use_mouse
        )

        if self.split_pump and gun_mapping:
            # with split pump (sinden_gun_modes) the Sinden front left is BTN_3 (gun BUTTON6), not front right BTN_2
            # (gun BUTTON5): BTN_3 takes the game's BUTTON3 and BTN_2 moves to BUTTON4
            gun_mapping['BUTTON3'] = 'BUTTON6'
            gun_mapping['BUTTON4'] = 'BUTTON5'

        return control_mapping, gun_mapping, mouse_mapping
