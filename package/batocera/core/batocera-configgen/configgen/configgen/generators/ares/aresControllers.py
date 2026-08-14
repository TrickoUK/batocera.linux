from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ...controller import Controller, Controllers
    from ...input import Input

# ares' desktop-ui has one generic "Virtual Gamepad" input device per player
# slot (VirtualPad1..VirtualPad5, see desktop-ui/input/input.hpp). Every
# emulated console's own controller (N64 Gamepad, Super Famicom pad, ...)
# inherits its bindings from whichever VirtualPad slot is plugged into that
# port unless it has been given its own direct binding - so binding just
# these 5 generic slots is enough to make every core playable, without
# needing each core's own native button names.
#
# The exact settings.bml key for each VirtualPad button is derived from its
# in-UI display name (desktop-ui/input/input.cpp, VirtualPad::VirtualPad())
# via the same "replace(' ', '.').replace('(', '.').replace(')', '')"
# transform ares itself applies when serializing (desktop-ui/settings/settings.cpp).
_VPAD_KEYS: Mapping[str, str] = {
    'up': 'Pad.Up',
    'down': 'Pad.Down',
    'left': 'Pad.Left',
    'right': 'Pad.Right',
    'select': 'Select',
    'start': 'Start',
    # ES's abstract a/b/x/y are SNES-style positions (a=East, b=South,
    # x=North, y=West - see GuiInputConfig.cpp's GUI_INPUT_CONFIG_LIST),
    # not literal ares/Xbox-style node names, so this is a swap, not an
    # identity mapping.
    'a': 'B..East',
    'b': 'A..South',
    'x': 'Y..North',
    'y': 'X..West',
    'pageup': 'L-Bumper',
    'pagedown': 'R-Bumper',
    'l2': 'L-Trigger',
    'r2': 'R-Trigger',
    'l3': 'L-Stick..Click',
    'r3': 'R-Stick..Click',
}

# HID::Joypad::GroupID (nall/nall/hid.hpp): Axis=0, Hat=1, Trigger=2, Button=3.
# ares' SDL joypad driver (ruby/input/joypad/sdl.cpp) never populates the
# Trigger group - triggers show up as regular axes, same as SDL reports them.
_GROUP_AXIS = 0
_GROUP_HAT = 1
_GROUP_BUTTON = 3

# Standard SDL hat bitmask values (SDL_HAT_UP/RIGHT/DOWN/LEFT) - this is
# what batocera records as an Input's `.value` for a 'hat'-type input.
_SDL_HAT_UP = 1
_SDL_HAT_RIGHT = 2
_SDL_HAT_DOWN = 4
_SDL_HAT_LEFT = 8


def _binding(prefix: str, input: Input, /, *, qualifier: str | None = None) -> str | None:
    if input.type == 'button':
        return f'{prefix}/{_GROUP_BUTTON}/{input.id}'

    if input.type == 'axis':
        # Any non-Button groupID binding is silently dead without a Hi/Lo
        # qualifier - InputDigital::value()/InputAnalog::value()
        # (desktop-ui/input/input.cpp) only produce a nonzero output for
        # Qualifier::Hi (raw value > 0) or Qualifier::Lo (raw value < 0),
        # never for Qualifier::None. For a single-direction input (a
        # trigger, or a d-pad direction some controllers report as an
        # axis rather than a hat/button) the caller doesn't know or need
        # to pick a side - the sign EmulationStation recorded when this
        # input was paired already tells us which half means "active".
        # (The two-directions-sharing-one-axis case - an analog stick's
        # up/down or left/right - passes an explicit qualifier instead,
        # see generate_virtualpad_bindings() below.)
        if qualifier is None:
            qualifier = 'Hi' if int(input.value) > 0 else 'Lo'
        return f'{prefix}/{_GROUP_AXIS}/{input.id}/{qualifier}'

    if input.type == 'hat':
        # Each physical hat is split by ares into two synthetic HID inputs:
        # 2*n (horizontal) and 2*n+1 (vertical), each ranging -32767..+32767
        # (ruby/input/joypad/sdl.cpp) - LEFT/UP are the negative (Lo) half,
        # RIGHT/DOWN the positive (Hi) half. This is ares' own fixed
        # convention, not dependent on anything EmulationStation recorded,
        # so the SDL hat bitmask batocera stores as the input's `.value`
        # maps directly, with no per-controller polarity to account for.
        hat = int(input.id)
        value = int(input.value)
        if value == _SDL_HAT_LEFT:
            return f'{prefix}/{_GROUP_HAT}/{hat * 2}/Lo'
        if value == _SDL_HAT_RIGHT:
            return f'{prefix}/{_GROUP_HAT}/{hat * 2}/Hi'
        if value == _SDL_HAT_UP:
            return f'{prefix}/{_GROUP_HAT}/{hat * 2 + 1}/Lo'
        if value == _SDL_HAT_DOWN:
            return f'{prefix}/{_GROUP_HAT}/{hat * 2 + 1}/Hi'
        return None

    return None


def generate_virtualpad_bindings(controller: Controller, prefix: str) -> dict[str, str]:
    """Returns {ares settings.bml key (under VirtualPadN/): assignment string}.

    `prefix` is ares' "<GUID>/<slot>" device identifier for this controller.
    """
    bindings: dict[str, str] = {}

    def add(vpad_key: str, binding: str | None, /) -> None:
        # ares stores up to 3 alternate physical bindings per input
        # (BindingLimit, desktop-ui/input/input.hpp) as a ";"-joined
        # settings.bml value - appending rather than overwriting lets two
        # different physical inputs (e.g. the real d-pad and the stick
        # read digitally) both drive the same VirtualPad key.
        if binding is None:
            return
        bindings[vpad_key] = f'{bindings[vpad_key]};{binding}' if vpad_key in bindings else binding

    for name, vpad_key in _VPAD_KEYS.items():
        if (input := controller.inputs.get(name)) is not None:
            add(vpad_key, _binding(prefix, input))

    # The two analog sticks are recorded by EmulationStation as a single
    # "up" and a single "left" axis each (down/right are the same physical
    # axis, opposite direction) - split each into ares' two independent
    # InputAnalog entries (L-Up/L-Down, L-Left/L-Right) using the Hi/Lo
    # qualifiers. `input.value`'s sign is the raw axis reading recorded
    # when the "up"/"left" direction was paired, i.e. it tells us which
    # qualifier (Hi = positive raw value, Lo = negative) that direction
    # actually is - so e.g. if pushing up reads positive, Up gets Hi and
    # Down gets Lo; if it reads negative, that's swapped.
    #
    # The primary stick is *also* bound a second way, read as a digital
    # threshold (InputDigital supports an axis+qualifier binding directly,
    # same as InputAnalog does), as an alternate source for the D-Pad
    # (Pad.Up/Down/Left/Right) - so a player can use either the physical
    # d-pad or the stick interchangeably per game, same as "left stick
    # also acts as d-pad" support elsewhere. This also gives SNES - no
    # analog stick on real hardware, so nothing downstream ever reads
    # L-Up/L-Down there - a way to use the stick at all. The second stick
    # has no equivalent second D-Pad to alternate-bind, so it's skipped
    # there (`dpad_this`/`dpad_other` are `None`).
    for base_name, stick, this_way, other_way, dpad_this, dpad_other in (
        ('joystick1up', 'L', 'Up', 'Down', 'Pad.Up', 'Pad.Down'),
        ('joystick1left', 'L', 'Left', 'Right', 'Pad.Left', 'Pad.Right'),
        ('joystick2up', 'R', 'Up', 'Down', None, None),
        ('joystick2left', 'R', 'Left', 'Right', None, None),
    ):
        input = controller.inputs.get(base_name)
        if input is None or input.type != 'axis':
            continue
        this_is_hi = int(input.value) > 0
        hi_binding = _binding(prefix, input, qualifier='Hi')
        lo_binding = _binding(prefix, input, qualifier='Lo')
        add(f'{stick}-{this_way}', hi_binding if this_is_hi else lo_binding)
        add(f'{stick}-{other_way}', lo_binding if this_is_hi else hi_binding)
        if dpad_this is not None:
            add(dpad_this, hi_binding if this_is_hi else lo_binding)
            add(dpad_other, lo_binding if this_is_hi else hi_binding)

    return bindings


def generate_all_virtualpad_bindings(controllers: Controllers) -> dict[int, dict[str, str]]:
    """Returns {player_number (1-based): {ares key: assignment string}}."""
    # ares identifies a joypad as "<GUID>/<slot>", where <slot> counts prior
    # same-GUID devices in SDL enumeration order (ruby/input/joypad/sdl.cpp).
    # We approximate that order with the order controllers of the same GUID
    # appear here, which is generally - but not guaranteed to be - the same
    # physical enumeration order ares itself will see.
    slots_seen: dict[str, int] = {}
    result: dict[int, dict[str, str]] = {}

    for controller in controllers[:5]:
        slot = slots_seen.get(controller.guid, 0)
        slots_seen[controller.guid] = slot + 1
        prefix = f'{controller.guid}/{slot}'
        result[controller.player_number] = generate_virtualpad_bindings(controller, prefix)

    return result
