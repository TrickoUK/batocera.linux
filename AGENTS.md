# AGENTS.md

Notes for working in this batocera.linux checkout, specifically for this
fork's goal: a fast-iterating, stripped-down **x86_64, AMD-only** build,
starting with **arcade** systems and growing to **PS1 + PS2**, as a base for
later experimenting with adding new systems/ports to batocera.

There is also a `USER-INSTRUCTIONS.md` at the repo root — detailed,
educational notes for the human to learn from (vs. this file's terse
technical reference for CLI sessions). **Whenever you work out something
useful for the user to know or learn from, add it to
`USER-INSTRUCTIONS.md`** in addition to keeping this file current.

There is also a `PROJECT-OVERVIEW.md` at the repo root — a generic,
fork-agnostic knowledge base about batocera.linux/Buildroot mechanics
(directory layout, the config/build pipeline, systems-selection Kconfig
hierarchy, build gotchas), written in neutral wiki-article voice with
nothing fork-specific in it, intended as a useful contribution toward the
project's actual wiki. **When something learned is generic Buildroot/batocera
mechanics that would apply to any checkout or build target — not a
decision or incident specific to this fork — add it to
`PROJECT-OVERVIEW.md` instead of (or in addition to, generalized)
`USER-INSTRUCTIONS.md`.**

## What batocera.linux is

A Buildroot-based Linux distro that boots into EmulationStation (ES-DE
fork) with RetroArch and a large set of standalone emulators. Runs from
USB/SD; doesn't touch the host.

## Directory map

- `buildroot/` — vendored Buildroot itself. Don't edit directly.
- `board/` — per-platform patches, kernel configs, filesystem overlays,
  boot scripts. `board/batocera/x86/` is the x86-specific tree (kernel
  defconfig, patches, fsoverlay, boot scripts like `S05nvidia`).
- `configs/` — `*.board` files, one per build target. `TARGETS` in the
  top-level `Makefile` is auto-derived from `configs/*.board`, so **adding
  a new `.board` file creates a new independent `make <name>-*` target**.
  `configs/createDefconfig.sh` resolves `include`/`-include` directives in
  a board file and concatenates: recursively-included files first, then the
  board file's own lines, then anything from `batocera.mk`
  (`add-defconfig`) last. Later lines win for the same `BR2_*` symbol
  (unless something else forces it via Kconfig `select` — see the Nvidia
  note below).
- `package/batocera/` — the actual Batocera-specific packages (Buildroot
  package + Config.in pairs). Key subdirs:
  - `core/batocera-system/Config.in` — the central Kconfig hub. Defines
    `BR2_PACKAGE_BATOCERA_SYSTEM` (always on), all the systems-selection
    umbrellas, and GPU/driver selection (`BATOCERA_GPU_X86`,
    `BATOCERA_VULKAN`). ~2400 lines; see below for the parts that matter
    here.
  - `emulators/` — standalone (non-libretro) emulators, one dir each:
    `duckstation/`, `pcsx2/`, `mame/`, `rpcs3/`, `dolphin-emu/`, etc.
  - `emulators/retroarch/libretro/` — libretro cores as separate packages:
    `libretro-fbneo/`, `libretro-mame/`, `libretro-mame2003-plus/`,
    `libretro-beetle-psx/`, etc.
  - `emulationstation/batocera-es-system/es_systems.yml` — the master list
    of every possible system + every possible emulator/core for it,
    tagged with the `BR2_PACKAGE_*` option that gates each one.
- `python-src/` — Python sources (uv-based), including the ES system
  metadata tooling (`batocera-es-system`).
- `docker/` — the official build container (`Dockerfile`, Ubuntu 26.04) and
  `docker.mk`.

## Build mechanics

Flow for `make <target>-build`: `configs/batocera-<target>.board` →
`configs/createDefconfig.sh` generates `configs/batocera-<target>_defconfig`
→ Buildroot's own `defconfig` target resolves it into
`output/<target>/.config` → Buildroot builds the image.

Useful per-target make targets (`<target>` = e.g. `x86_64-arcade`):
- `<target>-defconfig` / `<target>-config` — generate the defconfig / run
  Buildroot's config resolution only (fast, no build). Good for validating
  a systems/driver trim before committing to a real build.
- `<target>-build` — full build. `CMD=` forwards straight to Buildroot, so
  `make <target>-build CMD=menuconfig` (or `nconfig`/`xconfig`) opens the
  interactive Kconfig menu with every resolved `BR2_PACKAGE_*` option.
- `<target>-kernel` — `linux-menuconfig` shortcut.
- `<target>-pkg PKG=<name>` — build a single package in isolation
  (`CMD=<name>`) — useful to sanity-check the Docker/toolchain pipeline or
  time one package before a multi-hour full build.
- `<target>-show-build-order`, `<target>-graph-depends` — see the resolved
  package list/dependency graph without building.
- `<target>-clean`, `<target>-cleanbuild` — wipe output for a target.
- `<target>-shell` — shell inside the build environment (`CMD=` required if
  `BATCH_MODE=1`).
- `<target>-ccache-stats` — ccache hit-rate report.
- `<target>-systems-report[-clean|-serve]` — generates/serves a report of
  what would land in the image for a target.

Docker vs direct: builds go through Docker by default (`docker/docker.mk`,
image pulled/built via `pull-docker-image`/`build-docker-image`). Set
`DIRECT_BUILD=1` to build straight on the host instead (bypasses Docker
entirely; host must match `docker/Dockerfile`'s package list). **This fork
builds via Docker** (not direct-build) per current preference.

The locally cached `batoceralinux/batocera.linux-build:latest` image does
**not** auto-refresh when `docker/Dockerfile` changes upstream — compare
`docker inspect batoceralinux/batocera.linux-build:latest --format '{{.Created}}'`
against `git log -1 --format=%ai -- docker/Dockerfile`; if the image
predates the Dockerfile, `make rebuild-docker-image` before trusting any
compiler-looking error (see `USER-INSTRUCTIONS.md` for a real incident: a
stale image's GCC 11 produced a wall of cascading protobuf/abseil parse
errors that a rebuild fixed outright, no source change needed).

Mirror-image failure: image *updated* but `output/<target>/` (persistent
volume) keeps stale host-package artifacts built against the old image's
tools. Hit this via `pcmanfm` failing on missing `XML::Parser` — root cause
was a stale `host-libxml-parser-perl` XS module compiled against an old
container Perl ABI (not arcade-specific; can hit a stock build identically).
Also added `host-intltool` to `PCMANFM_DEPENDENCIES` (was missing, matches
libfm-extra's pattern), but confirmed via `build-time.log` that's cosmetic —
`libfm-extra` (a real transitive dep via `menu-cache`) already pulls in
`host-intltool` first regardless.
`grep -rl "INSTALLSITEARCH\|ExtUtils::MakeMaker\|Makefile.PL" buildroot/package/*/*.mk`
confirms `libxml-parser-perl` is the *only* package in the tree that compiles
against the container's system Perl, so no broad host-clean is needed; fix is
`make <target>-build CMD="<pkg>-dirclean <pkg>"` targeted at whichever
package errors. Full incident in `USER-INSTRUCTIONS.md`.

Same class of problem, different trigger, hit again on `batocera-configgen`
(2026-07-14, full trace in `USER-INSTRUCTIONS.md`): it builds via
`BATOCERA_CONFIGGEN_OVERRIDE_SRCDIR` (plain rsync from
`package/batocera/core/batocera-configgen/configgen`), and that rsync step
is just another stamp-gated Buildroot target
(`buildroot/package/pkg-generic.mk`, `.stamp_rsynced`) — editing the Python
source there does **not** invalidate it. A configgen fix (new `_geolith_options()`
function) silently missed two consecutive rebuilds because of this;
confirmed by comparing `.stamp_rsynced`'s timestamp against the fix
commit's timestamp, and finally by `unsquashfs`-ing the actual
`output/<target>/images/rootfs.squashfs` and grepping the installed `.py`
directly. Same fix: `make <target>-build CMD="batocera-configgen-dirclean
batocera-configgen" BATCH_MODE=1`, then a normal `-build`. **Any**
`OVERRIDE_SRCDIR`-built package in this tree has this same gotcha, not just
these two — if a source edit doesn't seem to take effect, check that
package's stamp timestamps before assuming the code is wrong.

Don't trust `/usr/share/batocera/batocera.version` as a build-freshness
signal for a specific change. It's written by `batocera-system`'s own
install step (`batocera-system.mk:104-111`, embeds `git rev-parse --short
HEAD` at the time *that* package last (re)installed) — itself just another
independently-stamped package with no dependency edge onto whatever you
actually changed, so it can lag behind (or race ahead of) the real content
of any other package. To verify a specific fix actually landed, grep the
installed file under `output/<target>/target/...` directly, or better,
extract it straight from `output/<target>/images/rootfs.squashfs`
(`unsquashfs -d <dir> -f rootfs.squashfs <path-inside-image>`) — that's the
only artifact that's actually flashed.

Speed levers: `PARALLEL_BUILD=y` (+ `MAKE_JLEVEL`/`MAKE_LLEVEL`, default
`nproc`) adds `BR2_PER_PACKAGE_DIRECTORIES` and `-j`; ccache is **on by
default** for every board (`BR2_CCACHE=y` in `configs/batocera-board.common`)
and persists in `buildroot-ccache/`; `<target>-refresh` does a surgical
incremental rebuild of recently-changed packages (`DAYS=<n>`, requires
`PARALLEL_BUILD=y`). Local overrides go in a `batocera.mk` (copy from
`batocera.mk.template`) using `$(call add-defconfig,BR2_FOO=y)`.

## Systems selection hierarchy

Every board sets `BR2_PACKAGE_BATOCERA_ALL_SYSTEMS=y` by default (via
`configs/batocera-board.common`). That one option `select`s category
umbrellas — `BATOCERA_ARCADE_SYSTEMS`, `BATOCERA_CONSOLE_SYSTEMS`,
`BATOCERA_HANDHELD_SYSTEMS`, `BATOCERA_COMPUTER_SYSTEMS`,
`BATOCERA_MSDOS_SYSTEMS`, `BATOCERA_SCUMMVM_SYSTEMS`,
`BATOCERA_HOMEBREW_SYSTEMS`, `BATOCERA_WINE_SYSTEMS`,
`BATOCERA_GAMESTREAM_SYSTEMS`, `BATOCERA_PORTS_SYSTEMS`,
`BATOCERA_FLASH_SYSTEMS` — each of which `select`s individual emulator
`BR2_PACKAGE_*` options. All defined in
`package/batocera/core/batocera-system/Config.in` (arcade block ~line 967,
console/PSX block ~line 1416). `BR2_PACKAGE_BATOCERA_RETROARCH` is selected
directly by `ALL_SYSTEMS`, **not** by the category umbrellas — a trimmed
config that skips `ALL_SYSTEMS` must select it explicitly.

**Manufacturer-scoped umbrellas (added 2026-07-15, enabled in the arcade
board as of 2026-07-15):** seven parallel options —
`BATOCERA_NINTENDO_SYSTEMS`, `BATOCERA_SEGA_SYSTEMS`, `BATOCERA_SONY_SYSTEMS`,
`BATOCERA_COMMODORE_SYSTEMS`, `BATOCERA_AMSTRAD_SYSTEMS`,
`BATOCERA_NEC_SYSTEMS`, `BATOCERA_ATARI_SYSTEMS` — `select` the same
underlying packages as the category umbrellas above, just regrouped by
manufacturer instead of by category (e.g. `NINTENDO_SYSTEMS` pulls in
NES/SNES/N64/GameCube-Wii/WiiU *and* GB/GBA/DS/3DS in one option, spanning
what would otherwise be split across `CONSOLE_SYSTEMS` and
`HANDHELD_SYSTEMS`). Each `select` line was copied verbatim including its
original condition, so these stay valid for any board, not just x86_64.

All 7 are now `=y` in `configs/batocera-x86_64-arcade.board`, replacing what
used to be the hand-picked "Phase 2a: PS1" lines there (now redundant —
`SONY_SYSTEMS` covers PS1 plus PS2/PS3/PSP/Vita). Not selected:
`BR2_PACKAGE_BATOCERA_CORES_STILL_COMMERCIALIZED`, deliberately left off —
without it, `NINTENDO_SYSTEMS`' `select BR2_PACKAGE_CITRON`/`RYUJINX`
conditions never fire, so Switch emulation stays off while everything else
under `NINTENDO_SYSTEMS` is unaffected. **Still not selected by
`ALL_SYSTEMS`** — only this board's defconfig opts into them.

**Deliberately not in `package/batocera/core/batocera-system/Config.in`.**
That file is shared/upstream-touched constantly, so these live instead in a
fork-only file, `package/batocera/custom-arcade/manufacturer-systems/Config.in`
(a normal file, safe to commit — upstream has no path collision with it).
Kconfig still requires *something* to `source` that file for its symbols to
exist in the tree, so one line is needed in the shared top-level
`./Config.in`; that line is kept as an uncommitted local patch,
`board/batocera/x86/local-patches/manufacturer-systems.patch`, applied the
same way and same lifecycle as `no-nvidia.patch` (see
"The local `Config.in` patches" in `USER-INSTRUCTIONS.md`). Without the
patch applied, `Config.in` is byte-for-byte upstream-clean and the seven
options don't exist in the Kconfig tree.

Full package-by-package breakdown and the deliberate scope exclusions (Sony
handhelds included; Atari/NEC deliberately narrower than "everything that
manufacturer made"; a mislabeled Sinclair core and the non-official
Commander X16 left out of Amstrad/Commodore) are in `USER-INSTRUCTIONS.md`.

The EmulationStation UI system list (`es_systems.cfg`) is **generated at
build time**, not hand-maintained: each emulator package's `.mk` registers
its metadata (`.core.yml`/`.emulator.yml`) only if its Kconfig option is
`y` (via `package/batocera/pkg-emulator-info.mk`), and
`batocera-es-system.mk` runs a Python tool
(`python-src/batocera-es-system`) that cross-references those against the
static `es_systems.yml` and writes `es_systems.cfg` — **a system with zero
enabled emulators is silently omitted from the UI**. So trimming what shows
up in ES = trimming which `BR2_PACKAGE_*` emulator options are enabled;
there's no separate ES-side list to edit.

**Two non-obvious things about this pipeline, hit while adding Geolith
(2026-07-14, full trace in `USER-INSTRUCTIONS.md`):**

1. **`batocera-es-system`'s Buildroot stamps have no dependency edge onto
   other packages' Kconfig state or onto `es_systems.yml`'s content.**
   Editing `es_systems.yml`, or newly enabling an emulator/core package,
   does **not** invalidate `batocera-es-system`'s existing
   `.stamp_built`/`.stamp_target_installed` — an incremental rebuild will
   silently ship a stale `es_systems.cfg` even though the new package
   itself builds and installs correctly. Confirmed by timestamp diff: a
   freshly-built core's stamps were minutes old while
   `batocera-es-system`'s stamps (and the shipped `es_systems.cfg`) were
   hours stale, still from before the edit. **Force it after any such
   change**: `make <target>-build CMD="batocera-es-system-dirclean
   batocera-es-system" BATCH_MODE=1`, then a normal `-build`. Verify
   against the generated file, not the source YAML:
   `grep -A20 '<name>SYSTEM</name>'
   output/<target>/target/usr/share/emulationstation/es_systems.cfg`.
2. **`es_systems.yml`'s per-system `emulators:` block (`requireAnyOf:`,
   `incompatible_extensions:`) is dead code** — parsed for schema shape
   only, never read by `python-src/batocera-es-system/batocera_es_system/es_systems.py`.
   The real per-system emulator/core list, and per-core extension
   exclusivity, comes entirely from a `Registry` built from each package's
   *own* `*.emulator.yml`/`*.libretro.core.yml` `systems:` declarations
   (`registry.py`). Concretely: to make one core exclude a file extension
   another core for the same system handles, add `exclude_extensions:
   [...]` under that core's own `systems: - name: <system>` entry in its
   own yml file — *not* an `incompatible_extensions:` field in
   `es_systems.yml`. (`clk.emulator.yml` is the pre-existing reference
   example of this idiom.) Don't trust a field that merely *looks* like
   the right lever by name/precedent without grepping
   `es_systems.py`/`registry.py` for where it's actually consumed.

## GPU driver notes

`BATOCERA_GPU_X86` (in the same Config.in, always selected for any x86
target — independent of systems selection) bundles AMD (`RADEONSI`
Gallium, `AMD`/RADV Vulkan) and Intel mesa drivers unconditionally, with no
per-vendor toggle. **Nvidia is force-selected on the same block** via:

```
select BR2_PACKAGE_BATOCERA_NVIDIA if BR2_PACKAGE_BATOCERA_TARGET_X86_64_ANY
```

Because this is a Kconfig `select` (forced/reverse dependency), setting
`BR2_PACKAGE_BATOCERA_NVIDIA=n` in a defconfig gets silently re-forced to
`y` — it cannot be disabled from a board file or `batocera.mk`. The only
way to exclude it is to break the `select` line itself.

**This fork's fix**: `board/batocera/x86/local-patches/no-nvidia.patch`
comments out that one line in
`package/batocera/core/batocera-system/Config.in`. It's kept as a
standalone patch (not a direct edit to that shared file) so it stays easy
to see/drop/regenerate independently if this checkout ever syncs from
upstream batocera. Apply it before generating a defconfig:

```
git apply board/batocera/x86/local-patches/no-nvidia.patch
```

(and revert with `git apply -R ...` if you ever need Nvidia back, or need a
clean tree to pull upstream changes).

## This fork's customization

- `configs/batocera-x86_64-arcade.board` — new build target (`make
  x86_64-arcade-*`), independent of the stock `x86_64` target. Same
  boot/kernel/EFI setup as `batocera-x86_64.board`, but overrides
  `BR2_PACKAGE_BATOCERA_ALL_SYSTEMS=n` and explicitly selects only
  `BR2_PACKAGE_BATOCERA_RETROARCH` + `BR2_PACKAGE_BATOCERA_ARCADE_SYSTEMS`
  for phase 1. `BR2_PACKAGE_BATOCERA_KODI21=y` (copied over from the stock
  board file) was removed — it's a plain board-level flag, not gated by
  `ALL_SYSTEMS`/the category umbrellas, so trimming systems doesn't trim it
  automatically. Worth re-checking the board file for other stock-copied
  flags like this (`diff` against `batocera-x86_64.board`) rather than
  assuming the systems tree covers everything.
- Phase 2a: PS1 (done, 2026-07-14). Enabled directly rather than the whole
  `BATOCERA_CONSOLE_SYSTEMS` umbrella, to get PS1 without
  N64/GameCube/Xbox/etc: `BR2_PACKAGE_DUCKSTATION=y`,
  `BR2_PACKAGE_LIBRETRO_SWANSTATION=y`, `BR2_PACKAGE_LIBRETRO_PCSX=y`,
  `BR2_PACKAGE_LIBRETRO_BEETLE_PSX=y` — every core
  `BATOCERA_CONSOLE_SYSTEMS`'s own `select` tree would enable for an
  x86_64 target specifically (`batocera-system/Config.in` ~1445-1468).
  `BR2_PACKAGE_DUCKSTATION_LEGACY` deliberately excluded: its condition is
  `!BATOCERA_GLES3`, and GLES3 defaults to `y` on x86_64, so it would never
  be selected here even in the stock full build.
- Phase 2b (not yet enabled — uncomment when ready): PS2,
  `BR2_PACKAGE_PCSX2=y`.
- Future: once this base is proven, adding a new system/port means: a
  package dir under `package/batocera/emulators/` (or
  `.../retroarch/libretro/`) with its own `Config.in`/`.mk`, a
  `.core.yml`/`.emulator.yml` registered via `pkg-emulator-info.mk`, and a
  matching entry (or new entry) in `es_systems.yml`. `ADD-GEOLITH.md`
  (repo root) is a worked case study of this — implemented 2026-07-14,
  adding the Geolith libretro core (`libretro-geolith`) as an extra
  emulator option for the existing `neogeo`/`neogeocd` systems, including
  the `exclude_extensions` mechanism (see "Systems selection hierarchy"
  above) needed since Geolith reads a different ROM format (`.neo`) than
  FBNeo/MAME, and a stale-`batocera-es-system`-build gotcha that initially
  made the new core invisible in ES despite building correctly. See
  `USER-INSTRUCTIONS.md` for the detailed writeup of both mechanics.
- `ADD-GOPHER64.md` (repo root) — a second case study, this time adding a
  **standalone (non-libretro)** emulator: `gopher64`, an optional extra
  core for the existing `n64` system (mupen64plus stays the default).
  Cargo/Rust package (`package/batocera/emulators/gopher64/`, modeled on
  `ruffle/`), opt-in via `BR2_PACKAGE_GOPHER64=y` in
  `configs/batocera-x86_64-arcade.board`, plus a new `configgen` generator
  module (`generators/gopher64/`) — the piece libretro cores never need,
  since libretro options flow through core-options instead of a Python
  generator. RetroAchievements is wired via a token-file
  (`retroachievements.json`) written from batocera's global RA settings,
  the same pattern `ppssppConfig.py` already uses for PPSSPP. Verified
  building (2026-07-17): `make x86_64-arcade-pkg PKG=gopher64` produces a
  working binary and `batocera-es-system` correctly lists it as an n64
  core — needed 3 source patches beyond the package skeleton (see
  `ADD-GOPHER64.md`'s "Build fixes actually needed" for the
  `-flto=thin`/GNU-`ar`/link-order gotchas of mixing a clang-family `CC`
  into a GCC cross toolchain).
- `TRIM-CANDIDATES.md` (repo root) — researched-but-not-implemented list of
  further non-emulation weight to cut (GPU driver vendors, firmware,
  Xorg/desktop bundle, background network services, lightgun drivers).
  Same pattern as Nvidia: everything in it is pulled in via unconditional
  Kconfig `select`, so trimming any of it means a new isolated patch file
  under `board/batocera/x86/local-patches/`, not a defconfig flag.

## Typical workflow for this fork

```
git apply board/batocera/x86/local-patches/no-nvidia.patch
make x86_64-arcade-defconfig
make x86_64-arcade-config          # fast — resolves Kconfig, no build
grep BATOCERA_NVIDIA output/x86_64-arcade/.config   # should be absent
grep -E 'BR2_PACKAGE_(MAME|LIBRETRO_FBNEO)=y' output/x86_64-arcade/.config  # should be present
make x86_64-arcade-show-build-order   # sanity check the package list first
make x86_64-arcade-pkg PKG=mame       # optional: time one package
make x86_64-arcade-build CMD="batocera-es-system-dirclean batocera-es-system" BATCH_MODE=1  # required after any Kconfig/es_systems.yml change — see below
make x86_64-arcade-build              # full image build
```

That `batocera-es-system` rebuild is required whenever the change enables/
disables an emulator or edits `es_systems.yml` — its Buildroot stamps have
no dependency edge onto other packages' Kconfig state (see "Two
non-obvious things" below), so skipping it ships a stale `es_systems.cfg`
and the expected system silently won't appear in EmulationStation even
though the underlying package built fine. Omit it only for changes that
don't touch emulator enablement (e.g. kernel/driver-only tweaks).
