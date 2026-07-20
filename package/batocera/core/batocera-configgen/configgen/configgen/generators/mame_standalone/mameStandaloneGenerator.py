from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from xml.dom import minidom

from PIL import Image

from ... import Command
from ...batoceraPaths import BATOCERA_SHARE_DIR, BIOS, CONFIGS, SAVES, SCREENSHOTS, USER_DECORATIONS, mkdir_if_not_exists
from ...exceptions import BatoceraException
from ...utils import bezels as bezelsUtil, videoMode
from ..Generator import Generator
from ..mame import mameControllers
from ..mame.mameGenerator import getMameControlScheme
from ..mame.mamePaths import MAME_BIOS, MAME_CHEATS
from .mameStandalonePaths import MAME_STANDALONE_CONFIG, MAME_STANDALONE_SAVES

if TYPE_CHECKING:
    from ...Emulator import Emulator
    from ...types import HotkeysContext, Resolution

_logger = logging.getLogger(__name__)

MAME_STANDALONE_BIN = "/usr/bin/standalone-mame/mame"


class MameStandaloneGenerator(Generator):
    """
    Second standalone MAME core: real upstream mamedev/mame, distinct from
    the "mame" core (package/batocera/emulators/mame, which is GroovyMAME).

    Scoped to the arcade `mame` and `neogeo` ES systems only - see
    ADD-STANDALONE-MAME.md. A direct Generator subclass rather than a
    MameGenerator subclass: MameGenerator hardcodes /usr/bin/mame/ in
    several places with no factored-out override point, and its MESS/
    computer-system branch (~40% of generate()) is unreachable dead code
    for the two systems this core supports - neither "mame" nor "neogeo"
    appears in data/mame/messSystems.csv. What IS reused (imported
    directly, not duplicated): mameControllers.generatePadsConfig() (the
    controller-config writer, fully parameterized by the cfgPath it's
    given) and getMameControlScheme() (a pure batocera-authored game-list
    heuristic, MAME-version-agnostic).

    Dropped versus MameGenerator, because stock MAME lacks GroovyMAME's
    bundled Switchres and out-of-tree lightgun patch:
    - switchres: always takes the plain -resolution branch.
    - -lightgunprovider udev / gun device routing: not emitted (depends on
      GroovyMAME's 005-lightgun-udev-driver.patch, not ported here).
    """

    def supportsInternalBezels(self) -> bool:
        return True

    def getHotkeysContext(self) -> HotkeysContext:
        return {
            "name": "mame",
            "keys": { "exit":  "KEY_ESC",
                      "menu":  "KEY_TAB",
                      "pause": "KEY_F5",
                      "reset": "KEY_F3",
                      "coin":  "KEY_5",
                      "fastforward": "KEY_PAGEDOWN",
                      "save_state" : [ "KEY_LEFTSHIFT", "KEY_F6" ],
                      "restore_state": [ "KEY_LEFTSHIFT", "KEY_F7" ] }
        }

    def generate(self, system, rom, playersControllers, metadata, guns, wheels, gameResolution):
        romBasename = rom.name
        romDirname = rom.parent

        # Generate userdata folders if needed - separate save/cfg tree from
        # groovy-mame's (see mameStandalonePaths.py), shared BIOS/cheats tree.
        standaloneMamePaths = [
            MAME_STANDALONE_CONFIG,
            MAME_STANDALONE_SAVES / "nvram",
            MAME_STANDALONE_SAVES / "input",
            MAME_STANDALONE_SAVES / "state",
            MAME_STANDALONE_SAVES / "diff",
            MAME_STANDALONE_SAVES / "comments",
            MAME_BIOS / "artwork" / "crosshairs",
            MAME_CHEATS,
            MAME_STANDALONE_SAVES / "plugins",
            MAME_STANDALONE_CONFIG / "ctrlr",
            MAME_STANDALONE_CONFIG / "ini",
        ]
        for checkPath in standaloneMamePaths:
            mkdir_if_not_exists(checkPath)

        commandArray: list[str | Path] = [ MAME_STANDALONE_BIN ]

        # set audio to pipewire to fix audio from 0.278
        commandArray += [ "-sound", "pipewire" ]
        # skip game info at start
        commandArray += [ "-skip_gameinfo" ]

        # arcade only (mame/neogeo) - no MESS softlist/BIOS-dir handling in scope
        commandArray += [ "-rompath", f"{romDirname};{MAME_BIOS};{BIOS}" ]

        # MAME various paths we can probably do better
        commandArray += [ "-bgfx_path",    "/usr/bin/standalone-mame/bgfx/" ]
        commandArray += [ "-fontpath",     "/usr/bin/standalone-mame/" ]
        commandArray += [ "-languagepath", "/usr/bin/standalone-mame/language/" ]
        commandArray += [ "-pluginspath", f"/usr/bin/standalone-mame/plugins/;{MAME_STANDALONE_SAVES / 'plugins'}" ]
        commandArray += [ "-samplepath",  MAME_BIOS / "samples" ]
        commandArray += [ "-artpath",     f"/var/run/mame_artwork/;/usr/bin/standalone-mame/artwork/;{MAME_BIOS / 'artwork'};{USER_DECORATIONS}" ]

        # Enable cheats
        commandArray += [ "-cheat" ]
        commandArray += [ "-cheatpath",    MAME_CHEATS ]

        commandArray += [ "-verbose" ]

        commandArray += [ "-nvram_directory", MAME_STANDALONE_SAVES / "nvram" ]

        # Set custom config path if option is selected or default path if not
        customCfg = system.config.get_bool("customcfg")
        cfgPath = MAME_STANDALONE_CONFIG / "custom" if customCfg else MAME_STANDALONE_CONFIG
        mkdir_if_not_exists(cfgPath)

        commandArray += [ "-cfg_directory"   ,    cfgPath ]
        commandArray += [ "-input_directory" ,    MAME_STANDALONE_SAVES / "input" ]
        commandArray += [ "-state_directory" ,    MAME_STANDALONE_SAVES / "state" ]
        commandArray += [ "-snapshot_directory" , SCREENSHOTS ]
        commandArray += [ "-diff_directory" ,     MAME_STANDALONE_SAVES / "diff" ]
        commandArray += [ "-comment_directory",   MAME_STANDALONE_SAVES / "comments" ]
        commandArray += [ "-homepath" ,           MAME_STANDALONE_SAVES / "plugins" ]
        commandArray += [ "-ctrlrpath" ,          MAME_STANDALONE_CONFIG / "ctrlr" ]
        commandArray += [ "-inipath" ,            f"{MAME_STANDALONE_CONFIG};{MAME_STANDALONE_CONFIG / 'ini'}" ]
        commandArray += [ "-crosshairpath" ,      MAME_BIOS / "artwork" / "crosshairs" ]

        # BGFX video engine - not GroovyMAME-specific, upstream MAME has had
        # bgfx since ~0.174.
        video = system.config.get("video")
        if video == "bgfx":
            commandArray += [ "-video", "bgfx" ]
            bgfxbackend = system.config.get("bgfxbackend", "automatic")
            commandArray += [ "-bgfx_backend", "auto" if bgfxbackend == "automatic" else bgfxbackend ]
            # NOTE: this core inherits the "mame" emulator's bgfxshaders
            # choice list, which includes GroovyMAME's custom
            # crt-geom-deluxe-* chains (not shipped by this package) -
            # picking one of those just won't resolve to a real chain file.
            commandArray += [ "-bgfx_screen_chains", system.config.get("bgfxshaders", "default") ]
        elif video == "accel":
            commandArray += ["-video", "accel" ]
        else:
            commandArray += [ "-video", "auto" ]

        # No Switchres in stock MAME (GroovyMAME-only) - always plain resolution.
        # The inherited "switchres" toggle in ES is a no-op for this core.
        commandArray += [ "-resolution", f"{gameResolution['width']}x{gameResolution['height']}" ]

        if system.config.get_bool("vsync"):
            commandArray += [ "-waitvsync" ]
        if system.config.get_bool("syncrefresh"):
            commandArray += [ "-syncrefresh" ]

        if (rotation := system.config.get("rotation")) in ["autoror", "autorol"]:
            commandArray += [ f"-{rotation}" ]

        if system.config.get_bool("artworkcrop"):
            commandArray += [ "-artwork_crop" ]

        if system.config.get_bool("enableui", True):
            commandArray += [ "-ui_active" ]

        # Load selected plugins - hiscore/data/offscreenreload ship in stock
        # MAME's plugins/ dir; coindrop is batocera-authored and copied in
        # from the groovy-mame package's source tree by standalone-mame.mk.
        pluginsToLoad = []
        if system.config.get_bool("hiscoreplugin", True):
            pluginsToLoad += [ "hiscore" ]
        if system.config.get_bool("coindropplugin"):
            pluginsToLoad += [ "coindrop" ]
        if system.config.get_bool("dataplugin"):
            pluginsToLoad += [ "data" ]
        if system.config.get_bool('offscreenreload'):
            pluginsToLoad += [ "offscreenreload" ]
        if pluginsToLoad:
            commandArray += [ "-plugins", "-plugin", ",".join(pluginsToLoad) ]

        # Mouse
        useMouse = system.config.get_bool('use_mouse')
        if useMouse:
            commandArray += [ "-dial_device", "mouse" ]
            commandArray += [ "-trackball_device", "mouse" ]
            commandArray += [ "-paddle_device", "mouse" ]
            commandArray += [ "-positional_device", "mouse" ]
            commandArray += [ "-mouse_device", "mouse" ]
            commandArray += [ "-ui_mouse" ]
            if not system.config.use_guns:
                commandArray += [ "-lightgun_device", "mouse" ]
                commandArray += [ "-adstick_device", "mouse" ]
        else:
            commandArray += [ "-dial_device", "joystick" ]
            commandArray += [ "-trackball_device", "joystick" ]
            commandArray += [ "-paddle_device", "joystick" ]
            commandArray += [ "-positional_device", "joystick" ]
            commandArray += [ "-mouse_device", "joystick" ]
            if not system.config.use_guns:
                commandArray += [ "-lightgun_device", "joystick" ]
                commandArray += [ "-adstick_device", "joystick" ]
        multiMouse = system.config.get_bool('multimouse')
        if multiMouse:
            commandArray += [ "-multimouse" ]

        # Guns: read the toggle so mameControllers still writes GUNCODE_*
        # crosshair/config entries, but no lightgun provider is configured
        # (needs GroovyMAME's 005-lightgun-udev-driver.patch, not ported
        # here per ADD-STANDALONE-MAME.md) - guns won't actually respond.
        useGuns = system.config.use_guns

        useWheels = system.config.use_wheels

        if system.config.get_bool('multiscreens'):
            screens = videoMode.getScreensInfos(system.config)
            if len(screens) > 1:
                commandArray += [ "-numscreens", str(len(screens)) ]

        commandArray += [ romBasename ]

        # bezels
        bezelSet = system.config.get_str('bezel') or None
        if system.config.get_bool('forceNoBezel'):
            bezelSet = None

        try:
            MameStandaloneGenerator.writeBezelConfig(bezelSet, system, rom, gameResolution, system.guns_borders_size_name(guns), system.guns_border_ratio_type(guns))
        except Exception:
            MameStandaloneGenerator.writeBezelConfig(None, system, rom, gameResolution, system.guns_borders_size_name(guns), system.guns_border_ratio_type(guns))

        buttonLayout = getMameControlScheme(system, rom)

        mameControllers.generatePadsConfig(cfgPath, playersControllers, "", buttonLayout, customCfg, "none", bezelSet, useGuns, guns, useWheels, wheels, useMouse, multiMouse, system)

        # If user provided a custom cmd file at the default location, use that as the customized commandArray
        if (defaultCustomCmdFilepath := Path(f"{rom}.cmd")).is_file():
            with defaultCustomCmdFilepath.open() as f:
                commandArray = f.read().splitlines()  # pyright: ignore

        # Change directory to standalone-mame folder (allows data plugin to load properly)
        os.chdir('/usr/bin/standalone-mame')
        return Command.Command(
            array=commandArray,
            env={
                "PWD": "/usr/bin/standalone-mame/",
                "XDG_CONFIG_HOME": CONFIGS,
                "XDG_CACHE_HOME": SAVES
                }
            )

    @staticmethod
    def writeBezelConfig(bezelSet: str | None, system: Emulator, rom: Path, gameResolution: Resolution, gunsBordersSize: str | None, gunsBordersRatio: str | None) -> None:
        # Simplified from mame.mameGenerator.MameGenerator.writeBezelConfig:
        # this core is arcade-only, so messSys is always "" here.
        tmpZipDir = Path("/var/run/mame_artwork") / rom.stem
        if tmpZipDir.exists():
            shutil.rmtree(tmpZipDir)

        if bezelSet is None and gunsBordersSize is None:
            return

        if (float(gameResolution["width"]) / float(gameResolution["height"]) < 1.6) and gunsBordersSize is None:
            return

        tmpZipDir.mkdir(parents=True)

        if bezelSet is None:
            if gunsBordersSize is not None:
                bz_infos = None
            else:
                return
        else:
            bz_infos = bezelsUtil.getBezelInfos(rom, bezelSet, system.name, 'mame')
            if bz_infos is None and gunsBordersSize is None:
                return

        if bz_infos is None:
            overlay_png_file = Path("/tmp/bezel_transstandalonemame_black.png")
            bezelsUtil.createTransparentBezel(overlay_png_file, gameResolution["width"], gameResolution["height"])
            bz_infos = { "png": overlay_png_file }

        if "mamezip" in bz_infos and bz_infos["mamezip"].exists():
            artFile = Path("/var/run/mame_artwork") / f"{rom.stem}.zip"
            if artFile.exists():
                artFile.unlink()
            artFile.symlink_to(bz_infos["mamezip"])
            return

        if "layout" in bz_infos and bz_infos["layout"].exists():
            (tmpZipDir / 'default.lay').symlink_to(bz_infos["layout"])
            pngFile = tmpZipDir / bz_infos["png"].name
            pngFile.symlink_to(bz_infos["png"])
            img_width, img_height = bezelsUtil.fast_image_size(bz_infos["png"])
        else:
            pngFile = tmpZipDir / "default.png"
            pngFile.symlink_to(bz_infos["png"])
            if "info" in bz_infos and bz_infos["info"].exists():
                bz_info_data = json.loads(bz_infos["info"].read_text())

                img_width: int = bz_info_data["width"]
                img_height: int = bz_info_data["height"]
                bz_y: int = bz_info_data["top"]
                bz_x: int = bz_info_data["left"]
                bz_bottom: int = bz_info_data["bottom"]
                bz_right: int = bz_info_data["right"]
                bz_alpha: float = bz_info_data.get("opacity", 1.0)

                bz_width = img_width - bz_x - bz_right
                bz_height = img_height - bz_y - bz_bottom
            else:
                img_width, img_height = bezelsUtil.fast_image_size(bz_infos["png"])
                _, _, rotate = MameStandaloneGenerator.getMameMachineSize(rom.stem, tmpZipDir)

                if rotate == 270 or rotate == 90:
                    bz_width = int(img_height * (3 / 4))
                else:
                    bz_width = int(img_height * (4 / 3))
                bz_height = img_height
                bz_x = int((img_width - bz_width) / 2)
                bz_y = 0
                bz_alpha = 1.0

            f = (tmpZipDir / "default.lay").open('w')
            f.write("<mamelayout version=\"2\">\n")
            f.write("<element name=\"bezel\"><image file=\"default.png\" /></element>\n")
            f.write("<view name=\"bezel\">\n")
            f.write(f"<screen index=\"0\"><bounds x=\"{bz_x}\" y=\"{bz_y}\" width=\"{bz_width}\" height=\"{bz_height}\" /></screen>\n")
            f.write(f"<element ref=\"bezel\"><bounds x=\"0\" y=\"0\" width=\"{img_width}\" height=\"{img_height}\" alpha=\"{bz_alpha}\" /></element>\n")
            f.write("</view>\n")
            f.write("</mamelayout>\n")
            f.close()

        if (bezel_tattoo := system.config.get_str('bezel.tattoo', "0")) != "0":
            tattoo: Image.Image | None = None

            if bezel_tattoo == 'system':
                tattoo_file = BATOCERA_SHARE_DIR / 'controller-overlays' / f'{system.name}.png'
                if not tattoo_file.exists():
                    tattoo_file = BATOCERA_SHARE_DIR / 'controller-overlays' / 'generic.png'
                try:
                    tattoo = Image.open(tattoo_file)
                except Exception:
                    _logger.error("Error opening controller overlay: %s", tattoo_file)
            elif bezel_tattoo == 'custom' and (bezel_tattoo_file := system.config.get_str('bezel.tattoo_file')) and (tattoo_file := Path(bezel_tattoo_file)).exists():
                try:
                    tattoo = Image.open(tattoo_file)
                except Exception:
                    _logger.error("Error opening custom file: %s", tattoo_file)
            else:
                tattoo_file = BATOCERA_SHARE_DIR / 'controller-overlays' / 'generic.png'
                try:
                    tattoo = Image.open(tattoo_file)
                except Exception:
                    _logger.error("Error opening custom file: %s", tattoo_file)

            if tattoo is not None:
                output_png_file = Path("/tmp/bezel_tattooed.png")
                back = Image.open(pngFile)
                tattoo = tattoo.convert("RGBA")
                back = back.convert("RGBA")
                tw, th = bezelsUtil.fast_image_size(tattoo_file)
                tatwidth = int(240/1920 * img_width)
                pcent = float(tatwidth / tw)
                tatheight = int(float(th) * pcent)
                tattoo = tattoo.resize((tatwidth, tatheight), Image.Resampling.LANCZOS)
                alphatat = tattoo.split()[-1]
                corner = system.config.get_str('bezel.tattoo_corner', 'NW')
                if corner.upper() == 'NE':
                    back.paste(tattoo, (img_width-tatwidth, 20), alphatat)
                elif corner.upper() == 'SE':
                    back.paste(tattoo, (img_width-tatwidth, img_height-tatheight-20), alphatat)
                elif corner.upper() == 'SW':
                    back.paste(tattoo, (0, img_height-tatheight-20), alphatat)
                else:
                    back.paste(tattoo, (0, 20), alphatat)
                imgnew = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 255))
                imgnew.paste(back, (0, 0, img_width, img_height))
                imgnew.save(output_png_file, mode="RGBA", format="PNG")

                try:
                    pngFile.unlink()
                except Exception:
                    pass

                pngFile.symlink_to(output_png_file)

        if gunsBordersSize is not None:
            output_png_file = Path("/tmp/bezel_gunborders.png")
            innerSize, outerSize = bezelsUtil.gunBordersSize(gunsBordersSize)
            bezelsUtil.gunBorderImage(pngFile, output_png_file, gunsBordersRatio, innerSize, outerSize, bezelsUtil.gunsBordersColorFomConfig(system.config))
            try:
                pngFile.unlink()
            except Exception:
                pass
            pngFile.symlink_to(output_png_file)

    @staticmethod
    def getMameMachineSize(machine: str, tmpdir: Path):
        proc = subprocess.Popen([MAME_STANDALONE_BIN, "-listxml", machine], stdout=subprocess.PIPE)
        (out, _) = proc.communicate()
        exitcode = proc.returncode

        if exitcode != 0:
            raise BatoceraException(f"standalone-mame -listxml {machine} failed")

        infofile = tmpdir / "infos.xml"
        f = infofile.open("w")
        f.write(out.decode())
        f.close()

        infos = minidom.parse(str(infofile))
        display = infos.getElementsByTagName('display')

        for element in display:
            iwidth = element.getAttribute("width")
            iheight = element.getAttribute("height")
            irotate = element.getAttribute("rotate")
            return int(iwidth), int(iheight), int(irotate)

        raise BatoceraException("Display element not found")
