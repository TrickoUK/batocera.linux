from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from batocera_launch_namco2x import emulator as namco2x_module
from batocera_launch_namco2x.emulator import Namco2x

from batocera_launch import BatoceraException, Emulator
from batocera_launch.rom import Rom

if TYPE_CHECKING:
    from collections.abc import Mapping


def _gun(*, needs_borders: bool, needs_cross: bool) -> MagicMock:
    gun = MagicMock()
    gun.needs_borders = needs_borders
    gun.needs_cross = needs_cross
    return gun


def _make_namco2x(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rom_name: str,
    options: Mapping[str, str],
    *,
    use_guns: bool = False,
    guns: list[MagicMock] | None = None,
    global_options: Mapping[str, str] | None = None,
) -> Namco2x:
    monkeypatch.setattr(namco2x_module, 'SAVES', tmp_path / 'saves')
    monkeypatch.setattr(namco2x_module, 'BIOS', tmp_path / 'bios')

    rom_path = tmp_path / 'roms' / 'namco22' / rom_name
    rom_path.parent.mkdir(parents=True, exist_ok=True)
    rom_path.write_bytes(b'')

    config = MagicMock()
    config.system = 'namco22'
    config.emulator = 'namco2x'
    config.rom = rom_path
    config.use_guns = use_guns
    config.get_str.side_effect = lambda key, default=None: options.get(key, default)
    config.get.side_effect = lambda key, default=None: (global_options or {}).get(key, default)

    emulator = Namco2x(config, MagicMock())
    emulator.rom = Rom(rom_path, None)
    emulator.guns = guns or []
    return emulator


def _cfg(tmp_path: Path) -> dict[str, str]:
    text = (tmp_path / 'saves' / 'namco2x' / 'timecris' / 'tc_controls.cfg').read_text()
    return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)


def test_namco2x_entry_point_resolves() -> None:
    assert Emulator._load_class('namco2x') is Namco2x  # pyright: ignore[reportPrivateUsage]


def test_namco2x_configure_without_guns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(tmp_path, monkeypatch, 'timecris.zip', {'namco2x_widescreen': '1'})

    game_dir = tmp_path / 'saves' / 'namco2x' / 'timecris'
    assert emulator.execution_path == game_dir
    assert game_dir.is_dir()

    command = asyncio.run(emulator.configure())

    assert command.args == [Path('/usr/lib/namco2x/tc'), '--fullscreen', 'extracted']
    assert command.env == {}
    assert (game_dir / 'roms' / 'timecris.zip').readlink() == Path(emulator.rom)
    assert _cfg(tmp_path) == {
        'window_mode': '1',
        'fullscreen': '1',
        'widescreen': '1',
        'resolution': '640x480',
        'gun_flash': '1',
        'gun_border': '0',
        'crosshair': '1',
    }


def test_namco2x_sinden_uses_batocera_border_and_no_crosshair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(
        tmp_path,
        monkeypatch,
        'timecris.zip',
        {},
        use_guns=True,
        guns=[_gun(needs_borders=True, needs_cross=False)],
        global_options={'controllers.guns.borderssize': 'big'},
    )

    asyncio.run(emulator.configure())

    cfg = _cfg(tmp_path)
    assert cfg['gun_border'] == '0'  # batocera's bezel overlay draws the border
    assert not emulator.handles_bezels
    assert cfg['crosshair'] == '0'


def test_namco2x_keeps_player_settings_and_honours_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(
        tmp_path,
        monkeypatch,
        'timecris.zip',
        {'namco2x_gun_border': '5', 'namco2x_crosshair': '1'},
        use_guns=True,
        guns=[_gun(needs_borders=True, needs_cross=False)],
    )
    cfg_path = tmp_path / 'saves' / 'namco2x' / 'timecris' / 'tc_controls.cfg'
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text('volume=40\ngun_border=1\nkey_coin=34\n')

    asyncio.run(emulator.configure())

    cfg = _cfg(tmp_path)
    assert cfg['volume'] == '40'
    assert cfg['key_coin'] == '34'
    assert cfg['gun_border'] == '5'
    assert cfg['crosshair'] == '1'


def test_namco2x_replaces_stale_rom_link(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(tmp_path, monkeypatch, 'timecris.zip', {})
    link = tmp_path / 'saves' / 'namco2x' / 'timecris' / 'roms' / 'timecris.zip'
    link.parent.mkdir(parents=True)
    link.symlink_to(tmp_path / 'elsewhere.zip')

    asyncio.run(emulator.configure())

    assert link.readlink() == Path(emulator.rom)


def test_namco2x_rejects_unsupported_game(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(tmp_path, monkeypatch, 'propcycl.zip', {})

    with pytest.raises(BatoceraException, match="unsupported game 'propcycl'"):
        asyncio.run(emulator.configure())


def test_namco2x_rave_racer_links_bios_and_has_no_gun_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(tmp_path, monkeypatch, 'raverace.zip', {}, use_guns=True)
    bios = tmp_path / 'bios' / 'namcoc74.zip'
    bios.parent.mkdir(parents=True)
    bios.write_bytes(b'')

    command = asyncio.run(emulator.configure())

    game_dir = tmp_path / 'saves' / 'namco2x' / 'raverace'
    assert command.args == [Path('/usr/lib/namco2x/rr'), '--fullscreen', 'extracted']
    assert (game_dir / 'roms' / 'namcoc74.zip').readlink() == bios
    assert (game_dir / 'rr_controls.cfg').read_text() == (
        'window_mode=1\nfullscreen=1\nwidescreen=0\nresolution=640x480\n'
    )


def test_namco2x_ace_driver_needs_namcoc74(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(tmp_path, monkeypatch, 'acedrive.zip', {})

    with pytest.raises(BatoceraException, match=r'namcoc74\.zip is missing'):
        asyncio.run(emulator.configure())


def test_namco2x_ace_driver_finds_namcoc74_beside_rom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(tmp_path, monkeypatch, 'acedrive.zip', {})
    beside = tmp_path / 'roms' / 'namco22' / 'namcoc74.zip'
    beside.write_bytes(b'')

    command = asyncio.run(emulator.configure())

    assert command.args[0] == Path('/usr/lib/namco2x/ad')
    assert (tmp_path / 'saves' / 'namco2x' / 'acedrive' / 'roms' / 'namcoc74.zip').readlink() == beside


def test_namco2x_dirt_dash_clone_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(tmp_path, monkeypatch, 'dirtdasha.zip', {})

    command = asyncio.run(emulator.configure())

    game_dir = tmp_path / 'saves' / 'namco2x' / 'dirtdasha'
    assert command.args == [Path('/usr/lib/namco2x/dd'), '--fullscreen', 'extracted']
    assert (game_dir / 'roms' / 'dirtdasha.zip').readlink() == Path(emulator.rom)
    assert (game_dir / 'dd_controls.cfg').exists()


def test_namco2x_time_crisis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emulator = _make_namco2x(
        tmp_path, monkeypatch, 'timecrs2.zip', {}, use_guns=True, guns=[_gun(needs_borders=True, needs_cross=False)]
    )

    command = asyncio.run(emulator.configure())

    assert command.args == [Path('/usr/lib/namco2x/tc2'), '--window', '--fullscreen']
    text = (tmp_path / 'saves' / 'namco2x' / 'timecrs2' / 'tc2.cfg').read_text()
    assert 'gun_border=0\n' in text
    assert 'crosshair=0\n' in text
