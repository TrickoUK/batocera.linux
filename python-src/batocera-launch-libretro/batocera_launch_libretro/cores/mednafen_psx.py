from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal

from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_launch_libretro import RACore

if TYPE_CHECKING:
    from batocera_launch import Controller, Gun, LibretroConfig


@cached_dataclass
class MednafenPsx(RACore):
    gun_mapping: ClassVar = {
        'default': {
            'device': 260,
            'p1': 0,
            'p2': 1,
            'gameDependant': [{'key': 'type', 'value': 'justifier', 'mapkey': 'device', 'mapvalue': '516'}],
        }
    }

    @cached_property
    def player1_device_type(self) -> str | None:
        return self.config.get_str('beetle_psx_hw_Controller1') or None

    @cached_property
    def player2_device_type(self) -> str | None:
        return self.config.get_str('beetle_psx_hw_Controller2') or None

    def get_analog_mode(self, controller: Controller, /) -> Literal['0', '1']:
        if controller.player_number == 1 and (psx_controller_1 := self.config.get('beetle_psx_hw_Controller1')):
            return '0' if psx_controller_1 != '1' else '1'

        if controller.player_number == 2 and (psx_controller_2 := self.config.get('beetle_psx_hw_Controller2')):
            return '0' if psx_controller_2 != '1' else '1'

        return super().get_analog_mode(controller)

    def set_core_options(self, core_options: LibretroConfig, /) -> None:
        # --- System ---

        # Show official Bootlogo
        core_options.set_from_config('beetle_psx_hw_skip_bios', default='disabled')

        # CPU Frequency Scaling (Overclock)
        core_options.set_from_config(
            'beetle_psx_hw_cpu_freq_scale', default='110%'
        )  # If not 110% NO options are working!

        # CD Access Method
        core_options.set_from_config('beetle_psx_hw_cd_access_method', default='sync')

        # CD Loading Speed
        core_options.set_from_config('beetle_psx_hw_cd_fastload', default='2x(native)')

        # Analog Stick self calibration
        core_options.set_from_config('beetle_psx_hw_analog_calibration', default='disabled')

        # --- Video ---

        # Video Resolution
        core_options.set_from_config('beetle_psx_hw_internal_resolution', default='1x(native)')

        # Core Aspect Ratio
        core_options.set_from_config('beetle_psx_hw_aspect_ratio', default='corrected')

        # Renderer
        core_options.set_from_config('beetle_psx_hw_renderer', default='hardware')

        # Software Framebuffer
        core_options.set_from_config('beetle_psx_hw_renderer_software_fb', default='enabled')

        # Internal Color Depth
        core_options.set_from_config('beetle_psx_hw_depth', default='16bpp(native)')

        # Dithering Pattern
        core_options.set_from_config('beetle_psx_hw_dither_mode', default='1x(native)')

        # Texture Filtering
        core_options.set_from_config('beetle_psx_hw_filter', default='nearest')

        # Exclude Sprites from Filtering (Vulkan)
        core_options.set_from_config('beetle_psx_hw_filter_exclude_sprite', default='disabled')

        # Exclude 2D Polygons from Filtering (Vulkan)
        core_options.set_from_config('beetle_psx_hw_filter_exclude_2d_polygon', default='disabled')

        # Adaptive Smoothing (Vulkan)
        core_options.set_from_config('beetle_psx_hw_adaptive_smoothing', default='disabled')

        # Supersampling (Vulkan)
        core_options.set_from_config('beetle_psx_hw_super_sampling', default='disabled')

        # Multi-Sampled Anti Aliasing (Vulkan)
        core_options.set_from_config('beetle_psx_hw_msaa', default='1x')

        # MDEC YUV Chroma Filter (Vulkan)
        core_options.set_from_config('beetle_psx_hw_mdec_yuv', default='disabled')

        # Deinterlace Method
        core_options.set_from_config('beetle_psx_hw_deinterlacer', default='weave')

        # PAL Video Timing Override
        core_options.set_from_config('beetle_psx_hw_pal_video_timing_override', default='disabled')

        # Frame Duping (Speedup)
        core_options.set_from_config('beetle_psx_hw_frame_duping', default='disabled')

        # --- PGXP (Precision Geometry Transform Pipeline) ---

        # PGXP Operation Mode
        core_options.set_from_config('beetle_psx_hw_pgxp_mode', default='disabled')

        # PGXP 2D Geometry Tolerance
        core_options.set_from_config('beetle_psx_hw_pgxp_2d_tol', default='disabled')

        # PGXP Primitive Culling
        core_options.set_from_config('beetle_psx_hw_pgxp_nclip', default='disabled')

        # PGXP Vertex Cache
        core_options.set_from_config('beetle_psx_hw_pgxp_vertex', default='disabled')

        # PGXP Perspective Correct Texturing
        core_options.set_from_config('beetle_psx_hw_pgxp_texture', default='disabled')

        # --- Emulation Hacks ---

        # Line-to-Quad Hack
        core_options.set_from_config('beetle_psx_hw_line_render', default='default')

        # Widescreen Hack
        if (
            self.config.get('beetle_psx_hw_widescreen_hack') == 'enabled'
            and self.config.get('ratio') == '16/9'
            and self.config.get('bezel') == 'none'
        ):
            core_options.set('beetle_psx_hw_widescreen_hack', 'enabled')
        else:
            core_options.set('beetle_psx_hw_widescreen_hack', 'disabled')

        # Widescreen Hack Aspect Ratio
        core_options.set_from_config('beetle_psx_hw_widescreen_hack_aspect_ratio', default='16:9')

        # CPU Dynarec (Speedup)
        core_options.set_from_config('beetle_psx_hw_cpu_dynarec', default='disabled')

        # Dynarec Code Invalidation
        core_options.set_from_config('beetle_psx_hw_dynarec_invalidate', default='full')

        # Multitap
        match self.config.get('multitap_mednafen'):
            case 'port1':
                core_options.set('beetle_psx_hw_enable_multitap_port1', 'enabled')
                core_options.set('beetle_psx_hw_enable_multitap_port2', 'disabled')
            case 'port2':
                core_options.set('beetle_psx_hw_enable_multitap_port1', 'disabled')
                core_options.set('beetle_psx_hw_enable_multitap_port2', 'enabled')
            case 'port12':
                core_options.set('beetle_psx_hw_enable_multitap_port1', 'enabled')
                core_options.set('beetle_psx_hw_enable_multitap_port2', 'enabled')
            case _:
                core_options.set('beetle_psx_hw_enable_multitap_port1', 'disabled')
                core_options.set('beetle_psx_hw_enable_multitap_port2', 'disabled')

    def get_pedal_config_name_for_player(self, player_number: int, /) -> str:
        return f'input_player{player_number}_gun_aux_a'

    def set_gun_config_for_player(self, custom_config: LibretroConfig, player_number: int, gun: Gun, /) -> None:
        if self.metadata.get('gun_type') == 'justifier':
            custom_config.set(f'input_player{player_number}_gun_offscreen_shot_mbtn', '')
            custom_config.set(f'input_player{player_number}_gun_aux_a_mbtn', 2)
        else:
            custom_config.set(f'input_player{player_number}_gun_offscreen_shot_mbtn', '')
            custom_config.set(f'input_player{player_number}_gun_start_mbtn', '')
            custom_config.set(f'input_player{player_number}_gun_aux_a_mbtn', 2)
            custom_config.set(f'input_player{player_number}_gun_aux_b_mbtn', 3)
