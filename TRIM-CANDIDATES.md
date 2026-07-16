# TRIM-CANDIDATES.md

Research pass into what else could be cut from the `x86_64-arcade` build
beyond the systems tree and Nvidia. **Nothing here has been implemented —
these are options to pick from, not a queued task list.** No config/code
changes were made while producing this doc.

## Recap: what's already trimmed, and why the rest is harder

Two trims are done:
- The systems tree — `BR2_PACKAGE_BATOCERA_ALL_SYSTEMS=n` +
  hand-picked `BATOCERA_ARCADE_SYSTEMS`/`BATOCERA_RETROARCH`
  (`configs/batocera-x86_64-arcade.board`).
- Nvidia — excluded via `board/batocera/x86/local-patches/no-nvidia.patch`,
  which comments out one forced `select` line in
  `package/batocera/core/batocera-system/Config.in`.
- Kodi — `BR2_PACKAGE_BATOCERA_KODI21=y` removed directly from the board
  file (it was a plain, unforced flag, so no patch was needed).

Everything below is a different shape of problem than Kodi: it's pulled in
via **unconditional Kconfig `select`** from one of a few always-on
umbrellas (`BATOCERA_SYSTEM`, `BATOCERA_GPU_X86`, `BATOCERA_XORG`,
`BATOCERA_LINUX_FIRMWARES`), so — same as Nvidia — none of it can be turned
off with a defconfig line. Setting `BR2_PACKAGE_FOO=n` in the board file
gets silently re-forced to `y`. Actually removing any of it means a small
source patch to `Config.in` (or, for firmware, the packaging `.mk`), in the
same isolated-patch-file style as `no-nvidia.patch` — see "How to apply"
at the end.

## Tier 1 — highest impact, lowest usability risk

These are the best next candidates: real space/build-time savings, and
low/no cost for a single-known-machine, AMD, no-lightgun-yet, offline
arcade cabinet.

### GPU driver trim

`BATOCERA_GPU_X86` (`package/batocera/core/batocera-system/Config.in:2367`)
unconditionally selects Mesa Gallium drivers for **every non-Nvidia GPU
vendor**, not just AMD:

```
package/batocera/core/batocera-system/Config.in:2376-2384
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_I915        # Intel legacy
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_CROCUS      # Intel Gen4-7
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_SVGA
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_IRIS        # Intel Gen8+
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_NOUVEAU
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_R600        # legacy AMD
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_RADEONSI    # keep — current AMD
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_VIRGL       # keep — virtio-gpu/VM passthrough
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_R300        # very old AMD
select BR2_PACKAGE_MESA3D_GALLIUM_DRIVER_ZINK        # keep — Vulkan-over-GL fallback
```

On known-AMD hardware, `RADEONSI` (+ `ZINK` as a fallback, + `VIRGL` if
this ever runs in a VM) is likely all that's needed. `I915`/`CROCUS`/`IRIS`
(Intel), `NOUVEAU` (Nvidia open driver — redundant with the Nvidia
exclusion already in place), `R600`/`R300` (pre-GCN AMD cards, not
relevant to modern AMD hardware), and `SVGA` (VMware) are dead weight.
Same fix shape as the Nvidia patch: comment out the unwanted `select`
lines. Trims Mesa build time (Mesa is one of the larger packages in the
build) and image size.

### Firmware trim

`BATOCERA_LINUX_FIRMWARES` → `alllinuxfirmwares`
(`package/batocera/firmwares/alllinuxfirmwares/alllinuxfirmwares.mk`)
already prunes a lot: SmartNIC/mainframe blobs unconditionally, and
ARM/mobile SoC vendor directories when building for x86_64
(`ALLLINUXFIRMWARES_REMOVE_DIRS` gains `airoha`, `amlogic`, `imx`,
`rockchip`, `qcom`, etc. under `ifeq ($(BR2_PACKAGE_BATOCERA_TARGET_X86_64_ANY),y)`,
lines 26–34). But that x86_64 branch **doesn't touch GPU or wifi/BT vendor
firmware at all** — a pure-ARM build branch a few lines below (lines 37–44)
already knows how to strip `nvidia`, `amd`/`amdgpu`, `i915`/`xe`/`intel/*`
directories, but that logic only runs for `arm`/`aarch64` targets, not
x86_64. Net effect: this x86_64 build ships Nvidia GPU firmware (despite
having no Nvidia driver at all), full Intel GPU firmware, and every wifi/BT
chipset vendor's blobs (Broadcom, Mediatek, Realtek, Qualcomm `ath*`, etc.)
regardless of what's actually in the machine.

Same mechanism, extended: add an x86_64-specific removal branch (or extend
the existing one) dropping at minimum `nvidia` (no driver uses it) and,
once known, whichever wifi/BT vendor directories don't match the actual
NIC/BT chipset. **Open question, not a ready-to-apply recommendation**:
this needs the target machine's actual wifi/BT chipset identified first —
guessing wrong strips firmware a real device needs. Moderate ongoing
maintenance cost too, since it tracks the upstream `linux-firmware` tree
and directory names can shift between versions (same caveat that already
applies to the existing prune list).

## Tier 2 — moderate impact, usability trade-offs to weigh

### Desktop-app bundle inside `BATOCERA_XORG`

`BATOCERA_XORG` (`Config.in:2321`) selects more than an X server: `openbox`
(window manager), `pcmanfm` (+`gvfs`, icon theme — file manager),
`l3afpad` (text editor), `touchegg` (touch gesture daemon), `unclutter`
(cursor hider), `xterm`, and — confirmed by direct grep —
`BR2_PACKAGE_BATOCERA_DESKTOPAPPS` (lines 2312/2356, desktop `.desktop`
launchers for emulator config GUIs) and `BR2_PACKAGE_BATOCERA_CONTROLCENTER`
(line 181, a GTK on-screen control panel) are *also* gated on this same
Xorg/Xwayland block, not independent options.

On a kiosk-style cabinet that only ever runs EmulationStation/RetroArch,
this whole desktop-environment layer is plausibly unused. **Open
question**: core Xorg + the `xf86-video-ati`/`nouveau` ddx drivers +
`libinput` may still be required underneath for AMD display mode-setting
even if the desktop-app layer is dropped — this would need testing
against how Batocera actually starts its video output before trimming,
not something to assume from static config reading.

### Network/remote-access services under `BATOCERA_SYSTEM`

`BATOCERA_SYSTEM` (the package everything else depends on) force-selects,
with no independent Kconfig toggle:

| Service | `select` | Purpose |
|---|---|---|
| OpenVPN + WireGuard tools/service | lines ~220–233 | VPN client |
| Syncthing | line ~322 | P2P file sync across Batocera devices |
| Rclone | line ~323 (x86_64) | Cloud storage sync |
| Flatpak + Bauh | lines ~318–319 (x86_64) | Flatpak app store/manager |
| Pacman | line ~317 | Arch-style package manager |
| Mosquitto (client) | line ~483 | MQTT, for LED/marquee hardware |
| MDADM | line ~487 | Software RAID tools |
| NFC | line ~490 | NFC tag support |
| DMD simulator / DMD play (Rust) | lines ~379–381 | Virtual pinball dot-matrix display |
| Backglass | line ~383 | Virtual pinball backglass support |

All of these are plausibly irrelevant to a single offline arcade cabinet
with no pinball cabinet hardware. **Deliberately not lumping in**: Samba4
+ WSDD (network share), Dropbear (SSH), GESFTPserver (SFTP), and Avahi/mDNS
— these are also unconditional `select`s from the same package, but are
commonly how people actually get ROMs onto a Batocera box and get a shell
for maintenance, so cutting them has real day-to-day cost even on a
single-purpose cabinet. Worth deciding on deliberately rather than cutting
by default. Most of the above (all of them, really) also have a *runtime*
on/off switch in `batocera.conf`/init.d scripts (e.g. `system.samba.enabled`)
— so disabling at runtime needs no rebuild, but the binaries still ship in
the image either way; only a Config.in patch actually removes them from
the build.

### Lightgun drivers

`BATOCERA_GUNS` (`Config.in:1884`) unconditionally selects ~15 lightgun
driver/config packages (Aimtrak, Sinden, GunCon, SAMCO, GUN4IR, etc.) plus
calibration art. Presented here as a **question**: arcade cabinets
commonly do use lightguns (House of the Dead, Time Crisis, etc.), so this
isn't a default recommendation — only worth cutting if lightgun support is
confirmed unwanted.

## Tier 3 — trivial, low value

- `es-background-musics` (`package/batocera/emulationstation/es-background-musics/`)
  — ~11 small `.ogg` menu-music tracks, forced-selected by `BATOCERA_SYSTEM`.
  A one-line `select` removal would cut it, but the size is a few MB at
  most — mentioned for completeness, not worth prioritizing.

## Not worth touching

- `BATOCERA_EXTRAS` — confirmed to be an empty umbrella today (no `select`
  lines at all in this tree). Nothing to trim; it's a no-op flag.
- `BATOCERA_TOOLS` — small diagnostic/sysadmin tools (vim, htop, evtest,
  switchres, etc.), low footprint, generally useful for a personal build.
- Themes — `es-theme-carbon` is the *only* ES theme package in this tree;
  there's no multi-theme bloat to cut here, this fork already ships one
  theme.

## Stale-artifact note (unrelated to this investigation)

`configs/batocera-x86_64-arcade_defconfig` (the committed/generated
Buildroot defconfig) still contains `BR2_PACKAGE_BATOCERA_KODI21=y` on
line 144 — a leftover from before Kodi was removed from the `.board`
source file. It'll self-correct the next time `make x86_64-arcade-defconfig`
or `-config` runs; noted here only so it isn't mistaken for Kodi still
being enabled if this generated file is checked directly.

## How to apply any of these later

Same isolated-patch-file pattern as `board/batocera/x86/local-patches/no-nvidia.patch`:
one new patch file per trim (or one combined patch), commenting out the
specific `select` lines in `package/batocera/core/batocera-system/Config.in`
(or editing `ALLLINUXFIRMWARES_REMOVE_DIRS` for the firmware case), applied
with `git apply` before generating a defconfig. Keeping each as a
standalone patch — rather than editing the shared file directly — keeps
them easy to review, drop, or regenerate independently, and keeps this
checkout easy to resync with upstream batocera later.
