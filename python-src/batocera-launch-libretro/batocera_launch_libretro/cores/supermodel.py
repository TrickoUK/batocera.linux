from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from batocera_common.dataclasses import cached_dataclass
from batocera_launch_libretro import Core

if TYPE_CHECKING:
    from batocera_launch import LibretroConfig


# Sega Model 3 (Supermodel)
@cached_dataclass
class Supermodel(Core):
    gun_mapping: ClassVar = {'default': {'device': 1, 'p1': 0, 'p2': 1}}

    def override_default_gfx_backend(self, default_gfx_backend: str, /) -> str | None:
        # supermodel's New3D engine asks for a core profile; its Legacy3D engine needs a compatibility one
        if default_gfx_backend in ('gl', 'glcore'):
            return 'gl' if self.config.get('supermodel_renderer_3d') == 'legacy3d' else 'glcore'

        return super().override_default_gfx_backend(default_gfx_backend)

    def set_core_options(self, core_options: LibretroConfig, /) -> None:
        # Graphics
        core_options.set_from_config('supermodel_resolution', default='native')
        core_options.set_from_config('supermodel_supersampling', default='1')
        core_options.set_from_config('supermodel_wide_screen', default='disabled')
        core_options.set_from_config('supermodel_crt_colors', default='0')
        core_options.set_from_config('supermodel_upscale_mode', default='2')
        core_options.set_from_config('supermodel_no_white_flash', default='disabled')
        core_options.set_from_config('supermodel_av_timing', default='60hz')
        core_options.set_from_config('supermodel_renderer_3d', default='new3d')
        core_options.set_from_config('supermodel_quad_rendering', default='disabled')

        # Light gun
        core_options.set_from_config('supermodel_crosshairs', default='3' if self.emulator.guns_need_crosses else '0')
        core_options.set_from_config('supermodel_gun_input', default='hybrid')
        core_options.set_from_config('supermodel_star_wars_input', default='hybrid')

        # Driving
        core_options.set_from_config('supermodel_force_feedback', default='enabled')
        core_options.set_from_config('supermodel_four_speed_shifter', default='h_gate')
        core_options.set_from_config('supermodel_steering_response', default='linear')
        core_options.set_from_config('supermodel_steering_output_range', default='100')
        core_options.set_from_config('supermodel_accelerator_output_range', default='100')
        core_options.set_from_config('supermodel_brake_output_range', default='100')

        # Audio
        core_options.set_from_config('supermodel_sound_volume', default='100')
        core_options.set_from_config('supermodel_music_volume', default='100')
        core_options.set_from_config('supermodel_scsp_dsp', default='new')

        # Advanced
        core_options.set_from_config('supermodel_ppc_frequency', default='auto')
        core_options.set_from_config('supermodel_emulation_threading', default='multi_gpu')
        core_options.set_from_config('supermodel_frameskip', default='0')
        core_options.set_from_config('supermodel_network_board', default='enabled')
        core_options.set_from_config('supermodel_initial_nvram_setup', default='enabled')
        core_options.set_from_config('supermodel_timing_overlay', default='disabled')
