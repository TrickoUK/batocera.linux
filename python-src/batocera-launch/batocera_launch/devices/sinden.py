from __future__ import annotations

import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Sequence

    from .gun import Guns

_logger = logging.getLogger(__name__)

_SINDEN_NAME: Final = 'Sinden lightgun'

# created by virtual-sindenlightgun-add, one per gun: the evsieve --control-fifo and a
# --output create-link symlink to the gun's event node
_RUN_DIR: Final = Path('/var/run')
_FIFO_GLOB: Final = 'virtual-sindenlightgun-devices.*.fifo'

# evsieve toggle "frontleft": 1 = front left sends the pump's BTN_RIGHT, 2 = BTN_3
_MERGED: Final = 1
_SPLIT: Final = 2

# evsieve toggles hand_fl/hand_fr/hand_rl/hand_rr: 1 = right hand, 2 = left hand (front and rear buttons mirrored)
_RIGHT_HAND: Final = 1
_LEFT_HAND: Final = 2
_HAND_TOGGLES: Final = ('hand_fl', 'hand_fr', 'hand_rl', 'hand_rr')


def _fifo_node(fifo: Path, /) -> str | None:
    try:
        return os.path.realpath(fifo.with_suffix('.event'), strict=True)
    except OSError:
        return None


def _send(fifo: Path, command: str, /) -> None:
    try:
        # non-blocking so a fifo without a reader (evsieve gone) can't hang the launch
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        _logger.warning('cannot open sinden control fifo %s', fifo)
        return

    with contextlib.closing(os.fdopen(fd, 'w')) as file:
        file.write(f'{command}\n')

    _logger.info('sinden control %s: %s', fifo, command)


def _command(front_left: int, hand: int, /) -> str:
    return ' '.join(['toggle', f'frontleft:{front_left}', *(f'{toggle}:{hand}' for toggle in _HAND_TOGGLES)])


@asynccontextmanager
async def sinden_gun_modes(guns: Guns, split_pump: bool, left_handed_players: Sequence[int], /) -> AsyncGenerator[None]:
    """While active, set the Sinden gun button modes.

    split_pump: the front left button is BTN_3 instead of sharing BTN_RIGHT with the pump.
    left_handed_players: 1-based player numbers (the order of guns given to the games) whose gun has its front and
    rear buttons mirrored for a left hand grip.
    """
    players = {gun.node: player for player, gun in enumerate(guns, start=1) if gun.name == _SINDEN_NAME}
    if not players or (not split_pump and not left_handed_players):
        yield
        return

    fifos = sorted(_RUN_DIR.glob(_FIFO_GLOB))

    for fifo in fifos:
        player = players.get(_fifo_node(fifo) or '')
        hand = _LEFT_HAND if player in left_handed_players else _RIGHT_HAND
        _send(fifo, _command(_SPLIT if split_pump else _MERGED, hand))

    try:
        yield
    finally:
        for fifo in fifos:
            _send(fifo, _command(_MERGED, _RIGHT_HAND))
