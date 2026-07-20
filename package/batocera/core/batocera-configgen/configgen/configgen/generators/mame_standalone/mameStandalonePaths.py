from __future__ import annotations

from typing import Final

from ...batoceraPaths import CONFIGS, SAVES

# Deliberately separate from mame.mamePaths' MAME_CONFIG/MAME_SAVES: the two
# MAME builds can disagree on cfg-XML schema version and NVRAM/state binary
# layout, so cfg/save state is never shared between them. BIOS/ROMs/cheats
# ARE shared (see mameStandaloneGenerator.py) since those are romset-format
# driven, not MAME-fork driven. See ADD-STANDALONE-MAME.md.
MAME_STANDALONE_CONFIG: Final = CONFIGS / "standalone-mame"
MAME_STANDALONE_SAVES: Final = SAVES / "standalone-mame"
