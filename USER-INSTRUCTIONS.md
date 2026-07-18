# USER-INSTRUCTIONS.md

This file is for **you** (the human) — detailed, higher-level notes to help
you learn how this batocera.linux fork works as you go, not just a quick
reference. For terse technical notes aimed at future Claude Code sessions,
see `AGENTS.md` instead.

> **Convention for this project**: whenever a Claude Code session in this
> repo works out something useful for you to know or learn from, it should
> add it here automatically, in addition to keeping `AGENTS.md` up to date
> with anything a future CLI session would need. `AGENTS.md` stays terse and
> technical; this file can be as detailed/explanatory as it needs to be.
>
> There's also `PROJECT-OVERVIEW.md` at the repo root, with a different
> audience: generic, fork-agnostic batocera.linux/Buildroot knowledge
> (project structure, the config/build pipeline, build gotchas) written in
> neutral wiki-article voice, with nothing about this specific fork in it —
> aimed at eventually improving the project's actual wiki. When something
> learned is generic mechanics rather than a decision/incident specific to
> this fork, it belongs there (generalized, fork details stripped) instead
> of, or in addition to, this file.

---

## Adding systems back into the build

The stock batocera.linux build turns on every system via one option,
`BR2_PACKAGE_BATOCERA_ALL_SYSTEMS=y`. Our `configs/batocera-x86_64-arcade.board`
turns that off and hand-picks what to include instead, so the build stays
small and fast. When you want to add something back, there are two levels
to choose from.

### Background: how the selection actually works

Batocera uses Buildroot's Kconfig system (the same config language the
Linux kernel uses). Every optional piece of the OS is a `BR2_PACKAGE_*`
boolean flag. Some flags are just plain on/off; others are "umbrella"
options that `select` (force-enable) a whole group of other flags. This all
lives in one big file:
`package/batocera/core/batocera-system/Config.in`.

`BATOCERA_ALL_SYSTEMS` is the top of the tree — it selects eleven
category umbrellas, and each of those selects the individual emulator
packages for that category. Our board file skips the top-level umbrella and
turns on just the pieces we want underneath it.

There's a second important consequence of this: the EmulationStation menu
you see when you boot the image isn't a fixed list — it's **generated at
build time** from whichever emulator packages actually got compiled in. If
a system has zero enabled emulators, it just doesn't show up in the menu at
all. So "adding a system" always means "turning on the `BR2_PACKAGE_*` flag
for an emulator of that system" — there's no separate menu file to edit.

### Option 1 — turn on a whole category

Fastest way to add a broad group of systems at once. Add one of these lines
to `configs/batocera-x86_64-arcade.board`:

```
BR2_PACKAGE_BATOCERA_HANDHELD_SYSTEMS=y   # Game Boy, GBA, DS, PSP, etc.
BR2_PACKAGE_BATOCERA_COMPUTER_SYSTEMS=y   # Amiga and other home computers
BR2_PACKAGE_BATOCERA_CONSOLE_SYSTEMS=y    # N64, GameCube, Xbox, PlayStation, etc.
BR2_PACKAGE_BATOCERA_MSDOS_SYSTEMS=y
BR2_PACKAGE_BATOCERA_SCUMMVM_SYSTEMS=y
BR2_PACKAGE_BATOCERA_HOMEBREW_SYSTEMS=y
BR2_PACKAGE_BATOCERA_WINE_SYSTEMS=y
BR2_PACKAGE_BATOCERA_GAMESTREAM_SYSTEMS=y
BR2_PACKAGE_BATOCERA_PORTS_SYSTEMS=y
BR2_PACKAGE_BATOCERA_FLASH_SYSTEMS=y
```

Trade-off: categories like `CONSOLE_SYSTEMS` bundle a lot together (e.g.
turning it on gets you N64 *and* GameCube *and* Xbox *and* every
PlayStation generation all at once), which works against the "keep it
small and fast" goal that started this whole exercise.

### Option 2 — turn on one specific system/emulator

More surgical: pick the exact `BR2_PACKAGE_*` option for the emulator you
want, and set just that, without pulling in the rest of its category. This
is what the board file already does — the (currently commented-out) PS1/PS2
lines:

```
BR2_PACKAGE_DUCKSTATION=y   # PS1
BR2_PACKAGE_PCSX2=y         # PS2
```

**How to find the right option name for a system you want:**

1. Search the Config.in comments — every system has a `# System Name`
   header above its `select` lines:
   ```
   grep -n -B1 -A5 "# Nintendo 64\|# Sega Genesis\|# Super Nintendo" \
     package/batocera/core/batocera-system/Config.in
   ```
2. Or look it up in the master systems list, which is easier to browse by
   system name:
   `package/batocera/emulationstation/batocera-es-system/es_systems.yml`
   — each emulator entry for a system lists `requireAnyOf: [BR2_PACKAGE_...]`,
   which is exactly the flag to turn on.

Some systems have several emulator choices (e.g. PS1 has Duckstation, the
older Duckstation-legacy, and a couple of RetroArch/libretro cores) — you
can enable more than one and pick your favorite at runtime in
EmulationStation, or just enable the one you actually want to keep the
build lean.

### Option 3 — turn on a whole manufacturer

As of 2026-07-15, there are also seven manufacturer-scoped umbrellas:
`BATOCERA_NINTENDO_SYSTEMS`, `BATOCERA_SEGA_SYSTEMS`, `BATOCERA_SONY_SYSTEMS`,
`BATOCERA_COMMODORE_SYSTEMS`, `BATOCERA_AMSTRAD_SYSTEMS`,
`BATOCERA_NEC_SYSTEMS`, `BATOCERA_ATARI_SYSTEMS`. They work exactly like the
11 category umbrellas below — a `bool` option that `select`s every relevant
emulator package, with each `select` conditioned on the target architectures
it's actually buildable for (copied verbatim from wherever that package was
already selected elsewhere in the file).

**Unlike the 11 category umbrellas, these don't live in**
`package/batocera/core/batocera-system/Config.in` **at all.** That file is
one batocera upstream edits constantly (every new package addition touches
it), so a ~350-line addition there would be a standing merge-conflict risk
on every upstream sync, and easy to accidentally drag into any future
upstream contribution. Instead:

- The actual `config` blocks live in a brand-new, fork-only file:
  `package/batocera/custom-arcade/manufacturer-systems/Config.in`. Upstream
  has no knowledge of this path, so it can never conflict on sync, and it's
  unambiguous that nothing under `package/batocera/custom-arcade/` should
  ever go into an upstream PR.
- Kconfig only recognizes `config` symbols reachable via a `source` chain
  from the root `Config.in`, so *something* still has to point at that new
  file — there's no way around at least one line somewhere. That one line
  is delivered as a patch, not a permanent edit, using the exact same
  mechanism as the Nvidia-exclusion patch documented below:
  `board/batocera/x86/local-patches/manufacturer-systems.patch`, which adds
  ```
  source "$BR2_EXTERNAL_BATOCERA_PATH/package/batocera/custom-arcade/manufacturer-systems/Config.in"
  ```
  to the top-level `./Config.in` (right after the line that sources
  `core/batocera-system/Config.in`). Apply it the same way, and under the
  same circumstances, as `no-nvidia.patch` — see "The Nvidia-exclusion
  patch" section below, which now applies to both patches:
  ```
  git apply board/batocera/x86/local-patches/manufacturer-systems.patch
  ```
  Without it applied, the top-level `Config.in` is byte-for-byte identical
  to upstream and the seven options simply don't exist in the Kconfig tree
  (harmless — they're just invisible, not an error).

The difference from Option 1: those umbrellas group by *category*
(all consoles, regardless of maker); these group by *manufacturer*
(all Nintendo systems, spanning both console and handheld). Useful for
turning on "everything Nintendo" or "everything Sega" in one line, without
pulling in every other maker's systems the way `CONSOLE_SYSTEMS` would.

**As of 2026-07-15, all 7 are `=y` in `configs/batocera-x86_64-arcade.board`**
(still not selected by `BATOCERA_ALL_SYSTEMS` itself — just this board's
defconfig). They replaced what used to be a hand-picked "Phase 2a: PS1"
block there — `SONY_SYSTEMS` covers those same PS1 cores plus PS2/PS3/PSP/
Vita. Turning one on for a *different* board (or off again here) is the
same mechanism as Option 1: set/remove the `=y` line in that board's
defconfig. **Requires `manufacturer-systems.patch` applied first** (see
"The local `Config.in` patches" below) — without it, these `=y` lines in
the board file are silently inert, since Kconfig doesn't recognize a symbol
it never parsed.

One deliberate exception: `NINTENDO_SYSTEMS`'s Switch cores (`CITRON`,
`RYUJINX`) need `BR2_PACKAGE_BATOCERA_CORES_STILL_COMMERCIALIZED=y` as well
(their own `select` condition on top of `NINTENDO_SYSTEMS`), which is *not*
set in the arcade board — so Switch stays off there even with
`NINTENDO_SYSTEMS=y`; everything else under it (NES/SNES/N64/GameCube/Wii/
Wii U/handhelds) still builds.

What's in each:

| Manufacturer | What it covers |
|---|---|
| `NINTENDO_SYSTEMS` | NES, SNES, N64, GameCube/Wii, Wii U, Switch, Game Boy/Color, GBA, DS, 3DS, Virtual Boy, Game & Watch, Pokémon Mini |
| `SEGA_SYSTEMS` | Master System/Game Gear, Genesis/Mega Drive/32X, Saturn, Dreamcast/Naomi/Atomiswave, Model 2/3 arcade, Demul, Lindbergh |
| `SONY_SYSTEMS` | PS1, PS2, PS3, PSP, PS Vita |
| `COMMODORE_SYSTEMS` | C64/128/VIC-20/PET/Plus4/16, Amiga |
| `AMSTRAD_SYSTEMS` | Amstrad CPC and GX4000 |
| `NEC_SYSTEMS` | PC Engine, PC Engine CD, TurboGrafx-16, SuperGrafx |
| `ATARI_SYSTEMS` | Atari 2600, 7800, Jaguar |

A few scoping choices worth knowing, if you go looking for something and
don't find it:

- `SONY_SYSTEMS` deliberately includes the PSP and PS Vita handhelds
  alongside PS1–3, even though the original ask was just "PS1, PS2, PS3" —
  they're Sony too, and both have working x86_64 emulators.
- `ATARI_SYSTEMS` and `NEC_SYSTEMS` are deliberately narrower than
  "everything that manufacturer made". Atari's Lynx (handheld) and
  800/5200/ST computers, and NEC's PC-FX console and PC-88/98 computers,
  are *not* included. If you want those, they'd need adding by hand
  (Option 2) or a follow-up expansion of these umbrellas.
- Two items live in the source `Config.in` under a manufacturer's comment
  header but aren't actually that manufacturer's hardware, and were
  deliberately left out: `LIBRETRO_81` (a Sinclair ZX80/ZX81 core,
  mislabeled under an "Amstrad CPC" comment in the original file) and the
  Commander X16 (`X16EMU`, a modern community homage inspired by
  Commodore, not an official Commodore product).

### The 11 system categories, and what's actually in each

For reference, here's what each `BATOCERA_*_SYSTEMS` umbrella actually
selects (all defined in `package/batocera/core/batocera-system/Config.in`).
Skimming this is the fastest way to figure out which umbrella (if any) has
what you're after, before deciding between Option 1 (whole category) and
Option 2 (one system):

| Category | What it covers |
|---|---|
| `ARCADE_SYSTEMS` *(on)* | MAME, FinalBurn Neo, MAME2003-Plus, Sega Model 2/3, Naomi/Atomiswave (via Flycast/Redream), laserdisc games (Hypseus Singe) |
| `CONSOLE_SYSTEMS` | Home consoles: N64, GameCube/Wii, Xbox/Xbox 360, PlayStation 1–4, and more |
| `HANDHELD_SYSTEMS` | Game Boy/Color/Advance, Nintendo DS/3DS, PSP/Vita, and other handhelds |
| `COMPUTER_SYSTEMS` | Home computers — Amiga and similar |
| `MSDOS_SYSTEMS` | DOS games, via DOSBox / DOSBox-X / DOSBox Staging |
| `SCUMMVM_SYSTEMS` | ScummVM — the point-and-click adventure game engine (Monkey Island, etc.) |
| `HOMEBREW_SYSTEMS` | Homebrew/engine-based games: OpenBOR, Lutro (LÖVE), PyGame, Solarus, EasyRPG |
| `WINE_SYSTEMS` | Windows game compatibility layer (Wine) — lets Windows-only games/emulators run |
| `GAMESTREAM_SYSTEMS` | Game streaming clients — Moonlight (for streaming from a GameStream/Sunshine PC) |
| `PORTS_SYSTEMS` | Native source-ports of classic games: Doom (PrBoom), Quake, Diablo (DevilutionX), OutRun (Cannonball), etc. |
| `FLASH_SYSTEMS` | Adobe Flash game emulation (Ruffle, Lightspark) |

Only `ARCADE_SYSTEMS` is currently on in `configs/batocera-x86_64-arcade.board`.

### Where the actual package files live

Every one of the `BR2_PACKAGE_*` options above corresponds to a real
package directory with a `Config.in` (the toggle + its `bool "..."`
description + its dependencies) and a `.mk` file (how to actually build
it). Two places to look, depending on the emulator type:

- `package/batocera/emulators/<name>/` — standalone emulators that run as
  their own program (not through RetroArch), e.g. `mame/`, `duckstation/`,
  `pcsx2/`, `dolphin-emu/`, `flycast/`, `supermodel/`.
- `package/batocera/emulators/retroarch/libretro/libretro-<name>/` —
  libretro "cores" that plug into the RetroArch frontend, e.g.
  `libretro-fbneo/`, `libretro-mame/`, `libretro-mame2003-plus/`,
  `libretro-beetle-psx/`. RetroArch itself (`BR2_PACKAGE_RETROARCH`) is a
  separate package that hosts all of these.

A system can have both — e.g. PS1 has a standalone Duckstation *and*
libretro cores (Beetle PSX, SwanStation) as alternative choices for the
same system.

`package/batocera/emulationstation/batocera-es-system/es_systems.yml` is
the master reference list — browse it by system name to see every emulator
option batocera knows about for that system and the exact
`BR2_PACKAGE_*` flag each one needs (`requireAnyOf: [...]`).

`INCLUDED-EMUS.md` (repo root) is a point-in-time snapshot of what's
actually resolved to "on" for the current `x86_64-arcade` config — useful
to sanity-check the current state without re-deriving it by hand.

### Excluding things (the harder direction)

Adding is straightforward (Option 1/2 above). Removing something is easy
in some cases and requires a patch in others, depending on **how** it got
turned on:

- **Excluding a whole category you haven't turned on** — nothing to do,
  it's already off (this board file doesn't use
  `BATOCERA_ALL_SYSTEMS`, so every category starts off by default).
- **Excluding one specific system while its whole category is off** —
  also nothing to do, same reason.
- **Excluding one system from within a category you've turned ON** — this
  is where it gets interesting. Turning on `BATOCERA_CONSOLE_SYSTEMS=y`
  `select`s *every* console emulator as a forced Kconfig dependency. Just
  like the Nvidia case documented in `AGENTS.md`, setting e.g.
  `BR2_PACKAGE_XEMU=n` (Xbox) in the board file **will not stick** — Kconfig
  re-forces it back to `y` because the umbrella still selects it. To
  exclude one system from an otherwise-enabled category you have two
  options:
  1. Don't use the umbrella at all — hand-pick just the systems you want
     (this is Option 2 from earlier, and is what this fork does for
     everything so far).
  2. Patch `Config.in` to remove that one `select` line, the same way
     `board/batocera/x86/local-patches/no-nvidia.patch` does for Nvidia.
     Only worth it if you want *almost everything* in a big category
     except one or two things.
- **Excluding one emulator choice while keeping others for the same
  system** — easy, as long as you got there via Option 2 (hand-picking).
  Each emulator/core for a system is usually its own independent
  `BR2_PACKAGE_*` option (not chained together), so if you've enabled, say,
  `BR2_PACKAGE_DUCKSTATION=y` for PS1 but not
  `BR2_PACKAGE_LIBRETRO_BEETLE_PSX`, only Duckstation gets built — you
  don't need to do anything special to "exclude" the one you didn't ask
  for in the first place.

### Watch out: not everything is gated by the systems tree

Everything above (`ALL_SYSTEMS` → category umbrellas → individual
`BR2_PACKAGE_*` emulators) is one specific mechanism. Not every optional
piece of the image goes through it — **Kodi is a real example we hit**:
`BR2_PACKAGE_BATOCERA_KODI21=y` was sitting in
`configs/batocera-x86_64-arcade.board` (line 23, in the "System" section
near the top, not the "systems selection" block near the bottom) because it
was copied over wholesale from the stock `batocera-x86_64.board` when this
fork's board file was created. It has nothing to do with
`BATOCERA_ALL_SYSTEMS` or any category umbrella — it's just a plain
board-level flag (default `n`, no `select` forcing it on), the same way
`BR2_PACKAGE_TSLIB` or the syslinux/grub lines nearby are. Turning off
`ALL_SYSTEMS` doesn't touch it at all, so Kodi was quietly being built into
an otherwise arcade-only image.

Removed for this fork (media-center app, not a game system, not part of the
goal) simply by deleting that one line from the board file — no patch
needed, since nothing `select`s it back on.

**The lesson**: when you want to know what's *actually* going into an
image, don't reason from the systems tree alone — check the resolved
config directly:

```
grep <FLAG> output/x86_64-arcade/.config
```

or, for something you don't already have a flag name for, diff your board
file against the stock one it was based on
(`diff configs/batocera-x86_64.board configs/batocera-x86_64-arcade.board`)
to catch anything copied over that you didn't actually mean to keep.

### Applying a systems change

Whichever option you use, validate before you build — this is the same
sequence covered in more depth in "Triggering a build" below:

```
make x86_64-arcade-defconfig
make x86_64-arcade-config BATCH_MODE=1
grep BR2_PACKAGE_<NAME>=y output/x86_64-arcade/.config   # confirm it's on
make x86_64-arcade-build CMD="batocera-es-system-dirclean batocera-es-system" BATCH_MODE=1
make x86_64-arcade-build
```

`make x86_64-arcade-config` is fast (seconds) — it just resolves the Kconfig
tree and writes `output/x86_64-arcade/.config`, it doesn't compile
anything. That's your chance to double check the flag actually resolved to
`y` (grep for it) before kicking off a real build. Because Buildroot only
compiles what's newly enabled, and ccache caches anything you've built
before, adding one more system later is much faster than the very first
build was.

The `batocera-es-system` rebuild step is not optional, and it has to run
*before* the full `-build`, not after: that package's Buildroot stamps have
no dependency edge onto other packages' Kconfig state, so an incremental
build silently ships a stale `es_systems.cfg` and the new system won't
appear in EmulationStation even though the emulator itself built and
installed correctly. See "Debugging note (2026-07-14)" below for the full
trace of what this looks like when missed, and the `es_systems.cfg`
verification grep to confirm it worked.

## Adding a new emulator core for an existing system — the Geolith case study

`ADD-GEOLITH.md` (repo root) documents adding **Geolith**, a Neo Geo
libretro core, as an extra emulator choice for the existing `neogeo` /
`neogeocd` systems (implemented 2026-07-14). Two mechanics from that work
are worth understanding generally, since they'll come up again for any
future "new core for an existing system" addition:

**1. A new libretro core is almost always three small files, no Python
changes.** `package/batocera/emulators/retroarch/libretro/libretro-<name>/`
needs a `Config.in` (the Kconfig toggle), a `.mk` (fetch a pinned upstream
commit SHA, build with the core's own libretro `Makefile`, install the
resulting `.so` to `/usr/lib/libretro/`), and a `.core.yml` (registers
which system(s) it belongs to, plus optional `custom_features` for a
batocera-native options UI). The config-generator Python code
(`configgen/generators/libretro/libretroOptions.py`) only needs a new
function when a core's options need *translation* — e.g. FBNeo's Neo Geo
BIOS selector maps a friendly label to an internal DIP-switch setting via
`_fbneo_options()`. If a core's option keys already match what you want to
expose 1:1 (Geolith's do — `geolith_system_type: aes` is both the internal
key and a sensible user-facing value), the `.yml`'s `custom_features` block
is all you need; `generateCoreSettings()` just skips any core absent from
its dispatch dict.

**2. When one system needs two emulators that read genuinely different
file formats, the exclusivity lives in each core's own `.yml` file
(`exclude_extensions:` under its `systems:` entry) — not in
`es_systems.yml`.** Normally every emulator for a system reads the same
file types (that's why `neogeo`'s `extensions: [7z, zip]` used to just be
the MAME-romset format every core there understood). Geolith breaks that
assumption — it only reads TerraOnion's single-file `.neo` format, not
zip/7z MAME sets. Two separate things are needed: add the new format to
the system-level `extensions:` union in `es_systems.yml`
(`[7z, zip, neo]` — this part *is* read by the generator), and tell each
emulator what it *can't* read via `exclude_extensions:` inside that
emulator's own `systems:` entry in its own
`*.libretro.core.yml`/`*.emulator.yml` file — e.g.
`fbneo.libretro.core.yml`'s `- name: neogeo` entry gets
`exclude_extensions: [neo]`, `geolith.libretro.core.yml`'s gets
`exclude_extensions: [7z, zip]`. `clk.emulator.yml` (used by MSX
`msx1`/`msx2`, `apple2`, and several others) already used this same
`exclude_extensions:` idiom before Geolith did, so it's an established
pattern, not something invented for this case. `neogeocd` didn't need any
of this — Geolith's CD support already reads the same `.bin/.cue`/`.chd`
formats the existing `neocd` core does, so adding it there was just one
more core declaring `systems: [{name: neogeocd}]` with no extension
changes.

*(Corrected 2026-07-14 — the original version of this point said the fix
was an `incompatible_extensions:` field added directly under each emulator
in `es_systems.yml`'s per-system `emulators:` block. That looked right —
right field name, real precedent elsewhere in the file — but it doesn't
actually do anything: that whole `emulators:` block in `es_systems.yml` is
parsed for schema validity only and never read by the code that generates
the file EmulationStation actually loads. See the debugging note just
below for the full trace and why this went unnoticed at first.)*

**BIOS note, if you actually try to play something on Geolith:** unlike
FBNeo (which falls back to its own bundled/emulated Universe BIOS when you
haven't supplied one), Geolith's upstream README states it hard-requires
real MAME-set BIOS zips (`aes.zip`, `neogeo.zip`, `neocd.zip`/`neocdz.zip`)
placed in batocera's bios folder — there's no no-BIOS fallback path for it.

### Debugging note (2026-07-14): built cleanly, but invisible in EmulationStation

After building this fork with Geolith enabled and confirming
`geolith_libretro.so` was actually present in the image, two symptoms
remained: Geolith never appeared as a selectable core for `neogeo` in
EmulationStation, and `.neo` ROMs dropped into `roms/neogeo/` weren't
visible at all (only `.zip` showed). This turned out to be **two
independent bugs**, not one — worth understanding both, since each is a
general gotcha that will resurface for any future core addition, not just
Geolith.

**Bug A (the actual blocker): a stale `batocera-es-system` build.**
EmulationStation doesn't read `es_systems.yml` directly — it reads a
generated file, `target/usr/share/emulationstation/es_systems.cfg`,
produced at build time by the `batocera-es-system` Buildroot package. That
package's `.mk`
(`package/batocera/emulationstation/batocera-es-system/batocera-es-system.mk`)
runs a host Python tool, `batocera-build-es-data`, against `es_systems.yml`
plus the list of every *currently enabled* emulator package's
`*.libretro.core.yml`/`*.emulator.yml` (collected into `EMULATOR_INFO_PATHS`,
gated on each package's own Kconfig var by
`package/batocera/pkg-emulator-info.mk`). Buildroot's per-package stamp
tracking (`.stamp_built`, `.stamp_target_installed`, etc.) has **no
dependency edge from `batocera-es-system` onto other packages' Kconfig
state, or onto `es_systems.yml`'s content** — so editing that YAML, or
newly enabling a core package, does not invalidate `batocera-es-system`'s
existing stamps. On an incremental rebuild, `libretro-geolith` correctly
built (it was newly *selected*, so Buildroot had never built it before),
but `batocera-es-system` was skipped as "already built." Confirmed
directly by comparing timestamps: `es_systems.yml` was edited at 06:45,
`.config` regenerated at 06:56 with `BR2_PACKAGE_LIBRETRO_GEOLITH=y`, and
`libretro-geolith`'s build stamps were fresh at 06:47 — but
`batocera-es-system`'s stamps, and the shipped `es_systems.cfg`, were
still dated 01:07, from *before* any of those edits. The image got
repackaged with the old `es_systems.cfg` even though every other piece
(the `.so`, the Kconfig flag, the source YAML) was correct and current.

Fix: force a rebuild of just that one package whenever you edit
`es_systems.yml` or newly enable an emulator/core package — the same
targeted-rebuild pattern already documented above for the Perl/XS case:
```
make x86_64-arcade-build CMD="batocera-es-system-dirclean batocera-es-system" BATCH_MODE=1
```
then a normal `make x86_64-arcade-build` to fold the regenerated
`es_systems.cfg` into the image. Verify against the generated file
directly rather than trusting the source YAML looks right:
```
grep -A20 '<name>neogeo</name>' output/x86_64-arcade/target/usr/share/emulationstation/es_systems.cfg
```

**Bug B: `es_systems.yml`'s per-system `emulators:` block is dead code.**
Even after Bug A is fixed, the `incompatible_extensions:`/`requireAnyOf:`
fields originally added to `es_systems.yml`'s `emulators:` block do
nothing. Traced end to end in
`python-src/batocera-es-system/batocera_es_system/es_systems.py`: the
function that writes each `<system>` block
(`_system_dict_to_xml`) reads `es_systems.yml`'s `SystemDict` only for
`name`/`manufacturer`/`release`/`hardware`/`extensions`/`platform`/`group`/
`theme` — its `emulators:` field is never accessed. The actual
`<emulator>`/`<cores>`/`incompatible_extensions="..."` XML is built
entirely from a `Registry` (`registry.py`: `Registry.load_files` →
`get_systems_metadata`), populated purely from each package's own
`*.emulator.yml`/`*.libretro.core.yml` `systems:` declarations — and the
`incompatible_extensions` attribute specifically comes from that yml's
`exclude_extensions:` field, a completely different name in a completely
different file from what `es_systems.yml`'s `emulators:` block uses. The
real fix (see the corrected point 2 above) is `exclude_extensions:` added
to each core's own `systems:` entry — touched `geolith`, `fbneo`,
`mame078plus`, `mame` (libretro), `mame` (standalone), `fbalpha`, and
`imame4all`'s yml files for the `neogeo` case.

This bug went unnoticed on the first implementation pass because Bug A was
masking it — Geolith wasn't showing up in EmulationStation at all yet, so
there was no way to notice the exclusivity fields weren't taking effect
either. Once Bug A was fixed and the `exclude_extensions:` fix applied,
the regenerated `es_systems.cfg` showed exactly what was expected:
```
<extension>.7z .zip .neo</extension>
...
<core default="true" incompatible_extensions=".neo">fbneo</core>
<core incompatible_extensions=".7z .zip">geolith</core>
<core incompatible_extensions=".neo">mame</core>
<core incompatible_extensions=".neo">mame078plus</core>
```

**The general lesson**: when EmulationStation doesn't show something you
just added, trace it against the actual generated `es_systems.cfg` (or
`es_features.cfg`) under
`output/<target>/target/usr/share/emulationstation/` — not the source
`es_systems.yml`. The source file can be perfectly correct and current
while the generated artifact is stale (Bug A), and even once regenerated,
not every field in the source YAML that *looks* like the right lever is
actually consumed by the generator (Bug B). When in doubt, grep the actual
code path
(`python-src/batocera-es-system/batocera_es_system/{es_systems,registry}.py`)
for where a field is read, rather than pattern-matching off another
system's `es_systems.yml` entry that merely looks similar.

### Extending Geolith to other boards (it currently only builds for `x86_64-arcade`)

Geolith was only enabled and tested on this fork's `x86_64-arcade` target.
It is **opt-in everywhere** by design — `BR2_PACKAGE_LIBRETRO_GEOLITH` is
never `select`ed by `BATOCERA_ARCADE_SYSTEMS` in
`package/batocera/core/batocera-system/Config.in` the way FBNeo is, so on
every board (stock x86_64, any RPi, anything else) it stays off until that
board's `.board` file turns it on explicitly. What else is needed depends
on the target's CPU architecture:

**Enabling it on the stock x86_64 board** (`configs/batocera-x86_64.board`,
as opposed to this fork's `x86_64-arcade.board`) needs *only* one line:
```
BR2_PACKAGE_LIBRETRO_GEOLITH=y
```
No `.mk` changes required — `LIBRETRO_PLATFORM` resolves to plain `unix`
on any x86_64 target (`package/batocera/emulators/retroarch/retroarch/retroarch.mk:196`),
identical to what was already built and verified on `x86_64-arcade`.

### Debugging note (2026-07-14): Geolith options visible in ES but never applied at launch — a second, different stale-package bug

After the Bug A/Bug B fixes above got Geolith showing up correctly in
EmulationStation, a follow-up commit (`d31a1ff6ba`, "Add geolith options to
configgen") added a `_geolith_options()` function to
`configgen/generators/libretro/libretroOptions.py` so the AES/MVS/Universe
BIOS choice (and region/aspect/memcard/palette/etc.) picked in ES's
non-advanced settings would actually get written into RetroArch's
per-core options file at launch. Tested it, and the setting still had no
effect in-game — picking "MVS" in ES, the game still booted as if nothing
had been chosen. This turned out to be **the same root-cause pattern as Bug
A above (a stale Buildroot package), just hitting a different package**, so
it's worth writing up separately since the diagnostic path was different
and more general — it applies to any Python-source-only edit under
`package/batocera/core/batocera-configgen/`, not just Geolith.

**Diagnosing from a real launch log first.** Batocera writes a full debug
log for every game launch (`mylogs/es_launch_stdout.log` in this
conversation's case — copy it off the device however you'd normally pull
Batocera logs). Two things stood out:
- The `Settings` dict logged at launch correctly showed
  `'geolith_system_type': 'mvs'` — so ES *did* save the chosen value into
  `batocera.conf`, and configgen *did* read it back. The read side was
  fine.
- Every actual settings **write** goes through `UnixSettings.save()`
  (`configgen/settings/unixSettings.py`), which unconditionally logs
  `Writing <key> = <value> to <path>` at DEBUG level — and every other
  core's option writes appeared in the log (all the `retroarchcustom.cfg`
  writes), but there was no line at all for
  `.../cores/retroarch-core-options.cfg`, which is where
  `_geolith_options()` should have written `geolith_system_type` and
  friends. The write that should have produced that specific log line
  simply never happened — meaning the *running* code didn't contain
  `_geolith_options()` at all, despite the commit existing in the repo.

**Confirming the code itself was correct before assuming a rebuild
problem.** Before chasing a build issue, traced the whole path to rule out
an actual bug: `geolith.libretro.core.yml`'s `custom_features` (already
present pre-fix, hence why ES showed the menu) → `_geolith_options()` in
`libretroOptions.py`, dispatched via `_option_functions['geolith']` →
`generateCoreSettings()` → `createLibretroConfig()`
(`configgen/generators/libretro/libretroConfig.py:147`) → written into
`RETROARCH_CORE_CUSTOM`, which resolves to the exact
`cores/retroarch-core-options.cfg` path RetroArch's own `core_options_path`
setting points at. Checked the actual keys/defaults the built
`geolith_libretro.so` expects, straight from its
`libretro_core_options.h` (found under
`output/x86_64-arcade/build/libretro-geolith-*/libretro/`) — every key and
default in `_geolith_options()` matched exactly. So the code was right;
something about the build had to be wrong.

**Root cause: identical mechanism to the `batocera-es-system` bug above,
different package.** `batocera-configgen` doesn't fetch a tarball — it uses
`BATOCERA_CONFIGGEN_OVERRIDE_SRCDIR`
(`package/batocera/core/batocera-configgen/batocera-configgen.mk:22`) to
build straight from the local
`package/batocera/core/batocera-configgen/configgen/` directory via
`rsync`. That rsync step is implemented in Buildroot as a normal
stamp-gated target (`buildroot/package/pkg-generic.mk`, `.stamp_rsynced`) —
**it is not automatically re-run just because the source directory's
content changed.** Once a package has built successfully, a plain `make
<target>-build` leaves its stamps alone and skips it entirely, exactly like
the `batocera-es-system` case, just for a different trigger (there, it was
"newly enabled Kconfig option with no dependency edge"; here, it's "edited
Python source with no dependency edge"). Two independent rebuilds after the
fix commit both missed it, because neither was a *forced* rebuild of that
specific package.

Confirmed empirically by comparing timestamps in `output/x86_64-arcade/`:
`batocera-configgen-custom/.stamp_rsynced` and `.stamp_installed` were both
dated from the *very first* arcade build (01:05 that morning) — hours
*before* the fix commit (`d31a1ff6ba`, authored 10:05:14 the same day) even
existed. Running a plain `make x86_64-arcade-build` again afterward left
those stamps completely untouched. `grep geolith` on both the rsynced
build-dir copy and the installed target-rootfs copy of
`libretroOptions.py` matched nothing — the fix genuinely never got copied
in, on either attempt.

**A red herring along the way: `batocera.version` is not a reliable
freshness signal.** The natural instinct when a fix "isn't taking" is to
check the running system's reported version
(`/usr/share/batocera/batocera.version`, e.g. `44-dev-69379b2626
2026/07/14 02:06` — shown in ES's system info and in every launch log).
That string is written by a *completely different* package,
`batocera-system`'s own `BATOCERA_SYSTEM_INSTALL_TARGET_CMDS`
(`package/batocera/core/batocera-system/batocera-system.mk:104-111`),
which embeds `git rev-parse --short HEAD` — but only at the moment *that*
package's install step actually runs. `batocera-system` is itself just
another independently-stamped Buildroot package with no dependency edge
tying it to whatever else you changed, so its embedded commit hash can
legitimately lag behind (or, in principle, sit ahead of) the real content
of any other package, including `batocera-configgen`. In this incident the
version string happened to correctly point at a build that predated the
fix — but that was a coincidence of both packages being stamped at the same
initial build, not something to rely on in general. **Don't use
`batocera.version` to decide whether a specific source change made it into
an image.** Verify the actual file instead:
```
grep -n geolith output/x86_64-arcade/target/usr/lib/python3.14/site-packages/configgen/generators/libretro/libretroOptions.py
```
or, to be certain about what's actually flashable (the target dir and the
final packaged image can in principle diverge too), extract straight from
the built image:
```
unsquashfs -d /tmp/rootfs-check -f output/x86_64-arcade/images/rootfs.squashfs \
    usr/lib/python3.14/site-packages/configgen/generators/libretro/libretroOptions.py
grep -c geolith /tmp/rootfs-check/usr/lib/python3.14/site-packages/configgen/generators/libretro/libretroOptions.py
```

**Fix**: same targeted-rebuild pattern as the `batocera-es-system` incident,
just naming the other package:
```
make x86_64-arcade-build CMD="batocera-configgen-dirclean batocera-configgen" BATCH_MODE=1
make x86_64-arcade-build
```
Confirmed this actually resolved it by re-running both greps above against
the freshly built `rootfs.squashfs` — `_geolith_options`/`geolith_system_type`
present, 10 matches.

**The general lesson, extending the one from Bug A above**: *any* package
in this tree that builds from local source without going through a normal
tarball/git-commit fetch — `OVERRIDE_SRCDIR` packages like
`batocera-configgen`, or packages Buildroot considers "already built" for
any other reason — will not automatically pick up source edits on a plain
incremental `<target>-build`. If you've edited Python (or any other
locally-sourced package's code) and a behavior change doesn't show up after
rebuilding, don't assume the code is wrong before checking whether the
package was actually rebuilt: compare that package's `output/<target>/build/
<pkg>*/.stamp_rsynced` (or `.stamp_built`) timestamp against your edit's
commit time, and force it with `make <target>-build
CMD="<pkg>-dirclean <pkg>" BATCH_MODE=1` if it's stale. `<target>-refresh
PARALLEL_BUILD=y` (see "Triggering a build" below) is meant to automate
exactly this detection, but it works off `git log --since=<days>`, so it
only sees **committed** changes — commit first, then `-refresh`, if you want
to rely on it instead of naming the package by hand.

**Enabling it on an ARM board (e.g. Raspberry Pi 4 — `configs/batocera-bcm2711.board`)
needs a second change, not just the flag.** `libretro-geolith.mk` currently
has no RPi override:
```
LIBRETRO_GEOLITH_PLATFORM = $(LIBRETRO_PLATFORM)
```
On ARM, that shared `$(LIBRETRO_PLATFORM)` variable is a **composite,
space-joined string** (see the `ifeq`/`+=` chain in `retroarch.mk` around
lines 196–222) — e.g. on BCM2711/RPi4 it resolves to something like
`unix arm64 neon rpi4_64`, built for cores whose Makefiles parse it
token-by-token with `$(findstring ...)`. Geolith's own upstream
`libretro/Makefile` does **not** work that way — checked directly (fetched
and grepped it, not guessed): it does exact string-equality matching
(`ifeq ($(platform), rpi4)`) against a single literal token, recognizing
`rpi1`, `rpi2`, `rpi3`, `rpi3_64`, `rpi4` for Raspberry Pi. That's the same
convention `libretro-gambatte.mk` already uses, so the fix is to add the
same style of override block to `libretro-geolith.mk`:
```
ifeq ($(BR2_PACKAGE_BATOCERA_TARGET_BCM2835),y)
LIBRETRO_GEOLITH_PLATFORM = rpi1
else ifeq ($(BR2_PACKAGE_BATOCERA_TARGET_BCM2836),y)
LIBRETRO_GEOLITH_PLATFORM = rpi2
else ifeq ($(BR2_PACKAGE_BATOCERA_TARGET_BCM2837),y)
LIBRETRO_GEOLITH_PLATFORM = rpi3_64
else ifeq ($(BR2_PACKAGE_BATOCERA_TARGET_BCM2711),y)
LIBRETRO_GEOLITH_PLATFORM = rpi4
endif
```
**Important gotcha found during this check**: unlike `libretro-gambatte.mk`
(which also maps `BCM2712` → `rpi5`), Geolith's upstream Makefile has **no
`rpi5` branch at all** as of this check — Raspberry Pi 5 support isn't
there yet on Geolith's side. Don't copy gambatte's `rpi5` line reflexively;
re-check `libretro/Makefile` at
https://github.com/libretro/geolith-libretro for an `rpi5` case before
assuming BCM2712 works, and test it rather than trusting the mapping.

**The general lesson for porting any core to a new architecture**: don't
assume a core's build will "just work" because the package resolves in
Kconfig — `$(LIBRETRO_PLATFORM)`'s composite multi-token value only means
something to cores whose own Makefile is written to expect it that way.
Always check the *specific* core's upstream Makefile for how it actually
parses `platform=` (exact match vs. `findstring`) before assuming the
shared variable is enough, the same way this check turned up for Geolith.

## Adding a standalone (non-libretro) emulator — the gopher64 case study

`ADD-GOPHER64.md` (repo root) documents adding **gopher64**, a Rust/SDL3/
Vulkan Nintendo 64 emulator, as an extra selectable core for the existing
`n64` system (implemented 2026-07-17). Where the Geolith case study above
is about the *libretro* path, this one is the template for the *standalone*
path — a meaningfully different shape of work, worth understanding
generally for any future standalone emulator addition.

**1. A standalone emulator is a Buildroot package *plus* a Python
generator — libretro cores only ever needed the package.** Libretro core
options flow through RetroArch's own core-options mechanism (a
`custom_features:` block in the core's `.libretro.core.yml`, translated by
`libretroOptions.py` only when the mapping isn't 1:1). A standalone
emulator has no such shared layer — batocera itself has to build the
command line, write whatever config file format the emulator expects, and
set up environment variables, every single launch. That's
`package/batocera/core/batocera-configgen/configgen/configgen/generators/<name>/`,
new for every standalone emulator: a `<name>Generator.py` (command + env,
the only required file — must subclass `Generator` and implement
`generate()`/`getHotkeysContext()`), and as many small support modules as
needed (`<name>Paths.py` for path constants, `<name>Config.py` for
config-file writing). No entry in `generators/importer.py`'s
`_GENERATOR_MAP` is needed if the module/class names follow the default
convention — `get_generator()` derives `<name>.<name>Generator` /
`<Name>Generator` automatically (see `importer.py`'s fallback branch).

**2. The XDG env-var trick is how this repo redirects a well-behaved
Linux app's config/data into `/userdata` without patching the app.** Any
emulator using a standard directories library (Rust's `dirs` crate,
Qt's `QStandardPaths`, glib's `g_get_user_config_dir()`, etc.) honors
`XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`XDG_CACHE_HOME` if set. Rather than
patching the emulator to accept a custom config path (not always
possible, and an upstream-sync liability if it were), configgen's
generator just sets those three env vars before exec, pointed at
batocera's own `CONFIGS`/`SAVES`/`CACHE` roots
(`batocera_common.paths`). `ppssppGenerator.py`/`xemuGenerator.py` already
do this (`"XDG_CONFIG_HOME": CONFIGS, "XDG_DATA_HOME": SAVES`);
`gopher64Generator.py` follows the identical pattern. One subtlety: if the
library appends its own app-name subdirectory (gopher64's `dirs::config_dir()`
does — `.join("gopher64")`), point the env var at the *parent* of where
you want files to land, not the final directory itself, or you'll get a
doubled-up path.

**3. RetroAchievements for a standalone emulator is usually a token file,
not a login call.** batocera stores a RetroAchievements *token* (obtained
once via ES's own RA login screen), under global config keys
`retroachievements`, `retroachievements.username`, `retroachievements.token`,
`retroachievements.hardcore` (same keys regardless of which emulator reads
them). Several standalone emulators (PPSSPP, DuckStation, gopher64) each
expect that same information in their *own* on-disk format — PPSSPP wants
an INI section plus a separate `ppsspp_retroachievements.dat` token file;
gopher64 wants a single `retroachievements.json`
(`{"username", "token", "enabled", "hardcore", ...}`). The generator's job
is just translating batocera's global keys into whatever shape that one
emulator wants, written to disk *before* the emulator launches — not a
live username/password login on every boot (gopher64's CLI actually
exposes `--ra-username`/`--ra-password` flags that would do exactly that,
but they're deliberately unused here in favor of the token file, both to
avoid a network round-trip on every game boot and to stay consistent with
how every other emulator's RA integration in this repo already works).

**4. `configs/batocera-<target>_defconfig` is a generated file — edit the
`.board` file instead.** Hit directly while adding gopher64's opt-in line:
editing `configs/batocera-x86_64-arcade_defconfig` by hand appeared to
work, but the very next `make x86_64-arcade-defconfig` silently
regenerated it from `configs/batocera-x86_64-arcade.board` (via
`configs/createDefconfig.sh`, see the `$(TARGET_DEFCONFIG_PATTERN)` rule
in the top-level `Makefile`) and the hand-edit vanished with no warning.
The `_defconfig` files are gitignored
(`/configs/batocera-*_defconfig` in `.gitignore`) precisely because
they're build artifacts, not source — every persistent Kconfig line for a
custom target (the `BATOCERA_ARCADE_SYSTEMS`/`LIBRETRO_GEOLITH`/
`GOPHER64` opt-ins, the `BATOCERA_NINTENDO_SYSTEMS`-etc. umbrellas) lives
in the `.board` file. After editing the `.board` file, regenerate with
`make <target>-defconfig`, then actually load it into Buildroot's
`.config` with `make <target>-config BATCH_MODE=1` (the `-defconfig`
target only rewrites the text file; `-config` is the separate step that
runs it through Buildroot's Kconfig machinery) — `BATCH_MODE=1` matters
here too, since the plain Docker invocation opens an interactive `-it`
session and fails outright (`cannot attach stdin to a TTY-enabled
container`) when run from a non-interactive shell/script.

**5. Building a package in isolation surfaces toolchain-version mismatches
fast, cheaper than discovering them mid full-image build.** `make
<target>-pkg PKG=gopher64 BATCH_MODE=1` got all the way through git
submodule checkout and Cargo vendoring (hundreds of crates) before
failing cleanly with `rustc 1.95.0 is not supported ... requires rustc
1.97.0` — gopher64's newest tags had bumped their `Cargo.toml`
`rust-version` past what this buildroot's vendored toolchain provides
(`RUST_BIN_VERSION` in `buildroot/package/rust-bin/rust-bin.mk`). Rather
than bumping the shared Rust toolchain (high blast radius — every other
Rust package in the tree depends on it), the fix was pinning
`GOPHER64_VERSION` back to the newest upstream tag whose `rust-version`
still satisfied 1.95.0 (checked by fetching `Cargo.toml` from a handful of
historical tags directly from GitHub until finding the boundary — v1.1.20
was the last to require exactly `1.95.0`; v1.1.22 already required
`1.96.0`). General lesson: when packaging any fast-moving upstream
project, check its *minimum supported* toolchain/dependency version
against what this buildroot currently vendors, and pin to a compatible
tag rather than assuming "latest" will build — this applies just as much
to a future Rust/Go/Zig package as it did here.

**6. Mixing a clang-family `CC` into an otherwise-GCC cross toolchain has
sharp edges beyond "does it compile."** Once the rustc-version mismatch
was fixed, gopher64's own `build.rs` turned out to hardcode `-flto=thin`
(Clang ThinLTO) when compiling its vendored C/C++ submodules via the
`cc` crate — a flag GCC (buildroot's default target compiler here)
rejects outright. Pointing just that C/C++ compilation at buildroot's
cross-clang (`$(HOST_DIR)/bin/clang`, the same binary `duckstation.mk`
already uses) fixed the flag-rejection, but needed its own workaround
first: a **plain `clang --target=<rust-triple>` invocation can't find
`crtbeginS.o`/`-lgcc`** on this fork's *internal* (non-`BR2_TOOLCHAIN_EXTERNAL`)
toolchain, because the `--gcc-install-dir` auto-config-file mechanism
`package/llvm-project/clang/clang.mk` sets up only runs for external
toolchains. Fixed by reproducing that same `--gcc-install-dir`/`--target`/
`--sysroot` flag set by hand (`$(TARGET_CC) -print-search-dirs` gives the
install dir, same as the external-toolchain path computes it).

Even after that, the *archiver* choice mattered independently of the
compiler: the `cc` crate prefers `llvm-ar` for a clang-family `CC`, and
since `host-clang` doesn't install one, it silently used something that
produced an unindexed static archive (`archive has no index; run ranlib
to add one`). Explicitly pinning `AR`/`RANLIB` to buildroot's own cross
`ar`/`ranlib` looked like the fix but wasn't — the *actual* cause was
that `-flto=thin` produces LLVM-bitcode-only `.o` files, which **no**
GNU-binutils `ar` can index regardless of which one runs. The only real
fix was dropping `-flto=thin` (via a source patch, since it's hardcoded
with no env var/feature to disable it) — a reminder that an error message
naming a specific tool (`ar`) doesn't always mean that tool is the actual
problem; here it was a symptom of an upstream compiler-file-format
mismatch one layer up.

**7. `RUSTFLAGS` is global to the whole dependency graph — `cargo:rustc-link-arg`
from the owning crate's own `build.rs` is the scoped alternative.** The
last fix needed (extra `-lvulkan`/`--start-group`/`--end-group` linker
args parallel-rdp and volk's symbols needed) was first tried as a
`RUSTFLAGS` override in the package `.mk`. It "worked" for gopher64's own
binary but broke an unrelated dependency crate (`sevenz-rust2`, which
happens to build its own `cdylib` as part of the workspace) by handing
*it* link args pointing at libraries only gopher64's own `build.rs`
`OUT_DIR` has — `RUSTFLAGS` applies to every single `rustc` invocation
cargo makes for every crate in the graph, not just the final binary.
`cargo:rustc-link-arg=FLAG` printed from `build.rs` is the correctly
scoped mechanism (only affects the crate that owns that build script) —
worth remembering any time a fix looks like "just add a linker flag" for
a Cargo-based package with more than one crate in its dependency tree.

**8. Hand-assembling unified-diff hunks by counting context/added/removed
lines is genuinely error-prone — use `diff -u` against real files
instead.** Every patch needed for gopher64 (`git-describe` removal,
`-flto=thin` removal + the link-arg additions) went through at least one
round of `corrupt patch` / `Hunk #1 FAILED` from the *actual* `patch` tool
inside the build container, **despite** `git apply --check` succeeding
locally against byte-identical content each time. The root cause was
always a wrong line count in the hand-typed `@@ -N,old +N,new @@` header
(off by one from mis-counting how blank lines / removed-then-re-added
lines factor into the old/new totals) — `git apply` tolerated the wrong
count silently, the container's `patch` did not. The reliable fix, once
this pattern repeated a third time: write out full "before" and "after"
versions of the target region as plain strings/files and run `diff -u
before after` to generate the hunk mechanically, rather than
hand-computing header numbers at all. Worth doing this from the start for
any future patch, rather than after multiple failed round-trips.

## Debugging note (2026-07-15): RPCS3 link failure — `cannot find -lLLVMIntelJITEvents`

After enabling `BATOCERA_SONY_SYSTEMS` (which pulls in RPCS3), the build
failed at RPCS3's final link step:
```
/x86_64-arcade/host/bin/x86_64-buildroot-linux-gnu-ld: cannot find -lLLVMIntelJITEvents: No such file or directory
clang++: error: linker command failed with exit code 1
```

This looked at first like a missing dependency in batocera's own
packaging, but it wasn't — `package/batocera/emulators/rpcs3/Config.in`
already correctly does `select BR2_PACKAGE_LLVM_INTEL_JITEVENTS` right next
to `select BR2_PACKAGE_LLVM` (that Kconfig option was added specifically
for this, per the `# batcoera - add intel jit events option` comment
sitting on it in `buildroot/package/llvm-project/llvm/Config.in:42`), and
`output/x86_64-arcade/.config` confirmed it was correctly resolved to `y`.
So the Kconfig wiring was right — the actual built `llvm` package just
didn't match it.

**Root cause: the same stale-Buildroot-stamp problem as the
`batocera-es-system`/`batocera-configgen` incidents above, but a new
variant.** Those were about a package's output depending on some *other*
package's Kconfig state or on an unrelated data file changing. This one is
narrower and easy to miss: **a package's *own* Kconfig-driven CMake
configure flags changed, after that same package had already built
successfully once.** `llvm` had been built early on, before `SONY_SYSTEMS`
(and therefore `LLVM_INTEL_JITEVENTS`) was ever turned on, so its one-time
CMake configure ran with `-DLLVM_USE_INTEL_JITEVENTS=OFF`. Once the Kconfig
option flipped on later, Buildroot had no reason to know `llvm`'s own build
was now out of date with its current `.config` — incremental builds only
re-run a package's configure/build steps in response to source/patch
changes or an explicit forced rebuild, not "this package's resolved
`_CONF_OPTS` changed since it was last built."

**How this was confirmed**, rather than guessed: `llvm`'s actual CMake
cache on disk was checked directly against the current `.config`:
```
grep LLVM_USE_INTEL_JITEVENTS output/x86_64-arcade/build/llvm-22.1.5/llvm/buildroot-build/CMakeCache.txt
```
showed `LLVM_USE_INTEL_JITEVENTS:BOOL=OFF`, while `.config` had
`BR2_PACKAGE_LLVM_INTEL_JITEVENTS=y` — a direct mismatch. The `llvm`
package's stamps (`.stamp_configured`/`.stamp_built`/`.stamp_installed`)
were all dated from the very first arcade-only build, well before
`SONY_SYSTEMS` was ever turned on, confirming it. `libLLVMPerfJITEvents.a`
(a different, always-on LLVM component) existed in staging, but
`libLLVMIntelJITEvents.a` was nowhere in the build output — consistent with
a `llvm` build that predates the flag turning on. This same technique — diff
a package's own on-disk build-system cache file against the current
`.config`, rather than assuming the Kconfig `select` graph alone explains
the failure — is the general way to confirm this specific variant.

**Fix**: force a targeted rebuild of just `llvm` (RPCS3 itself didn't need
a forced rebuild — it failed at the link step, so it never got a
completion stamp, and retried automatically on the next build once its
dependency was fixed):
```
make x86_64-arcade-build CMD="llvm-dirclean llvm" BATCH_MODE=1
make x86_64-arcade-build BATCH_MODE=1
```
Confirmed the fix by checking the rebuilt `CMakeCache.txt` showed
`LLVM_USE_INTEL_JITEVENTS:BOOL=ON`, `libLLVMIntelJITEvents.a` now existed
under the host sysroot's `usr/lib`, and RPCS3's own `.stamp_built` appeared
with a fresh timestamp along with a real `usr/bin/rpcs3` binary landing in
the target rootfs.

**The general lesson, extending the `batocera-es-system`/`batocera-configgen`
ones above**: it's not just *other* packages' Kconfig state or unrelated
data files that can go stale without a forced rebuild — a package's *own*
build-system configure flags can too, whenever those flags are themselves
driven by a Kconfig option that gets turned on *after* the package already
built successfully once. Newly enabling a whole category/manufacturer
umbrella (which can flip on options for packages that were already built
for an unrelated reason, e.g. `llvm` here was already needed by Mesa) is
exactly the kind of change likely to trigger this. If a package that
already builds without error still fails a *dependent* package's link step
in a surprising way, check whether that package's own resolved Kconfig
options actually match what it was last built with — its build-system's
own cache file (`CMakeCache.txt` for CMake, or the equivalent for other
build systems) is the direct way to check, rather than trusting the
Kconfig `select` graph alone.

## Triggering a build

The actual command that produces a bootable image:

```
make x86_64-arcade-build
```

What happens: it re-runs `-defconfig`/`-config` first (so it always picks
up any board-file edits automatically — you don't strictly need to run
those separately, they're just useful for the quick sanity-check above),
then invokes Buildroot inside the project's Docker container to compile
and package everything. This is the slow part — first run compiles the
toolchain, kernel, mesa, every enabled emulator, etc. from scratch.

Useful variations:
- `make x86_64-arcade-build BATCH_MODE=1` — non-interactive (no TTY
  attached to the container); needed if you're not running it from an
  interactive terminal.
- `make x86_64-arcade-build PARALLEL_BUILD=y` — turns on multi-package
  parallelism. See "Parallelism" below — without this flag, a build is
  much less parallel than you'd expect on a many-core machine.
- `make x86_64-arcade-clean` / `x86_64-arcade-cleanbuild` — wipe this
  target's build output and start over (rarely needed; Buildroot/ccache
  handle incremental changes on their own).
- `make x86_64-arcade-pkg PKG=<name>` — build (or rebuild) just one
  package by name, without touching the rest. Good for testing a change to
  a single emulator package quickly.

### Parallelism: are you actually using all your cores?

Not by default — this tripped us up on the very first real build, worth
understanding precisely. There are two independent layers of parallelism,
and plain `make x86_64-arcade-build` only gets you one of them:

- **Within one package's own compile step**, Buildroot already uses
  multiple cores regardless of any flags — `BR2_JLEVEL=0` is the default
  (confirmed in the generated `.config`), which Buildroot's own Kconfig
  help text defines as "determine automatically according to number of
  CPUs on the host system." So while a big package like Mesa or the kernel
  is compiling, you'll see close to full CPU usage.
- **Across packages, it's serial by default** — one package fully
  downloads/configures/builds/installs before the next one even starts.
  You can see this directly in the build log
  (`output/x86_64-arcade/build/build-time.log`): entries for one package
  never interleave with the next. For a build like this one with ~955
  mostly-small packages (lots of quick libretro cores and small libs, not
  just a few giant ones), that serial-across-packages behavior leaves a
  lot of idle core time — a small package with only a couple of source
  files can't use 16 cores no matter what `BR2_JLEVEL` says, and the next
  package has to wait its turn regardless.

**`PARALLEL_BUILD=y`** is what turns on the second layer: it sets
`BR2_PER_PACKAGE_DIRECTORIES=y` (lets Buildroot build multiple *different*
packages concurrently, each in its own isolated directory) and adds a
top-level `-j$(MAKE_JLEVEL)` (default `nproc`) to the actual `make`
invocation, which is required for that concurrency to actually kick in.
Use it as:
```
make x86_64-arcade-build PARALLEL_BUILD=y
```

**Important caveat if a build is already running without it**:
`BR2_PER_PACKAGE_DIRECTORIES` changes Buildroot's internal build-directory
layout. You can't toggle it on mid-build and just re-run `-build` — it
needs a clean rebuild (`x86_64-arcade-cleanbuild PARALLEL_BUILD=y` or
`-clean` then `-build`) to take effect, which throws away the in-progress
build graph (though ccache still speeds up recompiling anything it's
already seen, so it's not a full time cost, just not free either). For an
already-running first build, it's usually better to just let it finish and
use `PARALLEL_BUILD=y` on the next one (adding PS1/PS2, adding Geolith,
etc.) rather than restart.

**Watching progress:** every build writes a running log to
`output/x86_64-arcade/build/build-time.log` (one line per package as it
starts/finishes). Tail it live with:

```
make x86_64-arcade-tail
```

(equivalent to `tail -F output/x86_64-arcade/build/build-time.log`) — safe
to run from a second terminal while a build is in progress, it's read-only.

**When it's done:** finished images land under
`output/x86_64-arcade/images/batocera/images/x86_64-arcade/` (a `.img.gz`
plus boot files). If that directory doesn't exist yet, the build hasn't
completed.

## The Docker build image can go stale — force a rebuild when it does

None of the compiling happens on your host machine. `make x86_64-arcade-build`
runs everything (gcc, cmake, the whole toolchain) inside a locally cached
Docker image, `batoceralinux/batocera.linux-build:latest`, built from
`docker/Dockerfile`. Docker does **not** auto-refresh that local cache just
because you `git pull`ed changes to `docker/Dockerfile` — you keep using
whatever image you built/pulled last until you explicitly tell Docker to
redo it.

**How this bit us (2026-07-13):** a build failed on `host-protobuf-34.1`
with a wall of hundreds of C++ parse errors that looked exactly like a
genuine upstream protobuf/abseil source bug. The real cause was a stale
local image — built 2026-04-04 — that predated a `docker/Dockerfile`
commit from 2026-05-15 bumping the base image to `ubuntu:26.04`. The stale
image was still on Ubuntu 22.04's GCC 11.4.0, which has a real compiler
bug: `__has_cpp_attribute` wrongly reports support for the made-up
`gnu::warn_unused` attribute that abseil emits, GCC then fails to parse
its own false-positive, and that one parse failure cascades into hundreds
of unrelated-looking downstream errors. Newer GCC (15.2.0, what
`ubuntu:26.04` actually ships) doesn't have this bug. No source code was
at fault — rebuilding the Docker image fixed it outright.

**Check whether your image is stale:**
```
git log -1 --format=%ai -- docker/Dockerfile
docker inspect batoceralinux/batocera.linux-build:latest --format '{{.Created}}'
```
If the image's `Created` timestamp is older than the Dockerfile's last
commit date, it's stale — rebuild before spending time chasing a "build
failure" that's really just an outdated toolchain.

**Force a rebuild:**
```
make rebuild-docker-image
```
This clears the "image available" stamp and rebuilds locally from the
current `docker/Dockerfile`. It's a multi-arch build (amd64 + arm64 via
`docker buildx`), so it can take several minutes even though only the
amd64 result actually gets loaded for local use — the arm64 leg runs under
emulation on an x86 host and can't be skipped through this target. There's
also `make update-docker-image`, which re-*pulls* the published image from
the registry instead of building locally — only useful if someone has run
`make publish-docker-image` more recently than your last local build,
since publishing here is a manual step, not automatic per-commit.

**The opposite symptom — image updated, output stale (2026-07-13):** the
protobuf case above is "your image is too old." There's also the mirror-image
problem: the image gets updated (e.g. a newer Ubuntu base bumps system Perl
from 5.34 to 5.42), but `output/<target>/` is a persistent volume that
survives image rebuilds, so any already-built host package artifact tied to
the *old* image's tool versions just sits there stale. Buildroot has no way
to detect "the container's system Perl changed" — it only rebuilds a package
when its own sources/config change.

We hit this with `pcmanfm`'s build failing on
`configure: error: XML::Parser perl module is required for intltool`, even
though `host-libxml-parser-perl` (which provides `XML::Parser`) was already
built. Two things looked related but only one actually mattered:
1. `pcmanfm.mk` (in the vendored `batocera-linux/buildroot` fork, not
   anything our arcade board touches) was missing `host-intltool` from
   `PCMANFM_DEPENDENCIES` — added it, matching the pattern libfm-extra's
   `.mk` already uses. Turned out to be **cosmetic, not causal**: checking
   `build-time.log` showed `libfm-extra` (a real transitive dependency of
   pcmanfm via `menu-cache → libfm-extra`, which *does* correctly declare
   `host-intltool`) had already fully finished building before pcmanfm's
   first configure attempt even started. So `host-intltool` was always going
   to be present by the time pcmanfm ran — on the stock batocera build too,
   not just this arcade one. Worth having fixed anyway (self-documenting,
   matches convention, protects against libfm-extra's own dependency list
   ever changing), but it isn't what caused this failure and isn't specific
   to the trimmed-down build.
2. The *same* error persisted even after that fix — the real cause was the
   compiled `XML::Parser` XS module (`Expat.c`), which is deliberately built
   against the container's system Perl, not Buildroot's own toolchain (see
   the comment in `buildroot/package/Makefile.in` above `PERL5LIB=`). It had
   been compiled against an older Perl ABI and silently broke when the image
   was updated. This part also isn't arcade-specific — it's purely a
   function of container/output-directory history and could hit a stock
   full build identically given the same sequence of events.

This is narrow — a repo-wide search
(`grep -rl "INSTALLSITEARCH\|ExtUtils::MakeMaker\|Makefile.PL" buildroot/package/*/*.mk`)
found `libxml-parser-perl` is the *only* package in the whole tree that
compiles bindings against the container's system tools; everything else
builds against Buildroot's own cross toolchain and is unaffected by image
updates. So there's no need for a broad "clean all host packages" sweep —
if you hit a similarly bizarre error right after a Docker image update
(especially anything mentioning Perl/XS/ABI version mismatches), the fix is
a targeted rebuild of just that one package:

```
make x86_64-arcade-build CMD="<pkg>-dirclean <pkg>"
```

For this specific incident that was
`CMD="host-libxml-parser-perl-dirclean host-libxml-parser-perl"`, followed by
a normal `make x86_64-arcade-build` to pick it up.

**Pitfall to watch for after a diagnostic rebuild:** if you manually clear
out a package's build directory outside of Buildroot's own `-dirclean`
target (e.g. reaching in with `rm -rf`), make sure you actually remove
dotfiles too (`rm -rf dir/*` silently skips them) — a leftover
`.stamp_configured` with the real build tree gone underneath it produces a
confusing "not a CMake build directory" error on the next build. Also, one
run in this session somehow left files under `output/x86_64-arcade/`
owned by `root` instead of your user, which then made a later
`-dirclean` fail with `Permission denied`. Fastest fix without `sudo`,
using Docker itself to get root:
```
docker run --rm -v "$(pwd)/output:/output" alpine chown -R "$(id -u):$(id -g)" /output
```

## The local `Config.in` patches — one-time, or every build?

**One-time**, with caveats. This is worth understanding precisely because
it's easy to assume (wrongly) that they need to be reapplied before every
single build, like a `docker run` flag would. There are two of these
patches now, both in `board/batocera/x86/local-patches/`, both following
the same lifecycle described below:

- `no-nvidia.patch` — comments out the forced Nvidia `select` in
  `package/batocera/core/batocera-system/Config.in`.
- `manufacturer-systems.patch` — adds the one `source` line to the
  top-level `./Config.in` that hooks in
  `package/batocera/custom-arcade/manufacturer-systems/Config.in` (the
  seven manufacturer-scoped system umbrellas — see Option 3 above). Unlike
  the Nvidia patch, this one is purely additive (a new line, not a
  comment-out of existing content) and targets a different file (the
  top-level `Config.in`, not `batocera-system/Config.in`) — but the
  reasoning and lifecycle are identical: keep the shared file's committed
  state byte-for-byte upstream-clean, and treat the one line that actually
  enables the fork-only feature as a locally-applied patch instead of a
  permanent diff.

  Note this only applies to that one hookup line. The file it points at,
  `package/batocera/custom-arcade/manufacturer-systems/Config.in` itself,
  is *not* patch-based — it's a normal new file, safe to `git add`/commit
  outright, since it's not a path upstream batocera has ever touched or
  ever will. Only edits to a *shared* file need the patch treatment; wholly
  new fork-owned files don't.

`package/batocera/core/batocera-system/Config.in` and `./Config.in` are
normal source files that live directly in this git checkout — they aren't
tarballs that get freshly re-extracted and re-patched on every build the
way, say, the Linux kernel source is (via `BR2_GLOBAL_PATCH_DIR`). So once
you run:

```
git apply board/batocera/x86/local-patches/no-nvidia.patch
git apply board/batocera/x86/local-patches/manufacturer-systems.patch
```

...both changes just sit in your working tree as ordinary uncommitted
changes (`git status` will show both `Config.in` files as modified). Every
subsequent `make x86_64-arcade-*` command reads whatever is currently on
disk, patched or not — there's no per-build re-patching step to remember.

**You only need to reapply either one if the working tree loses that
change**, which happens when:
- You run something that resets tracked files — `git checkout --
  package/batocera/core/batocera-system/Config.in` (or `-- Config.in`),
  `git reset --hard`, `git stash` (without popping it back), etc.
- You pull/rebase/merge from upstream batocera and that file gets
  overwritten or a patch no longer applies cleanly (a conflict) — you'd
  need to reconcile it, possibly regenerating the patch if upstream has
  changed that section of the file.
- You start from a fresh clone of the repo.
- You (or a future Claude Code session) commit the `Config.in` change
  directly instead of leaving it as an uncommitted local patch — at that
  point it's permanent and there's nothing left to "apply", but see the
  trade-off noted in `AGENTS.md` about why we chose *not* to do that.

**How to check the current state without guessing:**

```
git status --porcelain package/batocera/core/batocera-system/Config.in Config.in
```

Empty output for a given file = that patch is **not** currently applied
(Nvidia will be built in / the manufacturer options won't exist in the
Kconfig tree if you build now). `M ...` output = it **is** currently
applied. You can also just `grep` the relevant line directly:

```
grep "select BR2_PACKAGE_BATOCERA_NVIDIA" package/batocera/core/batocera-system/Config.in
grep "custom-arcade/manufacturer-systems/Config.in" Config.in
```

For Nvidia: if the line is commented out (starts with `#`), the patch is
applied. For the manufacturer-systems patch: if the `grep` finds the
`source` line, it's applied. Note `git apply` itself refuses to
double-apply — running it again when it's already applied just errors out
safely, it won't corrupt the file.
