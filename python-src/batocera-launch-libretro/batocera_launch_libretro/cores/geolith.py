from __future__ import annotations

from typing import TYPE_CHECKING

from batocera_common.dataclasses import cached_dataclass
from batocera_launch_libretro import Core

if TYPE_CHECKING:
    from batocera_launch import LibretroConfig


# SNK Neogeo AES/MVS / Neogeo CD (Geolith)
@cached_dataclass
class Geolith(Core):
    def set_core_options(self, core_options: LibretroConfig, /) -> None:
        core_options.set_from_config('geolith_system_type', default='aes')
        core_options.set_from_config('geolith_unibios_hw', default='mvs')
        core_options.set_from_config('geolith_region', default='us')
        core_options.set_from_config('geolith_aspect', default='1:1')
        core_options.set_from_config('geolith_memcard', default='on')
        core_options.set_from_config('geolith_palette', default='resnet')
        core_options.set_from_config('geolith_sprlimit', default='96')
        core_options.set_from_config('geolith_oc', default='off')

        if self.system == 'neogeocd':
            core_options.set_from_config('geolith_cd_system_type', default='cdz')
            core_options.set_from_config('geolith_cd_dma_len_limit', default='disabled')
