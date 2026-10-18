from __future__ import annotations

import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from .gun import Guns

_logger = logging.getLogger(__name__)

_SINDEN_NAME: Final = 'Sinden lightgun'

# created by virtual-sindenlightgun-add (evsieve --control-fifo), one per gun
_FIFO_DIR: Final = Path('/var/run')
_FIFO_GLOB: Final = 'virtual-sindenlightgun-devices.*.fifo'

# evsieve toggle "frontleft": 1 = front left sends the pump's BTN_RIGHT, 2 = BTN_3
_MERGED: Final = 1
_SPLIT: Final = 2


def _set_front_left(state: int, /) -> None:
    for fifo in _FIFO_DIR.glob(_FIFO_GLOB):
        try:
            # non-blocking so a fifo without a reader (evsieve gone) can't hang the launch
            fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            _logger.warning('cannot open sinden control fifo %s', fifo)
            continue

        with contextlib.closing(os.fdopen(fd, 'w')) as file:
            file.write(f'toggle frontleft:{state}\n')

        _logger.info('sinden front left button %s on %s', 'split from the pump' if state == _SPLIT else 'merged', fifo)


@asynccontextmanager
async def split_sinden_pump(guns: Guns, enabled: bool, /) -> AsyncGenerator[None]:
    """While active, the front left button of Sinden guns is BTN_3 instead of sharing BTN_RIGHT with the pump."""
    if not enabled or not any(gun.name == _SINDEN_NAME for gun in guns):
        yield
        return

    _set_front_left(_SPLIT)
    try:
        yield
    finally:
        _set_front_left(_MERGED)
