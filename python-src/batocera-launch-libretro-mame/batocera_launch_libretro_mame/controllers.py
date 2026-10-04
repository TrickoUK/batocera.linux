from __future__ import annotations

import codecs
import os
from typing import TYPE_CHECKING, Final
from xml.dom import minidom

from batocera_common.dataclasses import cached_dataclass
from batocera_launch_mame_common import (
    ControlConfig,
    get_mess_control_scheme,
    load_mame_control_mapping,
    load_mess_system_controls,
    reverse_mapping,
)

from .base import MAMEBase

if TYPE_CHECKING:
    from batocera_launch import Controller

# Define RetroPad inputs for mapping
_RETRO_PAD_MAPPINGS: Final = {
    'joystick1up': 'YAXIS_UP_SWITCH',
    'joystick1down': 'YAXIS_DOWN_SWITCH',
    'joystick1left': 'XAXIS_LEFT_SWITCH',
    'joystick1right': 'XAXIS_RIGHT_SWITCH',
    'up': 'HAT{0}UP',
    'down': 'HAT{0}DOWN',
    'left': 'HAT{0}LEFT',
    'right': 'HAT{0}RIGHT',
    'joystick2up': 'RYAXIS_NEG_SWITCH',
    'joystick2down': 'RYAXIS_POS_SWITCH',
    'joystick2left': 'RXAXIS_NEG_SWITCH',
    'joystick2right': 'RXAXIS_POS_SWITCH',
    'b': 'BUTTON1',
    'a': 'BUTTON2',
    'y': 'BUTTON3',
    'x': 'BUTTON4',
    'pageup': 'BUTTON5',
    'pagedown': 'BUTTON6',
    'l2': 'RZAXIS_POS_SWITCH',
    'r2': 'ZAXIS_POS_SWITCH',
    'l3': 'BUTTON12',
    'r3': 'BUTTON11',
    'select': 'SELECT',
    'start': 'START',
}


def _get_input_definition(
    controller: Controller,
    key: str,
    input: str,
    joycode: int,
    reversed: bool,
    altButtons: str | int,
    ignore_axis: bool = False,
) -> str:
    if input.find('BUTTON') != -1 or input.find('HAT') != -1 or input == 'START' or input == 'SELECT':
        input = input.format(joycode) if '{0}' in input else input
        return f'JOYCODE_{joycode}_{input}'

    if input.find('AXIS') != -1:
        if altButtons == 'qbert':  # Q*Bert Joystick
            if key == 'joystick1up' or key == 'up':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1up"]}_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1right"]} OR \
                    JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["up"].format(joycode)} JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["right"].format(joycode)}'
            if key == 'joystick1down' or key == 'down':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1down"]} JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1left"]} OR \
                    JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["down"].format(joycode)} JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["left"].format(joycode)}'
            if key == 'joystick1left' or key == 'left':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1left"]} JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1up"]} OR \
                    JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["left"].format(joycode)} JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["up"].format(joycode)}'
            if key == 'joystick1right' or key == 'right':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1right"]} JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["joystick1down"]} OR \
                    JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["right"].format(joycode)} JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["down"].format(joycode)}'
            return f'JOYCODE_{joycode}_{input}'

        if ignore_axis:
            if key == 'joystick1up' or key == 'up':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["up"].format(joycode)}'
            if key == 'joystick1down' or key == 'down':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["down"].format(joycode)}'
            if key == 'joystick1left' or key == 'left':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["left"].format(joycode)}'
            if key == 'joystick1right' or key == 'right':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["right"].format(joycode)}'
        else:
            if key == 'joystick1up' or key == 'up':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["up"].format(joycode)}'
            if key == 'joystick1down' or key == 'down':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["down"].format(joycode)}'
            if key == 'joystick1left' or key == 'left':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["left"].format(joycode)}'
            if key == 'joystick1right' or key == 'right':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["right"].format(joycode)}'
            if key == 'joystick2up':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["x"]}'
            if key == 'joystick2down':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["b"]}'
            if key == 'joystick2left':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["y"]}'
            if key == 'joystick2right':
                return f'JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS[key]} OR JOYCODE_{joycode}_{_RETRO_PAD_MAPPINGS["a"]}'

            return f'JOYCODE_{joycode}_{input}'
    return 'unknown'


def _generate_port_element(
    controller: Controller,
    config: ControlConfig,
    nplayer: int,
    mapping: str,
    key: str,
    input: str,
    reversed: bool,
    altButtons: str,
) -> None:
    # Generic input
    config.add_sequence_port(
        f'P{nplayer}_{mapping}',
        sequence=_get_input_definition(controller, key, input, controller.index + 1, reversed, altButtons),
    )


def _generate_special_port_element(
    controller: Controller,
    config: ControlConfig,
    tag: str,
    nplayer: int,
    mapping: str,
    key: str,
    input: str,
    reversed: bool = False,
    mask: int | None = None,
    default: int | None = None,
) -> None:
    # Special button input (ie mouse button to gamepad)
    sequence = _get_input_definition(controller, key, input, controller.index + 1, reversed, 0)
    if mapping == f'COIN{nplayer}' and nplayer == 1:
        sequence = sequence + f' OR KEYCODE_{nplayer}_F{nplayer + 11}'  # f12 for player 1

    config.add_sequence_port(
        mapping,
        sequence=sequence,
        tag=tag,
        mask='' if mask is None else str(mask),
        defvalue='' if default is None else str(default),
    )


def _generate_combo_port_element(
    controller: Controller,
    config: ControlConfig,
    tag: str,
    mapping: str,
    kbkey: str,
    key: str,
    input: str,
    reversed: bool = False,
    mask: int | None = None,
    default: int | None = None,
):
    # Maps a keycode + button - for important keyboard keys when available
    config.add_sequence_port(
        mapping,
        sequence=f'KEYCODE_{kbkey} OR {
            _get_input_definition(controller, key, input, controller.index + 1, reversed, 0)
        }',
        tag=tag,
        mask='' if mask is None else str(mask),
        defvalue='' if default is None else str(default),
    )


def _generate_analog_port_element(
    controller: Controller,
    config: ControlConfig,
    tag: str,
    nplayer: int,
    mapping: str,
    inckey: str,
    deckey: str,
    mappedinput: str,
    mappedinput2: str,
    reversed: bool,
    mask: int,
    default: int,
    delta: int,
    axis: str = '',
):
    # Mapping analog to digital (mouse, etc)
    config.add_sequence_port(
        mapping,
        tag=tag,
        mask=str(mask),
        defvalue=str(default),
        key_delta=str(delta),
        sequences=[
            (
                'increment',
                _get_input_definition(controller, inckey, mappedinput, controller.index + 1, reversed, 0, True),
            ),
            (
                'decrement',
                _get_input_definition(controller, deckey, mappedinput2, controller.index + 1, reversed, 0, True),
            ),
            ('standard', 'NONE' if not axis else f'JOYCODE_{controller.index + 1}_{axis}'),
        ],
    )


@cached_dataclass
class MAMEControllers(MAMEBase):
    def write_controllers_config(self) -> None:
        # config file
        default_control_config = ControlConfig(self.cfg_path / 'default.cfg')

        # Don't overwrite if using custom configs
        overwrite_mame = not (default_control_config.exists() and self.config.get_bool('customcfg'))

        # Get controller scheme
        alt_buttons = self.mame_control_scheme

        # Load standard controls
        mappings = load_mame_control_mapping(alt_buttons)

        use_controls = get_mess_control_scheme(self.mess_model, self.control_type)
        mess_controls = load_mess_system_controls(self.mess_model, use_controls)

        system_control_config: ControlConfig | None = None
        overwrite_system = True

        # Open or create alternate config file for systems with special controllers/settings
        # If the system/game is set to per game config, don't try to open/reset an existing file, only write if it's blank or going to the shared cfg folder
        if mess_controls is not None:
            system_control_config = ControlConfig(self.cfg_path / f'{self.mess_model}.cfg', self.mess_model)
            overwrite_system = not (
                system_control_config.exists()
                and (self.config.get_bool('customcfg') or self.config.get_bool('pergamecfg'))
            )

            # Hide the LCD display on CD-i
            if use_controls == 'cdimono1':
                system_control_config.remove_system_elements('video')
                system_video = system_control_config.add_system_element('video')
                system_control_config.create_child_element(
                    system_video, 'target', index='0', view='Main Screen Standard (4:3)'
                )

            # If using BBC keyboard controls, enable keyboard to gamepad
            if use_controls == 'bbc':
                system_control_config.add_input_element('keyboard', tag=':', enabled='1')

        # Don't configure controllers if guns are present and "use_guns" is on
        if not (self.config.use_guns and self.guns):
            # Fill in controls on cfg files
            for nplayer, controller in enumerate(self.controllers, start=1):
                mappings_use = mappings.copy()
                if 'joystick1up' not in controller.inputs:
                    mappings_use['JOYSTICK_UP'] = 'up'
                    mappings_use['JOYSTICK_DOWN'] = 'down'
                    mappings_use['JOYSTICK_LEFT'] = 'left'
                    mappings_use['JOYSTICK_RIGHT'] = 'right'

                for mapping, mapped_key in mappings_use.items():
                    if mapped_key in controller.inputs:
                        if mapping in ['START', 'COIN']:
                            _generate_special_port_element(
                                controller,
                                default_control_config,
                                'standard',
                                nplayer,
                                mapping + str(nplayer),
                                mapped_key,
                                _RETRO_PAD_MAPPINGS[mapped_key],
                            )
                        else:
                            _generate_port_element(
                                controller,
                                default_control_config,
                                nplayer,
                                mapping,
                                mapped_key,
                                _RETRO_PAD_MAPPINGS[mapped_key],
                                False,
                                alt_buttons,
                            )
                    else:
                        rmapping = reverse_mapping(mapped_key)
                        if rmapping in _RETRO_PAD_MAPPINGS:
                            _generate_port_element(
                                controller,
                                default_control_config,
                                nplayer,
                                mapping,
                                mapped_key,
                                _RETRO_PAD_MAPPINGS[rmapping],
                                True,
                                alt_buttons,
                            )

                # UI Mappings
                if nplayer == 1:
                    # Down
                    _generate_combo_port_element(
                        controller,
                        default_control_config,
                        'standard',
                        'UI_DOWN',
                        'DOWN',
                        mappings_use['JOYSTICK_DOWN'],
                        _RETRO_PAD_MAPPINGS[mappings_use['JOYSTICK_DOWN']],
                    )
                    # Left
                    _generate_combo_port_element(
                        controller,
                        default_control_config,
                        'standard',
                        'UI_LEFT',
                        'LEFT',
                        mappings_use['JOYSTICK_LEFT'],
                        _RETRO_PAD_MAPPINGS[mappings_use['JOYSTICK_LEFT']],
                    )
                    # Up
                    _generate_combo_port_element(
                        controller,
                        default_control_config,
                        'standard',
                        'UI_UP',
                        'UP',
                        mappings_use['JOYSTICK_UP'],
                        _RETRO_PAD_MAPPINGS[mappings_use['JOYSTICK_UP']],
                    )
                    # Right
                    _generate_combo_port_element(
                        controller,
                        default_control_config,
                        'standard',
                        'UI_RIGHT',
                        'RIGHT',
                        mappings_use['JOYSTICK_RIGHT'],
                        _RETRO_PAD_MAPPINGS[mappings_use['JOYSTICK_RIGHT']],
                    )
                    # Select
                    _generate_combo_port_element(
                        controller,
                        default_control_config,
                        'standard',
                        'UI_SELECT',
                        'ENTER',
                        'a',
                        _RETRO_PAD_MAPPINGS['a'],
                    )

                if mess_controls is not None:
                    for thisControl in mess_controls.values():
                        if nplayer == thisControl.player and system_control_config is not None:
                            if thisControl.type == 'analog':
                                _generate_analog_port_element(
                                    controller,
                                    system_control_config,
                                    thisControl.tag,
                                    nplayer,
                                    thisControl.key,
                                    mappings_use[thisControl.incMapping],
                                    mappings_use[thisControl.decMapping],
                                    _RETRO_PAD_MAPPINGS[mappings_use[thisControl.incUseMapping]],
                                    _RETRO_PAD_MAPPINGS[mappings_use[thisControl.decUseMapping]],
                                    thisControl.reversed,
                                    thisControl.mask,
                                    thisControl.default,
                                    thisControl.delta,
                                    thisControl.axis,
                                )
                            elif thisControl.type == 'combo':
                                _generate_combo_port_element(
                                    controller,
                                    system_control_config,
                                    thisControl.tag,
                                    thisControl.key,
                                    thisControl.kbMapping,
                                    thisControl.mapping,
                                    _RETRO_PAD_MAPPINGS[mappings_use[thisControl.useMapping]],
                                    thisControl.reversed,
                                    thisControl.mask,
                                    thisControl.default,
                                )
                            elif thisControl.type in ('special', 'main'):
                                _generate_special_port_element(
                                    controller,
                                    system_control_config if thisControl.type == 'special' else default_control_config,
                                    thisControl.tag,
                                    nplayer,
                                    thisControl.key,
                                    thisControl.mapping,
                                    _RETRO_PAD_MAPPINGS[mappings_use[thisControl.useMapping]],
                                    thisControl.reversed,
                                    thisControl.mask,
                                    thisControl.default,
                                )

        # save the config file
        # mameXml = open(configFile, "w")
        # TODO: python 3 - workawround to encode files in utf-8
        if overwrite_mame:
            default_control_config.save()

        # Write system config (if used, custom config is turned off or file doesn't exist yet)
        if mess_controls is not None and overwrite_system and system_control_config is not None:
            system_control_config.save()

        # Light gun crosshair visibility - MAME only honors this from the driver-specific
        # (system-level) cfg file, not from default.cfg, so it needs its own file per driver.
        # Done last so it merges with (rather than races) any system config written above.
        self.write_crosshair_config(self.mess_model or self.rom.stem)

    def write_crosshair_config(self, driver_name: str, /) -> None:
        # MAME only loads <crosshairs> from the per-driver (SYSTEM level) cfg file, unlike
        # controls which are also read from default.cfg. So each driver needs its own file.
        # Not done through ControlConfig: that resets the <input> section, which would wipe
        # the per-game remaps MAME itself saves into this file.
        config_file = self.cfg_path / f'{driver_name}.cfg'

        # Don't overwrite if using custom configs
        if config_file.exists() and self.config.get_bool('customcfg'):
            return

        config = minidom.Document()
        if config_file.exists():
            try:
                config = minidom.parse(str(config_file))
            except Exception:
                pass  # reinit the file

        mameconfig = _get_or_create(config, config, 'mameconfig')
        mameconfig.setAttribute('version', '10')
        system = _get_or_create(config, mameconfig, 'system')
        system.setAttribute('name', driver_name)

        for element in system.getElementsByTagName('crosshairs'):
            system.removeChild(element).unlink()
        crosshairs = config.createElement('crosshairs')
        system.appendChild(crosshairs)

        show_crosshair = self.config.get(
            'mame_gun_crosshair', 'enabled' if self.emulator.guns_need_crosses else 'disabled'
        )
        crosshair_mode = '1' if show_crosshair == 'enabled' else '0'
        for player in range(10):  # MAME's MAX_PLAYERS; unused players are ignored on load
            crosshair = config.createElement('crosshair')
            crosshair.setAttribute('player', str(player))
            crosshair.setAttribute('mode', crosshair_mode)
            crosshairs.appendChild(crosshair)

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with codecs.open(str(config_file), 'w', 'utf-8') as mame_xml:
            # remove ugly empty lines while minicom adds them...
            mame_xml.write(os.linesep.join([s for s in config.toprettyxml().splitlines() if s.strip()]))


def _get_or_create(
    document: minidom.Document, parent: minidom.Document | minidom.Element, name: str, /
) -> minidom.Element:
    if elements := document.getElementsByTagName(name):
        return elements[0]

    element = document.createElement(name)
    parent.appendChild(element)
    return element
