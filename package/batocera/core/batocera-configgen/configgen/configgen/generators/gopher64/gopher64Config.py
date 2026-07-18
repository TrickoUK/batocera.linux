from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

from ...batoceraPaths import ensure_parents_and_open
from .gopher64Paths import GOPHER64_CONFIG_DIR

if TYPE_CHECKING:
    from ...Emulator import Emulator

gopher64Retroachievements: Final = GOPHER64_CONFIG_DIR / 'retroachievements.json'


# gopher64 reads RetroAchievements state from a standalone
# retroachievements.json (username/token/enabled/hardcore/...) rather
# than a live --ra-username/--ra-password login on every launch, so this
# writes that file directly from batocera's global RA settings - the
# same token-file approach ppssppConfig.writeRetroAchievements() uses.
def writeRetroAchievements(system: Emulator) -> None:
    if system.config.get_bool('retroachievements'):
        ra_config = {
            "username": system.config.get_str("retroachievements.username", ""),
            "token": system.config.get_str("retroachievements.token", ""),
            "enabled": True,
            "hardcore": system.config.get_bool("retroachievements.hardcore", False),
            "challenge": True,
            "leaderboard": True,
            "rich_presence": True,
        }
    else:
        ra_config = {
            "username": "",
            "token": "",
            "enabled": False,
            "hardcore": False,
            "challenge": False,
            "leaderboard": False,
            "rich_presence": False,
        }

    with ensure_parents_and_open(gopher64Retroachievements, 'w') as retroach_file:
        json.dump(ra_config, retroach_file)
