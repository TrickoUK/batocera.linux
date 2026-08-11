from __future__ import annotations

from typing import Final

from ...batoceraPaths import CONFIGS, SAVES

ARES_CONFIG_DIR: Final = CONFIGS / 'ares'
ARES_SETTINGS_FILE: Final = ARES_CONFIG_DIR / 'settings.bml'
ARES_SAVES_DIR: Final = SAVES / 'ares'

# ares has no CLI/settings override for its shader search directory - it's
# always resolved via locate("Shaders/") (desktop-ui/program/drivers.cpp),
# which checks $XDG_DATA_HOME/ares/Shaders/ as one of its fixed candidate
# paths. Pointing XDG_DATA_HOME at CONFIGS (ares.mk's launch env) makes that
# resolve to exactly this directory, giving us a stable, writable location
# to stage the currently-selected shader into.
ARES_DATA_HOME: Final = CONFIGS
ARES_SHADERS_DIR: Final = ARES_CONFIG_DIR / 'Shaders'
ARES_ACTIVE_SHADER: Final = ARES_SHADERS_DIR / 'active.slangp'
