from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_common.paths import BIOS, SAVES
from batocera_launch import BatoceraException, Command, Emulator, HotkeysContext, guns_need_crosses

_BIN_DIR: Final = Path('/usr/lib/namco2x')

_PLAY_ARGS: Final = ('--fullscreen', 'extracted')


@dataclass(frozen=True, slots=True)
class _Game:
    binary: str  # in the namco-2x-systems release (package namco2x, NAMCO2X_BINARIES)
    cfg_file: str  # the engine's settings file, in the working directory
    args: tuple[str, ...] = _PLAY_ARGS
    light_gun: bool = False
    bios_zips: tuple[str, ...] = ()  # other MAME zips the game unpacks beside its own


# MAME set name -> game. Each binary unzips its sets from roms/ on first run.
_GAMES: Final = {
    'timecris': _Game('tc', 'tc_controls.cfg', light_gun=True),
    'raverace': _Game('rr', 'rr_controls.cfg', bios_zips=('namcoc74.zip',)),
    'acedrive': _Game('ad', 'ad_controls.cfg', bios_zips=('namcoc74.zip',)),
    # the World DT2 Ver.A program is MAME's dirtdasha; the engine also takes
    # any dirtdash*.zip, so a clone-only (non-merged) set works on its own
    'dirtdash': _Game('dd', 'dd_controls.cfg'),
    'dirtdasha': _Game('dd', 'dd_controls.cfg'),
    # System 23, on its own host: '--window' selects play mode
    'timecrs2': _Game('tc2', 'tc2.cfg', ('--window', '--fullscreen'), light_gun=True),
}


def _merge_cfg(existing_text: str, managed: dict[str, str], /) -> str:
    # the engine's settings file is plain key=value; keep every key the player
    # set from the in-game menu (rebinds, volume, ...) and only replace ours
    remaining = dict(managed)
    lines: list[str] = []

    for line in existing_text.splitlines():
        stripped = line.strip()
        key = stripped.split('=', 1)[0].strip() if not stripped.startswith('#') and '=' in stripped else None
        if key in remaining:
            lines.append(f'{key}={remaining.pop(key)}')
        else:
            lines.append(line)

    lines.extend(f'{key}={value}' for key, value in remaining.items())
    return '\n'.join((*lines, ''))


@cached_dataclass
class Namco2x(Emulator):
    needs_sdl_game_controller_config = True
    cpu_cluster = 'fast'

    @cached_property
    def hotkeygen_context(self) -> HotkeysContext:
        return {
            'name': 'namco2x',
            # Alt+F4 -> labwc closes the window -> SDL_QUIT, a clean exit (the
            # EEPROM is also written every 120 frames, so a kill loses nothing)
            'keys': {'exit': ['KEY_LEFTALT', 'KEY_F4'], 'menu': 'KEY_ESC'},
        }

    @cached_property
    def saves_dir(self) -> Path:
        return SAVES / 'namco2x'

    @cached_property
    def game_dir(self) -> Path:
        # NOTE: self.rom is not set yet when execution_path is first used
        return self.saves_dir / self.config.rom.stem

    @property
    def execution_path(self) -> Path | None:
        # everything the engine reads and writes is relative to its working
        # directory: roms/, extracted/ (the ROM unpacked on first run), the
        # settings and the EEPROM
        self.game_dir.mkdir(parents=True, exist_ok=True)
        return self.game_dir

    @property
    def handles_bezels(self) -> bool:
        # the engine draws its own gun border around the picture; batocera's
        # border overlay is X11-only and would not show over this window
        return True

    def _gun_border(self) -> str:
        if (value := self.config.get_str('namco2x_gun_border', 'auto')) != 'auto':
            return value
        if self.config.use_guns and self.guns and (dimensions := self.gun_border_dimensions) is not None:
            return str(min(6, sum(dimensions)))
        return '0'

    def _crosshair(self) -> str:
        if (value := self.config.get_str('namco2x_crosshair', 'auto')) != 'auto':
            return value
        if self.config.use_guns and self.guns:
            return '1' if guns_need_crosses(self.guns) else '0'
        return '1'  # mouse or pad: the crosshair is the only cursor

    @staticmethod
    def _link(link: Path, target: Path, /) -> None:
        if link.is_symlink() and link.readlink() == target:
            return
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)

    def _link_roms(self, game: _Game, /) -> None:
        roms_dir = self.game_dir / 'roms'
        roms_dir.mkdir(parents=True, exist_ok=True)
        self._link(roms_dir / f'{self.rom.stem}.zip', Path(self.rom))
        for name in game.bios_zips:
            for source in (BIOS / name, Path(self.rom).parent / name):
                if source.exists():
                    self._link(roms_dir / name, source)
                    break
            else:
                raise BatoceraException(f'namco2x: {name} is missing (put it in {BIOS})')

    async def configure(self) -> Command:
        if (game := _GAMES.get(self.rom.stem)) is None:
            raise BatoceraException(
                f"namco2x: unsupported game '{self.rom.stem}' (supported: {', '.join(sorted(_GAMES))})"
            )
        self._link_roms(game)

        managed = {
            'window_mode': '1',
            'fullscreen': '1',
            'widescreen': self.config.get_str('namco2x_widescreen', '0'),
            'resolution': self.config.get_str('namco2x_resolution', '640x480'),
        }
        if game.light_gun:
            managed |= {
                'gun_flash': self.config.get_str('namco2x_gun_flash', '1'),
                'gun_border': self._gun_border(),
                'crosshair': self._crosshair(),
            }
        config_path = self.game_dir / game.cfg_file
        existing_text = config_path.read_text() if config_path.exists() else ''
        config_path.write_text(_merge_cfg(existing_text, managed))

        return Command([_BIN_DIR / game.binary, *game.args])
