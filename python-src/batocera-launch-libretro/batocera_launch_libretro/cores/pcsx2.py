from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from batocera_common.dataclasses import cached_dataclass
from batocera_launch_libretro import Core, GLCoreForceMixin

if TYPE_CHECKING:
    from batocera_launch import LibretroConfig


@cached_dataclass
class Pcsx2(GLCoreForceMixin, Core):
    gun_mapping: ClassVar = {'default': {'device': 4, 'p1': 0, 'p2': 1}}

    def set_core_options(self, core_options: LibretroConfig, /) -> None:
        # Fast Boot
        core_options.set_from_config('pcsx2_fastboot', 'lr_pcsx2_fast_boot', default='disabled')
        # Fast CD/DVD Access
        core_options.set_from_config('pcsx2_fastcdvd', 'lr_pcsx2_fast_cdvd', default='disabled')
        # Shared Memory Cards
        core_options.set_from_config('pcsx2_shared_memory_cards', 'lr_pcsx2_shared_memory_cards', default='disabled')
        # Enable Cheats
        core_options.set_from_config('pcsx2_enable_cheats', 'lr_pcsx2_cheats', default='disabled')
        # Language Unlock
        core_options.set_from_config('pcsx2_hint_language_unlock', 'lr_pcsx2_language_unlock', default='disabled')
        # Use External Game Database
        core_options.set_from_config(
            'pcsx2_use_external_gameindex', 'lr_pcsx2_use_external_gameindex', default='disabled'
        )
        # Graphics API / GS Renderer
        renderer = self.config.get('lr_pcsx2_renderer', 'Auto')
        if renderer == 'Auto':
            renderer = 'Vulkan' if self.config.get('gfxbackend') == 'vulkan' else 'OpenGL'
        core_options.set('pcsx2_renderer', renderer)
        # Render resolution
        core_options.set_from_config('pcsx2_upscale_multiplier', 'lr_pcsx2_resolution', default='1x Native (PS2)')
        # Texture Filtering
        core_options.set_from_config('pcsx2_texture_filtering', 'lr_pcsx2_texture_filtering', default='Bilinear (PS2)')
        # Trilinear Filtering
        core_options.set_from_config('pcsx2_trilinear_filtering', 'lr_pcsx2_trilinear_filtering', default='Automatic')
        # Anisotropic Filtering
        core_options.set_from_config('pcsx2_anisotropic_filtering', 'lr_pcsx2_anisotropic', default='disabled')
        # Dithering
        core_options.set_from_config('pcsx2_dithering', 'lr_pcsx2_dithering', default='Unscaled')
        # Blending Accuracy
        core_options.set_from_config('pcsx2_blending_accuracy', 'lr_pcsx2_blending', default='Basic')
        # paraLLEl-GS: Super Sampling
        core_options.set_from_config('pcsx2_pgs_ssaa', 'lr_pcsx2_pgs_ssaa', default='Native')
        # paraLLEl-GS: High-res Scanout
        core_options.set_from_config('pcsx2_pgs_high_res_scanout', 'lr_pcsx2_pgs_high_res_scanout', default='disabled')
        # paraLLEl-GS: SSAA Texture
        core_options.set_from_config('pcsx2_pgs_ss_tex', 'lr_pcsx2_pgs_ss_tex', default='disabled')
        # paraLLEl-GS: Sharp Backbuffer
        core_options.set_from_config('pcsx2_pgs_deblur', 'lr_pcsx2_pgs_deblur', default='disabled')
        # paraLLEl-GS: Force Texture LOD0
        core_options.set_from_config('pcsx2_pgs_disable_mipmaps', 'lr_pcsx2_pgs_disable_mipmaps', default='disabled')
        # Deinterlacing
        core_options.set_from_config('pcsx2_deinterlace_mode', 'lr_pcsx2_deinterlace_mode', default='Automatic')
        # Hardware Download Mode
        core_options.set_from_config('pcsx2_hw_download_mode', 'lr_pcsx2_hw_download_mode', default='Accurate')
        # No Interlacing hint
        core_options.set_from_config('pcsx2_nointerlacing_hint', 'lr_pcsx2_nointerlacing_hint', default='enabled')
        # PCRTC Anti-Blur
        core_options.set_from_config('pcsx2_pcrtc_antiblur', 'lr_pcsx2_pcrtc_antiblur', default='enabled')
        # PCRTC Screen Offsets
        core_options.set_from_config('pcsx2_pcrtc_screen_offsets', 'lr_pcsx2_pcrtc_screen_offsets', default='disabled')
        # Disable Interlace Offset
        core_options.set_from_config(
            'pcsx2_disable_interlace_offset', 'lr_pcsx2_disable_interlace_offset', default='disabled'
        )
        # Auto Flush (Software)
        core_options.set_from_config('pcsx2_auto_flush_software', 'lr_pcsx2_auto_flush_software', default='enabled')
        # EE Cycle Rate
        core_options.set_from_config('pcsx2_ee_cycle_rate', 'lr_pcsx2_ee_cycle_rate', default='100% (Normal Speed)')
        # MTVU (Multi-Threaded VU1)
        core_options.set_from_config('pcsx2_mtvu', 'lr_pcsx2_mtvu', default='enabled')
        # Instant VU1
        core_options.set_from_config('pcsx2_instant_vu1', 'lr_pcsx2_instant_vu1', default='enabled')
        # EE Cycle Skipping
        core_options.set_from_config('pcsx2_ee_cycle_skip', 'lr_pcsx2_ee_cycle_skip', default='disabled')
        # Game Enhancements hint
        core_options.set_from_config(
            'pcsx2_game_enhancements_hint', 'lr_pcsx2_game_enhancements_hint', default='disabled'
        )
        # Uncapped Framerate hint
        core_options.set_from_config(
            'pcsx2_uncapped_framerate_hint', 'lr_pcsx2_uncapped_framerate_hint', default='disabled'
        )
        # Start in Analog Mode (per port)
        core_options.set_from_config('pcsx2_analog_mode1', 'lr_pcsx2_analog_mode1', default='disabled')
        core_options.set_from_config('pcsx2_analog_mode2', 'lr_pcsx2_analog_mode2', default='disabled')
        # Widescreen hint
        core_options.set_from_config('pcsx2_widescreen_hint', 'lr_pcsx2_widescreen_hint', default='disabled')
