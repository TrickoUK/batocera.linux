from __future__ import annotations

from typing import TYPE_CHECKING

from ... import Command
from ...batoceraPaths import BATOCERA_SHADERS, USER_SHADERS, ensure_parents_and_open, mkdir_if_not_exists
from ...exceptions import BatoceraException
from ..Generator import Generator
from .aresControllers import generate_all_virtualpad_bindings
from .aresPaths import (
    ARES_ACTIVE_SHADER,
    ARES_CONFIG_DIR,
    ARES_DATA_HOME,
    ARES_SAVES_DIR,
    ARES_SETTINGS_FILE,
    ARES_SHADERS_DIR,
)

if TYPE_CHECKING:
    from ...Emulator import Emulator

    from ...types import HotkeysContext

# The name each entry needs is desktop-ui's own top-level Emulator::name
# (desktop-ui/emulator/*.cpp - what --system actually matches against),
# which is a different, more granular layer than the underlying core's
# own information.name (ares/*/system/system.cpp) that several of these
# share. "Mega Drive"/"Mega 32X"/"Mega CD" are three separate desktop-ui
# entries, all backed by the exact same "md" ares core and all reporting
# information.name = "Mega Drive" internally - which mode a ROM boots
# into depends entirely on *which desktop-ui entry launched it*, not
# anything in the ROM itself. Similarly there's no separate "NES"
# desktop-ui entry (ares/fc's "Famicom" covers NTSC-U/NES too) or
# "TurboGrafx-16" one (ares/pce's own load() explicitly maps *both* "PC
# Engine" and "TurboGrafx 16" configuration strings to the same "PC
# Engine" desktop-ui entry). "sfc"/"famicom"/"tg16" are hand-authored
# custom ES systems some users add alongside "snes"/"nes"/"pcengine" for
# the region-variant name/ROM-set split - each maps to the exact same
# ares system underneath, just a different batocera system id, so they
# need their own entries here even though they're not part of
# ares.emulator.yml's `systems:` list (that list only registers the
# emulator against systems the normal build-time es_systems.yml/registry
# pipeline knows about - a custom runtime system doesn't go through it at
# all, and hand-writes its own <emulator> entry in EmulationStation's XML
# instead).
_ARES_SYSTEM_NAME = {
    'n64': 'Nintendo 64',
    'snes': 'Super Famicom',
    'sfc': 'Super Famicom',
    'nes': 'Famicom',
    'famicom': 'Famicom',
    'megadrive': 'Mega Drive',
    'sega32x': 'Mega 32X',
    'megacd': 'Mega CD',
    'mastersystem': 'Master System',
    'pcengine': 'PC Engine',
    'tg16': 'PC Engine',
}

# ares' keyboard-binding assignment string is "<deviceID>/<groupID>/<inputID>"
# (desktop-ui/input/input.cpp's inputAssignment()/InputMapping::bind()). The
# keyboard HID device never gets a text identifier() (nothing calls
# setIdentifier() for it), so it resolves via the numeric "0x<id>" branch -
# but its id() is NOT the zero default: InputKeyboardXlib::initialize()
# (ruby/input/keyboard/xlib.cpp) explicitly calls
# hid->setVendorID(HID::Keyboard::GenericVendorID)  // 0x0000
# hid->setProductID(HID::Keyboard::GenericProductID) // 0x0001
# hid->setPathID(0)
# and Device::id() packs those as (pathID<<32)|(vendorID<<16)|productID,
# giving a fixed id of 0x0001 - so the deviceID token is "0x1", not "0x0".
# groupID 0 is HID::Keyboard::GroupID::Button (its only group). inputID is
# the key's fixed position in the `keys.push_back(...)` list built by that
# same initialize() - Escape=0, F1=1, F2=2, F3=3, F4=4, ... - scraped from
# that exact list at the ARES_VERSION pinned in ares.mk; if that version is
# ever bumped, re-diff xlib.cpp's key ordering (and these setVendorID/
# setProductID/setPathID calls) before trusting these numbers again.
_ARES_KEYBOARD_INPUT_ID = {
    'F1': 1,
    'F2': 2,
    'F3': 3,
    'F4': 4,
}


def _keyboard_binding(key: str, /) -> str:
    return f'0x1/0/{_ARES_KEYBOARD_INPUT_ID[key]}'


def _write_bml_section(lines: list[str], name: str, values: dict[str, str], /) -> None:
    if not values:
        return
    lines.append(name)
    for key, value in values.items():
        lines.append(f'  {key}: {value}')


def _resolve_shader(system: Emulator, /) -> str:
    """Returns the value for ares' Video/Shader BML key.

    The "shaderset" custom control (shared_features - populated the same
    way for every emulator that lists it, resolved by Emulator.py against
    the user's own /userdata/shaders/ sets first, falling back to the
    built-in /usr/share/batocera/shaders/ ones) already resolves down to a
    single relative shader path (no extension) for the current system, via
    system.renderconfig. Stage whichever real file that points to (checking
    the same two roots, in the same order, since renderconfig doesn't say
    which one the actual .slangp lives under) as a symlink at a fixed name
    under ARES_SHADERS_DIR, and point ares at that - see aresPaths.py for
    why a fixed, writable location is needed (ares only ever looks in a
    handful of fixed candidate directories, none of which are userdata).
    """
    shader_path = system.renderconfig.get('shader')
    if not shader_path:
        return 'None'

    for root in (USER_SHADERS, BATOCERA_SHADERS):
        candidate = root / f'{shader_path}.slangp'
        if candidate.exists():
            mkdir_if_not_exists(ARES_SHADERS_DIR)
            if ARES_ACTIVE_SHADER.is_symlink() or ARES_ACTIVE_SHADER.exists():
                ARES_ACTIVE_SHADER.unlink()
            ARES_ACTIVE_SHADER.symlink_to(candidate)
            return ARES_ACTIVE_SHADER.name

    return 'None'


class AresGenerator(Generator):

    def getHotkeysContext(self) -> HotkeysContext:
        return {
            "name": "ares",
            "keys": {
                "exit": ["KEY_LEFTALT", "KEY_F4"],
                "save_state": "KEY_F2",
                "restore_state": "KEY_F1",
                "previous_slot": "KEY_F3",
                "next_slot": "KEY_F4",
                "menu": "KEY_F7",
            }
        }

    def generate(self, system, rom, playersControllers, metadata, guns, wheels, gameResolution):
        ares_system = _ARES_SYSTEM_NAME.get(system.name)
        if ares_system is None:
            raise BatoceraException(f"ares: unsupported system '{system.name}'")

        mkdir_if_not_exists(ARES_CONFIG_DIR)
        mkdir_if_not_exists(ARES_SAVES_DIR)

        lines: list[str] = []

        _write_bml_section(lines, 'Video', {
            'Driver': 'OpenGL 3.2',
            'Shader': _resolve_shader(system),
            # "Scale" = aspect-correct best-fit (desktop-ui/program/platform.cpp's
            # Program::video()) - fills as much of the screen as the game's own
            # aspect ratio allows, only ever bordering a single axis; "Integer"
            # only scales by whole numbers, leaving slack on both axes; "Stretch"
            # ignores aspect entirely.
            'Output': system.config.get('ares_output', 'Scale'),
            'AspectCorrection': system.config.get('ares_aspect_correction', 'Standard'),
            # "Displays the full frame without cropping 'undesirable' borders"
            # (ares' own tooltip) - many games leave that border blank, which
            # reads as an inconsistent, game-dependent black border around an
            # otherwise correctly-scaled image. Default to cropped.
            'Overscan': system.config.get('ares_overscan', 'false'),
        })

        _write_bml_section(lines, 'General', {
            'NoFilePrompt': 'true',
            # ares' own overlay (game name / fps, at the bottom of the
            # window) isn't wanted for a frontend-launched game and reserves
            # vertical space that would otherwise go to the video output.
            'ShowStatusBar': 'false',
        })

        _write_bml_section(lines, 'Paths', {
            'Saves': str(ARES_SAVES_DIR) + '/',
        })

        # ares ships with no default hotkeys at all (every Hotkey/* key is
        # empty until assigned via its own in-window Settings > Hotkeys
        # panel) - without writing these, the F1/F2/F3/F4 keys hotkeygen
        # synthesizes for save_state/restore_state/previous_slot/next_slot
        # (getHotkeysContext() above) reach ares' window but have nothing
        # bound to react to them.
        _write_bml_section(lines, 'Hotkey', {
            'SaveState': _keyboard_binding('F2'),
            'LoadState': _keyboard_binding('F1'),
            'DecrementStateSlot': _keyboard_binding('F3'),
            'IncrementStateSlot': _keyboard_binding('F4'),
        })

        if system.name == 'n64':
            _write_bml_section(lines, 'Nintendo64', {
                'Quality': system.config.get('ares_n64_quality', 'SD'),
                'Supersampling': system.config.get('ares_n64_supersampling', 'false'),
                'WeaveDeinterlacing': system.config.get('ares_n64_weave_deinterlacing', 'false'),
                'DisableVideoInterfaceProcessing': system.config.get('ares_n64_disable_vi_processing', 'false'),
            })

        for player_number, bindings in generate_all_virtualpad_bindings(playersControllers).items():
            _write_bml_section(lines, f'VirtualPad{player_number}', bindings)

        with ensure_parents_and_open(ARES_SETTINGS_FILE, 'w') as settingsFile:
            settingsFile.write('\n'.join(lines) + '\n')

        commandArray = [
            '/usr/bin/ares',
            '--fullscreen',
            '--no-file-prompt',
            '--system', ares_system,
            '--settings-file', ARES_SETTINGS_FILE,
        ]

        # Launching a specific slot from EmulationStation's save-state panel
        # (GuiSaveState) passes "-state_slot <N>" (and "-state_file <path>",
        # unused here - ares' own --save-state flag only takes a slot digit,
        # deriving the actual path itself via Emulator::locate() the same
        # way stateSave/stateLoad do). Without this, ES's panel entry just
        # boots the ROM fresh - it never actually requests a load. ares only
        # accepts a single digit 1-9 (desktop-ui.cpp's --save-state parsing)
        # and silently ignores anything else, which conveniently also covers
        # ES's slot -1 ("run current autosave") and -2 ("new game, no
        # autosave") sentinel values - neither applies since this emulator
        # entry has autosave="false" in es_savestates.cfg.
        if state_slot := system.config.get('state_slot'):
            commandArray += ['--save-state', str(state_slot)]

        commandArray.append(rom)

        return Command.Command(
            array=commandArray,
            env={
                # ares has no CLI override for its shader search directory -
                # only for settings.bml itself (--settings-file, used above).
                # XDG_DATA_HOME redirects locate("Shaders/")'s user-data
                # candidate (desktop-ui/program/drivers.cpp) to
                # ARES_SHADERS_DIR; see aresPaths.py for the full chain.
                'XDG_DATA_HOME': ARES_DATA_HOME,
                # Read by this fork's 001-batocera-savestate-system-scoped-
                # folders.patch (desktop-ui/emulator/emulator.cpp's
                # Emulator::locate()) so save states/undo states/screenshots
                # land under a batocera-system-scoped folder instead of
                # ares' own coarser core name - without this, megadrive/
                # sega32x/megacd (all the same "md" core, all reporting
                # root->name() == "Mega Drive") would share one save folder.
                'ARES_BATOCERA_SYSTEM_ID': system.name,
            },
        )
