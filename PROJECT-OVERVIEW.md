# PROJECT-OVERVIEW.md

A generic technical reference for how the batocera.linux repository is
structured and how its Buildroot-based build system works. This document is
deliberately fork-agnostic — it describes mechanics that apply to any
batocera.linux checkout and any build target, not the specifics of any one
custom build. It is intended as a starting point for wiki-quality
documentation of the project's internals.

---

## What batocera.linux is

Batocera.linux is a Buildroot-based Linux distribution that boots directly
into EmulationStation (an ES-DE fork) with RetroArch and a large collection
of standalone emulators. It is designed to run from a USB stick or SD card
without modifying the host machine it boots from.

## Repository layout

- `buildroot/` — vendored copy of Buildroot itself, the underlying
  build system. Not normally edited directly.
- `board/` — per-platform patches, kernel configuration, filesystem
  overlays, and boot scripts. Each supported architecture/platform has its
  own subdirectory (kernel defconfig fragments, patches applied at build
  time, root filesystem overlay files, boot-time scripts).
- `configs/` — one `*.board` file per build target, plus shared fragments
  (e.g. a common file included by every board). The set of available
  `make <name>-*` targets is derived automatically from the `.board` files
  present in this directory — adding a new `.board` file creates a new,
  independent build target with no other registration step required.
- `package/batocera/` — the actual batocera-specific packages: Buildroot
  `Config.in`/`.mk` pairs for every emulator, system utility, and
  integration package. This is the primary place to look when working on
  emulator support or system-level features.
- `python-src/` — Python source packages (managed with `uv`), including the
  tooling that generates EmulationStation's system metadata at build time.
- `docker/` — the official build container definition (`Dockerfile`) and
  the make integration for building/pulling/using it.

## The config pipeline: board file → defconfig → `.config`

A build target's configuration flows through several stages before it
becomes the resolved set of options Buildroot actually builds from:

1. `configs/batocera-<target>.board` — the human-edited source of truth for
   a target. Board files can `include`/`-include` other files (e.g. a
   common fragment shared by every board), and are resolved by
   `configs/createDefconfig.sh`, which concatenates included files first,
   then the board file's own lines, then any local overrides — later lines
   win for the same `BR2_*` symbol, **unless** something else forces that
   symbol via a Kconfig `select` (see below).
2. This produces `configs/batocera-<target>_defconfig`, a flat list of
   `BR2_*` assignments.
3. Buildroot's own `defconfig` mechanism resolves that flat list against the
   full Kconfig dependency tree (every `Config.in` file reachable from the
   project's top-level `Config.in`), writing the fully resolved
   configuration to `output/<target>/.config`.
4. Buildroot builds from `output/<target>/.config`.

Because resolution happens in a defined order, a plain assignment in a board
file can still be overridden if some enabled option `select`s that same
symbol elsewhere in the Kconfig tree — Kconfig `select` is a forced/reverse
dependency, not a suggestion, and takes priority over a plain `=n`/`=y`
assignment for the same symbol.

## Package anatomy

Every `BR2_PACKAGE_*` option corresponds to a real package directory
containing:

- A `Config.in` — the Kconfig toggle itself (a `bool` prompt/description,
  plus any dependencies or `select` relationships to other options).
- A `.mk` file — the actual Buildroot build recipe (where to fetch the
  source, how to configure/build/install it).

Two package layouts are common for emulation-related packages:

- `package/batocera/emulators/<name>/` — standalone emulators that run as
  their own program rather than through RetroArch (e.g. full standalone
  builds of various console/computer emulators).
- `package/batocera/emulators/retroarch/libretro/libretro-<name>/` —
  libretro "cores" that plug into the RetroArch frontend. RetroArch itself
  is a separate package that hosts all of these cores.

A single system can offer both a standalone emulator and one or more
libretro cores as alternative choices — nothing prevents enabling more than
one emulator for the same system; EmulationStation lets the user pick which
one to launch at runtime.

## The systems-selection Kconfig hierarchy

The central Kconfig file for systems selection is
`package/batocera/core/batocera-system/Config.in`. At its top,
`BR2_PACKAGE_BATOCERA_ALL_SYSTEMS` (on by default for every board) `select`s
eleven category umbrella options, each of which in turn `select`s the
individual emulator packages belonging to that category:

| Category | What it covers |
|---|---|
| `ARCADE_SYSTEMS` | MAME, FinalBurn Neo, MAME2003-Plus, Sega Model 2/3, Naomi/Atomiswave, laserdisc games |
| `CONSOLE_SYSTEMS` | Home consoles: N64, GameCube/Wii, Xbox/Xbox 360, PlayStation generations, and more |
| `HANDHELD_SYSTEMS` | Game Boy/Color/Advance, Nintendo DS/3DS, PSP/Vita, and other handhelds |
| `COMPUTER_SYSTEMS` | Home computers (Amiga and similar vintage computer platforms) |
| `MSDOS_SYSTEMS` | DOS games, via DOSBox and its variants |
| `SCUMMVM_SYSTEMS` | ScummVM, the point-and-click adventure game engine |
| `HOMEBREW_SYSTEMS` | Homebrew/engine-based games and fantasy consoles |
| `WINE_SYSTEMS` | The Wine Windows-compatibility layer, enabling Windows-only games/emulators |
| `GAMESTREAM_SYSTEMS` | Game-streaming clients (e.g. Moonlight, for streaming from a GameStream/Sunshine host) |
| `PORTS_SYSTEMS` | Native source ports of classic games |
| `FLASH_SYSTEMS` | Adobe Flash game emulation |

Note that `BATOCERA_RETROARCH` (the RetroArch frontend package itself) is
selected directly by `ALL_SYSTEMS`, not by any of the category umbrellas —
a configuration that disables `ALL_SYSTEMS` in favor of hand-picking
categories/systems must select `BATOCERA_RETROARCH` explicitly if any
libretro cores are wanted.

**A forced `select` cannot be turned off from a defconfig alone.** If some
enabled option unconditionally (or conditionally-but-currently-true)
`select`s a package, setting that package to `=n` in a board file or local
override gets silently re-forced back to `=y` — Kconfig re-resolves the
forced dependency every time. The only way to actually exclude something
selected this way is to remove or condition the `select` line itself in the
`Config.in` that contains it. Since that file is typically shared/upstream
content, a common technique is to keep the modification as a standalone
`.patch` file (applied with `git apply` before generating a defconfig)
rather than a permanent edit — this keeps the change easy to see, drop, or
regenerate independently, and avoids an unnecessary permanent diff against
upstream in a file that changes frequently.

The EmulationStation menu is not driven by a separate, hand-maintained
list — it's generated at build time from whichever emulator packages
actually got compiled in (see next section). Enabling a system therefore
always means enabling the `BR2_PACKAGE_*` option for one of its emulators;
there is no separate menu file to edit.

## How the EmulationStation system list gets built

`package/batocera/emulationstation/batocera-es-system/es_systems.yml` is
the static master list of every system batocera knows about and every
possible emulator/core for it, with each emulator entry tagged with the
`BR2_PACKAGE_*` option (`requireAnyOf: [...]`) that would enable it.

At build time, a dedicated package cross-references that static list
against whichever emulator packages are *actually* enabled in the current
configuration — each enabled emulator package registers its own metadata
file (a `.core.yml` for libretro cores or `.emulator.yml` for standalone
emulators) via a shared Buildroot include that gates registration on that
package's own Kconfig option. The result is written out as the actual
system-list file EmulationStation reads at runtime. A system with zero
enabled emulators is silently omitted from the generated list entirely —
again, there's no separate hand-edited menu to keep in sync.

Two non-obvious mechanics worth knowing about this pipeline:

1. **The generator package's Buildroot build stamps have no dependency edge
   onto other packages' Kconfig state or onto the static YAML's content.**
   Editing the static system list, or newly enabling an emulator/core
   package, does not by itself invalidate the generator package's existing
   "already built" stamps. On an incremental rebuild this can silently
   ship a stale generated system list even though the newly-enabled
   package itself builds and installs correctly — the fix is to force a
   targeted rebuild of just the generator package (Buildroot supports
   `<pkg>-dirclean <pkg>` as a forced clean-and-rebuild of one package by
   name) after any such change, then do a normal build to fold the
   regenerated file into the image. When verifying a change to the system
   list took effect, check the actual generated file under the build
   output directory, not the source YAML — the source can be completely
   correct while the generated artifact is stale.
2. **The static YAML's per-system emulator-choice metadata block is largely
   informational/schema-validated only, not the actual mechanism used at
   generation time.** The real per-system emulator/core list, and any
   per-core file-extension exclusivity (for cases where two emulators for
   the same system read genuinely different file formats), is derived
   entirely from each package's *own* metadata file — specifically an
   `exclude_extensions:` field under that core's own system entry, not a
   field of the same intent living in the static system-list YAML. When a
   field in the static YAML looks like it should control behavior but
   doesn't seem to take effect, verify what the generator code actually
   reads before assuming the field name itself is wrong.

## How the per-game options menu gets built

Related to, but distinct from, the system list above: the per-game/per-system
*options* menu in EmulationStation (aspect ratio, shaders, and per-core
options like a specific PSX core's renderer/filtering settings) is built by
the same `.core.yml`/`.emulator.yml` metadata files and the same
`batocera_es_system` registry/build tooling, but produces a different output
(`es_features.cfg` rather than the system list), and has an entirely separate
downstream half — the "configgen" pipeline that turns the user's picked value
into the actual config file an emulator reads at launch. This is generic
mechanics, not specific to this fork, so it's documented in full in
`CUSTOM-OPTIONS.md` at the repo root rather than here — see that file for the
complete YAML-declaration-to-emulator-config pipeline, including how
per-core vs. shared/global options differ, how multiple cores per system
coexist, what "dynamic" options actually means in this codebase (mostly
build-time Kconfig gating, not runtime conditionals), and a checklist for
adding/removing/reorganizing an option.

## Build mechanics & useful make targets

The top-level `Makefile` exposes a family of per-target make targets
(substituting the actual target name, e.g. a board's short name, for
`<target>`):

- `<target>-defconfig` / `<target>-config` — generate the defconfig and run
  Buildroot's Kconfig resolution only; fast, does not compile anything.
  Useful for validating a configuration change before committing to a full
  build.
- `<target>-build` — the full build: regenerates the defconfig/config
  automatically first (so board-file edits are always picked up), then
  invokes Buildroot to compile and package everything.
- `<target>-kernel` — shortcut into the kernel's own `menuconfig`.
- `<target>-pkg PKG=<name>` — build (or rebuild) a single named package in
  isolation, without touching the rest of the build — useful for testing a
  change to one package quickly, or for sanity-checking the toolchain
  before committing to a multi-hour full build.
- `<target>-show-build-order`, `<target>-graph-depends` — inspect the
  resolved package build order / dependency graph without building.
- `<target>-clean`, `<target>-cleanbuild` — wipe a target's build output
  and start over.
- `<target>-shell` — open a shell inside the build environment.
- `<target>-ccache-stats` — report ccache hit rate.
- `<target>-systems-report[-clean|-serve]` — generate (and optionally serve
  over HTTP) a report of what would land in the image for a target, without
  doing a full build.

`CMD=` forwards directly to the underlying Buildroot invocation — for
example, `make <target>-build CMD=menuconfig` (or `nconfig`/`xconfig`) opens
the interactive Kconfig menu with every currently-resolved option, letting
options be browsed/toggled interactively rather than by hand-editing a
board file.

**Docker vs. direct build**: builds run inside a dedicated Docker container
by default, using an image pulled or built from `docker/Dockerfile`. A
`DIRECT_BUILD` flag bypasses Docker and builds directly on the host
instead — in that mode the host machine itself must satisfy whatever
package list the Dockerfile otherwise provides inside the container.

## Docker build image staleness

None of the actual compiling happens on the host machine when building via
Docker — the locally cached build image is used as-is every time. Docker
does not automatically refresh that local image just because
`docker/Dockerfile` changed upstream; a locally built or pulled image keeps
being reused until explicitly rebuilt or re-pulled.

To check whether a local image predates the current `Dockerfile`, compare
the image's creation timestamp (`docker inspect <image> --format
'{{.Created}}'`) against the `Dockerfile`'s last commit date (`git log -1
--format=%ai -- docker/Dockerfile`). If the image is older, it's stale.
Building against a stale image can produce misleading, seemingly-unrelated
compiler errors — an older toolchain inside a stale image can genuinely
fail to compile source that a current toolchain handles fine, which looks
like an upstream source bug but is purely an artifact of the local image
being out of date. Rebuilding the image (typically a dedicated make target
for forcing this) is worth trying before spending time chasing what looks
like a compiler/source-level bug right after a Dockerfile update.

There is also a mirror-image failure mode: the image itself gets updated
(bumping some underlying system library or interpreter version), but a
target's build output directory is a persistent volume that survives image
rebuilds — so any previously-built artifact that happens to have been
compiled *against the container's own system tools* (rather than
Buildroot's cross-compilation toolchain) can be left stale and broken by
the image update, even though nothing in the source tree changed. This is
narrow in practice — most packages build entirely against Buildroot's own
toolchain and are unaffected — but it's worth knowing the failure signature
(a package that built fine before suddenly fails after an image update,
with an error that points at a host-side tool or library version mismatch)
so it isn't mistaken for a genuine source regression. The fix in that case
is a targeted rebuild of just the affected package.

## Parallelism and speed levers

Buildroot's parallelism operates on two independent layers, and a plain
build only benefits from one of them by default:

- **Within one package's own compile step**, multiple cores are already
  used automatically — Buildroot's per-package job-level setting defaults
  to "determine automatically according to number of CPUs on the host."
- **Across different packages, building is serial by default** — one
  package fully downloads/configures/builds/installs before the next one
  starts. For a build consisting of many small-to-medium packages (rather
  than a handful of very large ones), this serial-across-packages behavior
  leaves a lot of host CPU idle even on a many-core machine, since a small
  package with few source files can't itself use all available cores.

A `PARALLEL_BUILD` flag turns on the second layer: it enables Buildroot's
per-package build-directory isolation (letting genuinely different
packages build concurrently, each in its own isolated directory) and adds
a top-level parallel job count to the actual `make` invocation, which is
required for that concurrency to take effect.

**Important caveat**: the per-package build-directory isolation setting
changes Buildroot's internal build-directory layout. It cannot be toggled
on for a build that's already in progress — an already-running build needs
a full clean rebuild to pick it up, not just re-running the build target
with the flag added. For an already-running first build, it's generally
better to let it finish and enable the parallel flag starting with the
next build, rather than restart mid-build (ccache still speeds up anything
already compiled once, so restarting isn't a full time cost, but it isn't
free either).

**A make flag like `PARALLEL_BUILD` only applies to the specific `make`
invocation it's passed on** — it is not persisted anywhere between separate
commands. Because every make target that resolves configuration
(`<target>-defconfig`, `<target>-config`, `<target>-build`, etc.) re-derives
the defconfig from scratch on each invocation, a flag has to be present on
*every* command in a multi-step sequence (e.g. running `-defconfig`, then
`-config`, then a targeted `-build CMD=...`, then a final `-build`) — adding
it only to the last command in that sequence means earlier steps silently
ran without it. If a build has already produced output under a different
setting for a toggle like `PARALLEL_BUILD` and a later step in the same
sequence flips it, that's the same "toggled mid-build" situation described
above, just triggered by an inconsistent flag across separate commands
rather than by editing a running build directly.

To set a flag permanently for every invocation without retyping it, the
top-level `Makefile` silently includes a local override file
(`-include batocera.mk`, controlled by the `LOCAL_MK` variable) if one
exists at the repo root — this file is a normal Makefile-syntax fragment,
already covered by `.gitignore` since it's meant for personal/local
settings, not something to commit. Putting `PARALLEL_BUILD=y` there is
enough to make every subsequent `make <target>-*` command behave as if the
flag were passed explicitly, without needing to remember it per command.

Other relevant levers:
- ccache is on by default for every board and persists across builds in a
  dedicated cache directory, so rebuilding after a source change is
  typically much faster than the very first build.
- A `<target>-refresh`-style target can do a surgical incremental rebuild
  of only recently-changed packages (based on recent commit history),
  rather than reasoning about which packages need rebuilding by hand.
- Every build writes a running per-package log as it progresses
  (`build-time.log` under the target's output directory), which can be
  tailed live from a separate terminal to watch progress without
  interfering with the running build.
- Finished images land under the target's `images/` output directory once
  a build completes fully.

## Common build gotchas

**Buildroot's per-package "already built" stamp files have no dependency
edge onto arbitrary related state** — not onto another package's Kconfig
option, and not onto the content of files that aren't that package's own
declared inputs. Two situations where this bites in practice:

- A package that builds from local, in-repository source (rather than
  fetching an upstream tarball/git commit) via a source-directory override
  mechanism: editing that local source does not itself invalidate the
  package's "already built"/"already installed" stamps. A plain incremental
  build will leave the old, unmodified build artifact in place.
- A package whose output depends on cross-referencing another package's
  Kconfig state or an unrelated data file (as described above for the
  EmulationStation system-list generator): enabling a new option elsewhere,
  or editing that data file, does not invalidate this package's stamps
  either.
- A package's *own* build-system configure flags, when those flags are
  themselves derived from a Kconfig option that gets turned on *after* that
  same package already built successfully once. Enabling a new umbrella of
  options can flip on a build flag for a package that was already built
  earlier for an unrelated reason (a common shared dependency needed by
  several packages, brought in early by one of them, then reused later by
  another that needs it configured differently) — the package's one-time
  configure step doesn't automatically re-run just because the flags it
  would now be given have changed. This tends to surface as a *different*,
  dependent package failing at build or link time with something missing,
  which can look at first like a packaging bug in the dependent package
  when the actual stale artifact is the shared dependency.

In all three cases, the general fix is the same: force a targeted rebuild
of just the affected package with a dedicated clean-then-rebuild invocation
naming that package specifically, rather than assuming a plain incremental
build will pick up the change. If a source or configuration edit doesn't
seem to have any effect after rebuilding, check whether the affected
package's build stamps actually postdate the edit before concluding the
code itself is wrong; for the third case specifically, diff that package's
own on-disk build-system cache file (e.g. a CMake `CMakeCache.txt`) against
the currently resolved `.config` to confirm the mismatch directly, rather
than assuming the Kconfig `select` graph alone explains a dependent
package's failure.

**A distribution's embedded version string is not a reliable
freshness signal for any specific change.** It is typically written by one
specific package's own install step (embedding, for example, the current
git commit hash at the moment *that* package last installed) — and that
package is, like any other, independently stamped with no dependency edge
onto whatever else may have changed. It can legitimately lag behind (or
even sit ahead of) the real content of any other package. To verify a
specific fix actually made it into a build, check the relevant installed
file directly under the target's build output directory, or better,
extract it straight from the final packaged root filesystem image — that's
the only artifact that actually gets flashed.

**Manual build-directory cleanup can leave a build in a confusing state.**
If clearing a package's build directory by hand (rather than through
Buildroot's own dedicated clean target), make sure to also remove dotfiles
— a shell glob that only matches regular filenames can silently skip
Buildroot's own internal stamp files, leaving a stale stamp pointing at a
build tree that's no longer actually there, which produces a confusing
error on the next build rather than a clean rebuild.

**Docker-run builds can leave build output owned by an unexpected user**,
which can then cause a later host-side cleanup (or a Buildroot clean
target that isn't run through Docker) to fail with a permission error. This
can be recovered without elevated host privileges by running a throwaway
container that mounts the same output directory and changes ownership back
from inside the container.

## Adding a new emulator/core for an existing system

The general recipe for adding a new emulator choice (either a new
libretro core or a new standalone emulator) for a system that already
exists in batocera:

1. Create a new package directory under `package/batocera/emulators/` (for
   a standalone emulator) or
   `package/batocera/emulators/retroarch/libretro/libretro-<name>/` (for a
   libretro core), containing:
   - A `Config.in` defining the new `BR2_PACKAGE_*` toggle.
   - A `.mk` file that fetches a pinned upstream version, builds it (using
     the emulator's own build system, or a wrapper `Makefile` for libretro
     cores), and installs the resulting binary/shared object into the
     target image.
   - A metadata file (`.core.yml` for a libretro core, `.emulator.yml` for
     a standalone emulator) declaring which system(s) it supports. This
     file is only picked up when the package's own Kconfig option is
     enabled.
2. If the new emulator is for a system that doesn't yet exist in the
   static system list, add a corresponding entry there; if it's simply a
   new choice for an existing system, no change to the static list is
   needed — the new emulator's own metadata file is enough to register it
   as an additional option for that system.
3. Only add code to the Python configuration-generator layer when the new
   emulator's own option keys need translating into different, more
   user-facing values (e.g. mapping a friendly label to an internal
   setting the emulator expects). If the emulator's native option keys are
   already suitable to expose directly, no generator code changes are
   needed — a `custom_features` block in the metadata file is sufficient
   to surface the option in the user-facing settings UI.
4. When a system has multiple emulator choices that read genuinely
   different file formats for the same logical system, express that via
   each emulator's own metadata file (an exclusion list of file extensions
   that particular emulator doesn't handle), rather than trying to encode
   it in the static system list.

Verifying a new addition end-to-end means confirming both that the new
package actually built and installed its binary, *and* that the generated
system-list file (not just the source YAML) reflects the new option — see
the EmulationStation system-list section above for why those can diverge
on an incremental build.
