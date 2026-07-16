# ADD-GEOLITH.md

Research notes for adding **Geolith** (https://github.com/libretro/geolith-libretro),
a libretro core for Neo Geo, as a selectable emulator for the `neogeo`
system in EmulationStation.

**Status: implemented (2026-07-14).** See
`package/batocera/emulators/retroarch/libretro/libretro-geolith/`,
`es_systems.yml`'s `neogeo`/`neogeocd` blocks, and the "Geolith case study"
section in `USER-INSTRUCTIONS.md` for the writeup. One correction vs. the
research below, confirmed by actually building the package
(`make x86_64-arcade-pkg PKG=libretro-geolith`) rather than trusting a
first-pass fetch of upstream's Makefile: it needs no
`BR2_INSTALL_LIBSTDCPP` guard (confirmed pure C, no C++ anywhere in its
build) — but it **does** link `-lz` (an early WebFetch-based read of the
Makefile only surfaced `-lm` for the `unix` platform and missed the zlib
link; the real build command ends `... -flto -lz -lm`), so the original
research's "only external system library is zlib" claim was right all
along. Not a blocker either way — zlib is already present across every
batocera target regardless. Pinned commit:
`c5b57a6b31b7abef4a8a9b521cae58d653e28154` (no tagged releases exist
upstream). The rest of this document is left as-is as the original
research trail.

## Verdict up front

**Packaging effort is low** — it's a well-worn, copy-paste-and-adapt
pattern this repo already uses for ~140 other libretro cores, and Geolith's
build is clean (self-contained, one external dependency, proven
cross-compilation via Recalbox/Lakka). **The real cost isn't the build —
it's that Geolith uses a different ROM file format than the Neo Geo cores
already in batocera**, which is a rom-library/UX question, not a
build-system blocker. See "The ROM format caveat" below before doing
anything else with this.

## What Geolith is

- Author: Rupert Carmichael (Neo Geo CD support: Romain Tisserand).
  Upstream non-libretro repo: https://gitlab.com/jgemu/geolith. Libretro
  port: https://github.com/libretro/geolith-libretro.
- License: **BSD-3-Clause** — cleaner than FBNeo's "Non-commercial" license
  (as recorded in this repo's `libretro-fbneo.mk`), no GPL entanglement.
  Bundled deps (libretro-common, miniz, Musashi, YMFM-C, Speex Resampler)
  are all MIT/BSD-3-Clause too.
- Actively maintained: commits within weeks of this research, a security
  fix merged May 2026, 32 stars / 14 forks — small but healthy.
- Positioning: describes itself as instruction-level-accurate, claims
  compatibility with 100% of commercial Neo Geo AES and MVS titles plus
  100% of the Neo Geo CD library. Framed as **console (AES) first**, unlike
  FBNeo/MAME which are arcade (MVS) first — it still supports MVS mode.
  Known gaps: video timing isn't yet cycle-accurate, one obscure prototype
  can't be emulated (missing SRAM dump), no dedicated JAMMA PCB / PAL mode.

## Precedent: already packaged elsewhere

- **Recalbox**: packaged and confirmed working on RPi0/1/3/4/400/5, Odroid
  XU4, OGA/OGS/RG351, RG353, and PC x86.
- **Lakka**: added in Lakka 5.0 (RetroArch 1.17.0 base).
- **RetroPie**: available via the standard libretro buildbot.
- No distro-specific packaging pitfalls reported anywhere. This is a
  positive cross-check — batocera wouldn't be the first to cross-compile
  this core for ARM SBCs or x86.
- Confirmed via `grep -rli geolith` across this entire repo (tracked and
  untracked, excluding `output/`): **zero existing references**. This
  would be a from-scratch package, not resuming stale work.

## Build system

Standard libretro-style plain `Makefile` at `libretro/Makefile` (not repo
root), invoked as `make -C libretro platform=<target>`. Respects `CC`,
`CFLAGS`, `DEBUG=1` and a wide `platform=` value set (unix, various
ARM/RPi/console variants) the same way virtually every libretro core does
— this is exactly the shape this repo's existing `.mk` packages already
target.

Dependencies are almost entirely vendored under `deps/` (libretro-common,
lzma, miniz, speex, zstd). **The only external system library is zlib**
(`-lz`), which is already present across every batocera target. Upstream
CI already builds linux-x64/i686/aarch64, Windows, macOS, Android, iOS,
tvOS, webOS — cross-compilation is proven, not something batocera would be
pioneering.

## Packaging checklist (mirrors this repo's existing libretro-core convention)

Reference template: **`libretro-gambatte`** is the closest structural
match among existing cores (single build dir, no arch-specific extra
flags) — closer than `libretro-fbneo`, which has RPi-model-specific
`platform=` overrides and extra `EXTRA_ARGS` (`USE_CYCLONE`, NEON, x86 DRC)
that Geolith likely won't need. Compare against
`package/batocera/emulators/retroarch/libretro/libretro-gambatte/` and
`.../libretro-fbneo/` directly when implementing.

1. **New directory**:
   `package/batocera/emulators/retroarch/libretro/libretro-geolith/` with
   three files:
   - `Config.in` — boilerplate:
     ```
     config BR2_PACKAGE_LIBRETRO_GEOLITH
         bool "libretro-geolith"
     	depends on BR2_INSTALL_LIBSTDCPP
         help
           A libretro Neo Geo emulator core.

     	  http://www.libretro.com
     ```
     (confirm whether Geolith is C or C++ at implementation time — its
     README describes it as ISO C11, so the `BR2_INSTALL_LIBSTDCPP` guard
     other cores use may not even be necessary; check what the upstream
     Makefile actually requires before copying it reflexively.)
   - `libretro-geolith.mk` — same idiom as every other core's `.mk`:
     `LIBRETRO_GEOLITH_VERSION` pinned to an upstream commit SHA (**pin
     this at implementation time** — not fixed here, it drifts),
     `LIBRETRO_GEOLITH_SITE = $(call github,libretro,geolith-libretro,$(LIBRETRO_GEOLITH_VERSION))`,
     `LIBRETRO_GEOLITH_LICENSE = BSD-3-Clause`,
     `LIBRETRO_GEOLITH_DEPENDENCIES += retroarch`,
     `LIBRETRO_GEOLITH_EMULATOR_INFO = geolith.libretro.core.yml`,
     `LIBRETRO_GEOLITH_PLATFORM = $(LIBRETRO_PLATFORM)` (shared variable
     from `retroarch.mk`), build via
     `-C $(@D)/libretro -f Makefile platform="$(LIBRETRO_GEOLITH_PLATFORM)"`,
     install `geolith_libretro.so` to
     `$(TARGET_DIR)/usr/lib/libretro/`, end with
     `$(eval $(generic-package))` + `$(eval $(emulator-info-package))`.
   - `geolith.libretro.core.yml` — see "Core options" below for what goes
     in `custom_features`; at minimum needs a `systems:` entry associating
     it with `neogeo`, e.g. `systems: [{name: neogeo}]` (a minimal version
     with no `custom_features` is a valid starting point — see BIOS section).
2. **Register the Kconfig option**: add a `source
   "$BR2_EXTERNAL_BATOCERA_PATH/package/batocera/emulators/retroarch/libretro/libretro-geolith/Config.in"`
   line to the root `Config.in`'s cores menu — every existing core has one
   (e.g. gambatte's is at line 241, fbneo's at line 259 as of this
   writing). Easy to forget; without it the option never appears in
   `menuconfig` at all.
3. **Wire it into the neogeo system**: `es_systems.yml`'s `neogeo:` block
   currently looks like this (verified directly against the file):
   ```yaml
   neogeo:
     name:       Neo-Geo
     manufacturer: SNK
     release: 1990
     hardware: console
     extensions: [7z, zip]
     platform:   neogeo, arcade
     emulators:
       libretro:
         fbalpha:      { requireAnyOf: [BR2_PACKAGE_LIBRETRO_FBALPHA]        }
         fbneo:        { requireAnyOf: [BR2_PACKAGE_LIBRETRO_FBNEO]          }
         imame4all:    { requireAnyOf: [BR2_PACKAGE_LIBRETRO_IMAME]          }
         mame078plus:  { requireAnyOf: [BR2_PACKAGE_LIBRETRO_MAME2003_PLUS]  }
         mame:         { requireAnyOf: [BR2_PACKAGE_LIBRETRO_MAME]           }
       mame:
         mame:         { requireAnyOf: [BR2_PACKAGE_MAME]                    }
       fba2x:
         fba2x:        { requireAnyOf: [BR2_PACKAGE_PIFBA]                   }
   ```
   Add a `geolith` line under `emulators.libretro`:
   `geolith: { requireAnyOf: [BR2_PACKAGE_LIBRETRO_GEOLITH] }`. See "The ROM
   format caveat" below about the `extensions: [7z, zip]` line at the top —
   this most likely needs to change too, not just the emulator list.
4. **Don't auto-select it by default (at least initially)**. FBNeo is
   force-included for everyone via `select BR2_PACKAGE_LIBRETRO_FBNEO #
   ALL` in `package/batocera/core/batocera-system/Config.in`'s
   `BATOCERA_ARCADE_SYSTEMS` block. Recommend **not** doing the same for
   Geolith yet, given the ROM-format friction below — leave it opt-in via
   `BR2_PACKAGE_LIBRETRO_GEOLITH=y` in a board file (the same "Option 2:
   turn on one specific system/emulator" pattern documented in
   `USER-INSTRUCTIONS.md`), and only promote it to a default `select` once
   the ROM-format UX question is actually resolved and tested.

## BIOS: required, same as existing cores (corrects an earlier assumption)

Geolith's own README states BIOS files "from a recent MAME set are
required": `aes.zip` (AES/home console), `neogeo.zip` (MVS/arcade + Universe
BIOS), `neocd.zip` + `neocdz.zip` (Neo Geo CD), `irrmaze.zip` (The
Irritating Maze). **This is not BIOS-optional** — an earlier hypothesis
going into this research assumed it might be; the upstream README says
otherwise, so don't repeat that assumption in future planning.

Practically, this isn't a new problem: FBNeo and MAME (already packaged
here) need the same MAME-set BIOS zips. Batocera's existing default for
FBNeo (`package/batocera/core/batocera-configgen/configgen/configgen/generators/libretro/libretroOptions.py`,
`_fbneo_options`) falls back to FBNeo's own bundled/emulated Universe BIOS
(`fbneo-neogeo-mode = UNIBIOS`) when the user hasn't supplied/selected
anything, rather than hard-requiring a user-supplied `neogeo.zip`. Geolith
doesn't have an equivalent "just work with no BIOS at all" fallback per its
README, so document for users that real BIOS files (from a MAME-set) are
expected, same as MAME/FBNeo already effectively expect.

## The ROM format caveat (the actual hard part)

**Geolith requires TerraOnion's `.NEO` file format** — a single,
one-file-per-game format also used by the MiSTer FPGA Neo Geo core —
**not** the MAME-style multi-file zip romsets that FBNeo/MAME (and the
current `neogeo:` es_systems.yml entry's `extensions: [7z, zip]`) use.
Neo Geo CD titles use standard `.bin/.cue` or `.chd`, which is not a
special case.

This means a user's existing Neo Geo (cartridge) ROM collection will
**not** run in Geolith without conversion. Upstream ships a `rename-neo.sh`
helper script; broader TerraOnion/MiSTer community conversion tooling
exists, but nothing built into batocera today.

**Open question for implementation time** (not resolved by this research —
needs hands-on testing): how to model this in `es_systems.yml` so
EmulationStation doesn't offer Geolith for `.zip`/`.7z` files (which it
can't use) or offer FBNeo/MAME for `.neo` files (which they can't use).
`es_systems.yml` already has a field for exactly this kind of mismatch —
`incompatible_extensions` (seen in use elsewhere, e.g. colecovision's
`clk` entry: `{ requireAnyOf: [BR2_PACKAGE_CLK], incompatible_extensions:
[7z] }`) — but no system in this file currently juggles two *different*
non-overlapping extension sets for different emulators of the *same*
system the way Geolith vs. FBNeo/MAME would require. Concretely, this
would likely mean:
- Adding `neo` to the system-level `extensions:` list.
- Adding `incompatible_extensions: [neo]` to the existing
  FBNeo/MAME/etc. entries, and `incompatible_extensions: [7z, zip]` to
  the new `geolith` entry.
- **Testing** that ES/configgen actually honor this combination correctly
  (filter the right emulator choices per file extension) before shipping
  it — this is inferred from the field's existence and one other usage,
  not confirmed against Geolith specifically.

## Core options

Geolith exposes libretro core-options v2 with categories **System**,
**Video**, **Hacks** — system type (AES/MVS/Universe BIOS), CD system type
(front/top loader, CDZ), region, memory card + write-protect, DIP
"settings mode", 4-player mode, free play, overscan masking, palette mode,
aspect ratio presets, sprite-per-line/overclock hacks.

This maps naturally onto a `custom_features:` block in
`geolith.libretro.core.yml`, modeled on FBNeo's
`fbneo-neogeo-mode-switch` pattern (dropdown `prompt`/`choices`, optional
`group` for UI grouping under "ADVANCED OPTIONS", nested under a `systems:
[{name: neogeo, custom_features: {...}}]` entry). **Exact option keys and
values were not extracted in this research pass** — read
`libretro/libretro_core_options.h` directly from the geolith-libretro repo
at implementation time to get the real `geolith_*` option strings rather
than guessing them. A minimal first cut can ship with no `custom_features`
at all (just `systems: [{name: neogeo}]`) and still function — richer
per-option UI can be layered on after the core itself works.

## Open questions to resolve before/during implementation

1. Exact `geolith_*` core-option keys/values (`libretro_core_options.h`).
2. How to actually make the `.neo` vs `.zip`/`.7z` extension split work in
   `es_systems.yml` — needs hands-on testing, not just field lookup.
3. Whether Geolith needs the `BR2_INSTALL_LIBSTDCPP` guard at all, given
   it's pure C — check what its Makefile actually requires.
4. Pin the actual upstream commit SHA when implementing (not fixed here).
5. Once ROM-format UX is sorted and tested, reconsider whether to promote
   it to a default `select` in `BATOCERA_ARCADE_SYSTEMS` like FBNeo, or
   keep it permanently opt-in given the `.NEO` conversion burden.
