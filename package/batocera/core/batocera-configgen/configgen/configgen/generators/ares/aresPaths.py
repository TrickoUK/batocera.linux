from __future__ import annotations

from typing import Final

ARES_BIN: Final = "/usr/bin/ares"

# ares (per its own mia/medium/*.cpp Medium::name() overrides, confirmed
# directly against upstream ares-emulator/ares source) identifies each system
# by a specific human-readable string passed to --system. Passed explicitly
# here rather than relying on ares' own extension-based auto-detection, since
# several of these systems share an extension (e.g. .bin, .zip, .cue) with
# another system ares also supports.
ARES_SYSTEM_NAMES: Final[dict[str, str]] = {
    "nes": "Famicom",
    "snes": "Super Famicom",
    "mastersystem": "Master System",
    "megadrive": "Mega Drive",
    "megacd": "Mega CD",
    "sega32x": "Mega 32X",
    "pcengine": "PC Engine",
    "pcenginecd": "PC Engine CD",
    "supergrafx": "SuperGrafx",
    "n64": "Nintendo 64",
}
