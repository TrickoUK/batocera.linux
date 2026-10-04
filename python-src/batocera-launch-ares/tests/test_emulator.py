from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from batocera_launch_ares import emulator as ares_module
from batocera_launch_ares.emulator import Ares

from batocera_launch import BatoceraException, Emulator, Input, emulator as base_module
from batocera_launch.rom import Rom

if TYPE_CHECKING:
    from collections.abc import Mapping


def _make_ares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, system: str, options: Mapping[str, str], state_slot: str | None
) -> Ares:
    monkeypatch.setattr(base_module, 'CONFIGS', tmp_path / 'configs')
    monkeypatch.setattr(ares_module, 'SAVES', tmp_path / 'saves')
    monkeypatch.setattr(ares_module, '_ARES_DATA_HOME', tmp_path / 'configs')

    config = MagicMock()
    config.system = system
    config.emulator = 'ares'
    config.state_slot = state_slot
    config.get_str.side_effect = lambda key, default=None: options.get(key, default)
    config.render_config.get.return_value = None

    emulator = Ares(config, MagicMock())
    emulator.rom = Rom(Path('/userdata/roms/n64/game.z64'), None)

    controller = MagicMock()
    controller.guid = 'guid'
    controller.player_number = 1
    controller.inputs = {
        'a': Input(name='a', type='button', id='0', value='1'),
        'up': Input(name='up', type='hat', id='0', value='1'),
    }
    emulator.controllers = [controller]
    return emulator


def test_ares_entry_point_resolves() -> None:
    assert Emulator._load_class('ares') is Ares  # pyright: ignore[reportPrivateUsage]


def test_ares_configure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_ares(tmp_path, monkeypatch, 'n64', {'ares_n64_quality': 'HD'}, '3')

    # Emulator.__post_init__ must have run (system is used for the ares system name and save folders)
    assert emulator.system == 'n64'

    command = asyncio.run(emulator.configure())

    settings_file = tmp_path / 'configs' / 'ares' / 'settings.bml'
    assert command.args == [
        '/usr/bin/ares',
        '--fullscreen',
        '--no-file-prompt',
        '--system',
        'Nintendo 64',
        '--settings-file',
        settings_file,
        '--save-state',
        '3',
        emulator.rom,
    ]
    assert command.env == {'XDG_DATA_HOME': tmp_path / 'configs', 'ARES_BATOCERA_SYSTEM_ID': 'n64'}

    settings = settings_file.read_text()
    assert f'  Saves: {tmp_path}/saves/ares/\n' in settings
    assert '  Quality: HD\n' in settings
    assert '  SaveState: 0x1/0/2\n' in settings
    assert 'VirtualPad1\n  Pad.Up: guid/0/1/1/Lo\n  B..East: guid/0/3/0\n' in settings


def test_ares_rejects_unsupported_system(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_ares(tmp_path, monkeypatch, 'psx', {}, None)

    with pytest.raises(BatoceraException, match='unsupported system'):
        asyncio.run(emulator.configure())
