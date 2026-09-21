from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, Self
from unittest.mock import AsyncMock, MagicMock

from batocera_launch import emulator as emulator_module

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import pytest


def _fake_manager(name: str, events: list[str]) -> Any:
    class Manager:
        async def __aenter__(self) -> Self:
            events.append(f'enter:{name}')
            return self

        async def __aexit__(self, *exc_info: object) -> None:
            events.append(f'exit:{name}')

        @contextlib.asynccontextmanager
        async def monitor_controllers(self) -> AsyncIterator[None]:
            yield

    return Manager()


def _run_emulator(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    events: list[str] = []
    command = MagicMock()
    command.run = AsyncMock(side_effect=lambda: events.append('run') or 0)

    async def group_tasks(*awaitables: Any) -> tuple[None, MagicMock]:
        for awaitable in awaitables:
            await awaitable
        return None, command

    @contextlib.asynccontextmanager
    async def bezel_overlay(*_: object) -> AsyncIterator[None]:
        yield

    monkeypatch.setenv('SDL_RENDER_VSYNC', '1')  # Emulator.run() sets it; restored on teardown
    monkeypatch.setattr(emulator_module, 'script_caller', lambda *_, **__: _fake_manager('script_caller', events))
    monkeypatch.setattr(emulator_module, 'EvmapyManager', lambda *_, **__: _fake_manager('evmapy', events))
    monkeypatch.setattr(emulator_module, 'HotkeygenManager', lambda *_, **__: _fake_manager('hotkeygen', events))
    monkeypatch.setattr(emulator_module, 'group_tasks', group_tasks)
    monkeypatch.setattr(emulator_module, 'bezel_overlay', bezel_overlay)

    emulator = MagicMock()
    emulator.config.get_bool.return_value = '1'
    emulator.needs_sdl_controller_db = False
    emulator.needs_sdl_game_controller_config = False
    emulator.config.use_guns = False
    emulator.configure_windows = AsyncMock()
    emulator.configure = AsyncMock(return_value=command)
    emulator.prepare_bezel = AsyncMock(return_value=None)
    emulator.prepare_hud = AsyncMock()
    emulator.before_run = AsyncMock()

    assert asyncio.run(emulator_module.Emulator.run(emulator)) == 0
    return events


def test_evmapy_is_stopped_before_hotkeygen_leaves_the_game_context(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stopping evmapy releases the buttons it still holds (KEY_EXIT when hotkey+start is held past the game's
    # exit). That release must reach hotkeygen while it is still in the game's context, otherwise the keys the
    # press sent (Alt+F4) are never released and a compositor that binds Alt+F4 keeps closing every new window.
    events = _run_emulator(monkeypatch)

    assert events.index('run') > events.index('enter:evmapy') > events.index('enter:hotkeygen')
    assert events.index('exit:evmapy') < events.index('exit:hotkeygen') < events.index('exit:script_caller')
    assert events.index('exit:evmapy') > events.index('run')
