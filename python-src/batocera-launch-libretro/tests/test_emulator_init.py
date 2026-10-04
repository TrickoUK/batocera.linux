from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from batocera_launch_libretro import emulator as emulator_module
from batocera_launch_libretro.emulator import Libretro

if TYPE_CHECKING:
    import pytest


def test_libretro_runs_the_base_emulator_post_init(monkeypatch: pytest.MonkeyPatch) -> None:
    # Emulator.__post_init__ sets system/fancy_system_name/game_info_path; Libretro overrides
    # __post_init__, and without the super() call every libretro launch died in
    # Emulator.__aenter__ with "'Libretro' object has no attribute 'system'".
    monkeypatch.setattr(emulator_module, 'load_core', lambda emulator: MagicMock(emulator=emulator))

    config = MagicMock()
    config.system = 'pcengine'
    config.core = 'pce_fast'
    config.cli_args.systemname = 'PC Engine'
    config.cli_args.gameinfoxml = Path('/tmp/game.xml')

    emulator = Libretro(config, MagicMock())

    assert emulator.system == 'pcengine'
    assert emulator.fancy_system_name == 'PC Engine'
    assert emulator.game_info_path == Path('/tmp/game.xml')
    assert emulator.lr_core.emulator is emulator
