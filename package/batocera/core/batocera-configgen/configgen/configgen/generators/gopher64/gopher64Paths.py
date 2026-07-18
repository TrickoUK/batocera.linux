from __future__ import annotations

from pathlib import Path
from typing import Final

from ...batoceraPaths import CACHE, CONFIGS, SAVES

GOPHER64_BIN: Final = Path('/usr/bin/gopher64')

# gopher64 resolves its own config/data/cache dirs via the Rust `dirs`
# crate (dirs::config_dir()/data_dir()/cache_dir(), each with a
# "gopher64" subdirectory appended by the app itself), which honors
# XDG_CONFIG_HOME/XDG_DATA_HOME/XDG_CACHE_HOME - point those roots at
# batocera's own tree rather than the app's usual $HOME-based defaults.
GOPHER64_CONFIG_HOME: Final = CONFIGS
GOPHER64_DATA_HOME: Final = SAVES / 'n64'
GOPHER64_CACHE_HOME: Final = CACHE

# Resolved directories (CONFIG_HOME/DATA_HOME/CACHE_HOME + the "gopher64"
# subdirectory the app appends itself), used when configgen needs to
# read/write files inside them directly (e.g. retroachievements.json)
# ahead of launch.
GOPHER64_CONFIG_DIR: Final = GOPHER64_CONFIG_HOME / 'gopher64'
GOPHER64_DATA_DIR: Final = GOPHER64_DATA_HOME / 'gopher64'
