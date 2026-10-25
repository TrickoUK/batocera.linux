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
from batocera_launch_mame_common import precalibrate_mame_guns

from .base import MAMEBase
from .command import MAMECommand
from .controllers import MAMEControllers

if TYPE_CHECKING:
    from pathlib import Path

    from batocera_launch import Gun, LibretroConfig


@cached_dataclass
class MAME(MAMEControllers, MAMECommand, MAMEBase):
    @property
    def split_pump(self) -> bool:
        return self.config.get_bool('sinden_split_pump')

    @cached_property
    def rom_argument(self) -> str | Path | None:
        return self.cmd_filename

    def precalibrate_guns(self) -> None:
        if self.system != 'mame' or self.emulator.core != 'mame':
            return

        precalibrate_mame_guns(self.rom, self.emulator.gun_precalibration_dir, self.saves_dir / 'mame')

    def generate_special_configs(self) -> None:
        super().generate_special_configs()

        self.write_cmd_file()
        self.write_controllers_config()

    def set_core_options(self, core_options: LibretroConfig, /) -> None:
        if self.config.core != 'same_cdi':
            # Lightgun mode
            core_options.set('mame_lightgun_mode', 'lightgun' if self.config.use_guns and self.guns else 'disabled')

            # Enable cheats
            core_options.set('mame_cheats_enable', 'enabled')

            # CPU Overclock
            core_options.set_from_config('mame_cpu_overclock', default='default')

            # Video Resolution
            altres = self.config.get('mame_altres', '640x480')
            if altres == '1600x800':
                altres = '1600x900'
            core_options.set('mame_altres', altres)
            # The core ignores altres unless the alternate renderer is on
            core_options.set('mame_alternate_renderer', 'disabled' if altres == '640x480' else 'enabled')

            # PS1 GPU Hardware Rendering (Experimental)
            core_options.set_from_config('mame_psx_gpu_hle', default='disabled')

            # PS1 GPU PGXP Geometry Correction (Experimental)
            core_options.set_from_config('mame_psx_gpu_pgxp', default='disabled')

            # PS1 GPU 4x MSAA (Experimental)
            core_options.set_from_config('mame_psx_gpu_msaa', default='enabled')

            # PS1 GPU Texture Filtering (Experimental)
            core_options.set_from_config('mame_psx_gpu_texfilter', default='disabled')

            # PS1 GPU Exclude Sprites from Filtering (Experimental)
            core_options.set_from_config('mame_psx_gpu_filter_exclude_sprite', default='all')

            # PS1 GPU Exclude 2D Polygons from Filtering (Experimental)
            core_options.set_from_config('mame_psx_gpu_filter_exclude_2d_polygon', default='all')

            # 3D Supersampling (Enhancement: Voodoo, GTI Club, Model 2)
            core_options.set_from_config('mame_3d_supersample', default='disabled')

            # 3D Output Scale (Enhancement: Model 2, GTI Club, Hyper Neo Geo 64, GPU-drawn Voodoo)
            core_options.set_from_config('mame_3d_output_scale', default='native')

            # 3D GPU Rendering (Model 2, GTI Club, Hyper Neo Geo 64, Voodoo)
            core_options.set_from_config('mame_3d_gpu', default='disabled')

            # 3D Multisample Anti-Aliasing (GPU path: Voodoo, GTI Club, Model 2)
            core_options.set_from_config('mame_3d_msaa', default='disabled')

            # 3D Anisotropic Filtering (GPU path: Voodoo, GTI Club, Model 2, Namco System 22/23)
            core_options.set_from_config('mame_3d_aniso', default='disabled')

            # 3D Edge Anti-Aliasing (Enhancement: Voodoo)
            core_options.set_from_config('mame_3d_edge_aa', default='disabled')

            # 3D Texture Filtering (Enhancement: GTI Club)
            core_options.set_from_config('mame_3d_texfilter', default='disabled')

            # Gamepad steering assists for wheel games (override MAME's Machine Configuration)
            core_options.set_from_config('mame_steering_response', default='game')
            core_options.set_from_config('mame_steering_smoothing', default='game')
            core_options.set_from_config('mame_steering_input', default='game')
            core_options.set_from_config('mame_stick_steering_speed', default='game')

            # Disable controller profiling
            core_options.set('mame_buttons_profiles', 'disabled')

            # Software Lists (MESS)
            core_options.set('mame_softlists_enable', 'disabled')
            core_options.set('mame_softlists_auto_media', 'disabled')

            # Enable config reading (for controls)
            core_options.set('mame_read_config', 'enabled')

            # Use CLI (via CMD file) to boot
            core_options.set('mame_boot_from_cli', 'enabled')

            # Activate mouse for Mac & Archimedes
            core_options.set(
                'mame_mouse_enable', 'enabled' if self.system in {'macintosh', 'archimedes'} else 'disabled'
            )

        else:
            # Lightgun mode
            core_options.set('same_cdi_lightgun_mode', 'lightgun')

            # Enable cheats
            core_options.set('same_cdi_cheats_enable', 'enabled')

            # CPU Overclock
            core_options.set_from_config('same_cdi_cpu_overclock', default='default')

            # Video Resolution
            altres = self.config.get('same_cdi_altres', '640x480')
            if altres == '1600x800':
                altres = '1600x900'
            core_options.set('same_cdi_altres', altres)
            # The core ignores altres unless the alternate renderer is on
            core_options.set('same_cdi_alternate_renderer', 'disabled' if altres == '640x480' else 'enabled')

            # Disable controller profiling
            core_options.set('same_cdi_buttons_profiles', 'disabled')
            # Software Lists (MESS)
            core_options.set('same_cdi_softlists_enable', 'disabled')
            core_options.set('same_cdi_softlists_auto_media', 'disabled')
            # Enable config reading (for controls)
            core_options.set('same_cdi_read_config', 'enabled')
            # Use CLI (via CMD file) to boot
            core_options.set('same_cdi_boot_from_cli', 'enabled')
            # Activate mouse
            core_options.set('same_cdi_mouse_enable', 'enabled')

    def get_pedal_config_name_for_player(self, player_number: int, /) -> str:
        return f'input_player{player_number}_gun_aux_a'

    def set_gun_config_for_player(self, custom_config: LibretroConfig, player_number: int, gun: Gun, /) -> None:
        custom_config.set(f'input_player{player_number}_gun_offscreen_shot_mbtn', '')
        custom_config.set(f'input_player{player_number}_gun_aux_a_mbtn', 2)
        # Aux B (BUTTON3) stays on the default BTN_3 (mbtn 6): with sinden_split_pump the Sinden front left button
        # is BTN_3, see sinden_gun_modes
        custom_config.set(f'input_player{player_number}_start_mbtn', 3)
        custom_config.set(f'input_player{player_number}_select_mbtn', 4)
