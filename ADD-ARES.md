# ADD-ARES.md

Implementation notes for **ares** (https://ares-emu.net,
https://github.com/ares-emulator/ares), a higan/bsnes-descended multi-system
emulator, added as an extra, opt-in emulator choice for **NES/Famicom,
SNES/Super Famicom, Master System, the Mega Drive family (Mega Drive, Mega
CD, 32X), the PC Engine family (PC Engine, PC Engine CD, SuperGrafx), and
Nintendo 64** - each of those systems keeps its existing default emulator;
ares is purely an additional option.

## Verdict up front

**Status: packaged and registered, but does not yet build to completion.**
Kconfig/board/ES-registration/configgen wiring is done and verified correct
(see "What's actually verified" below - most of ares' own dependency graph
does compile successfully). The build is blocked on one real, well-understood
gap: **ares' Linux desktop UI hard-requires `librashader`, a Rust library
this buildroot doesn't package, and upstream provides no prebuilt Linux
binary for it** - see "librashader: the real remaining blocker" below. This
is a distinct, scoped follow-up task (package a new Rust library), not a
CMake flag or a small patch.

## What ares is, and the scope decision

Upstream: https://github.com/ares-emulator/ares, license `ISC`. A single
binary that emulates many systems (per `ares/CMakeLists.txt`'s `ARES_CORES`
list: `a26 fc sfc sg ms md saturn ps1 pce ng msx cv myvision gb gba ws ngp
spec n64`). This package trims that down to exactly six core codes via
`-DARES_CORES="fc;sfc;ms;md;pce;n64"` (see "The ARES_CORES footgun" below for
why the syntax matters) - the six needed to cover the ten batocera systems
requested:

| ares core code | batocera system(s) covered |
|---|---|
| `fc`  | `nes` |
| `sfc` | `snes` |
| `ms`  | `mastersystem` |
| `md`  | `megadrive`, `megacd`, `sega32x` (all three share the same "md" core subdirectory upstream - confirmed directly against `ares/CMakeLists.txt`, there is no separate `megacd`/`32x` `ARES_CORES` entry) |
| `pce` | `pcengine`, `pcenginecd`, `supergrafx` (same "one core, whole family" reasoning as `md`) |
| `n64` | `n64` |

Everything else `ARES_CORES` can build (Atari 2600, PlayStation, Neo Geo,
MSX, ColecoVision, MyVision, Game Boy/Color/Advance, WonderSwan, Neo Geo
Pocket, ZX Spectrum, SG-1000, Saturn) is left disabled - out of scope for
this addition, and several already have a different, established default
emulator in this fork.

Per-system `--system` name strings (used by the generator to disambiguate,
rather than relying on ares' own extension-based auto-detection - several of
these systems share an extension with another system ares also supports)
were confirmed directly against each system's own `mia/medium/*.cpp`
`name()` override:

| batocera system | ares `--system` value |
|---|---|
| `nes` | `Famicom` |
| `snes` | `Super Famicom` |
| `mastersystem` | `Master System` |
| `megadrive` | `Mega Drive` |
| `megacd` | `Mega CD` |
| `sega32x` | `Mega 32X` |
| `pcengine` | `PC Engine` |
| `pcenginecd` | `PC Engine CD` |
| `supergrafx` | `SuperGrafx` |
| `n64` | `Nintendo 64` |

## Independent emulator, not a core of any existing one

Same lesson as `ADD-STANDALONE-MAME.md`'s "Independent emulator, not a core
of mame", stated once there in full: `registry.py`'s
`Registry._iter_system_emulator_cores()` only synthesizes an implicit single
core for an emulator whose `.emulator.yml` has a `systems:` list and **no**
explicitly-registered cores (no companion `*.<emulator>.core.yml` file).
`ares.emulator.yml` (`package/batocera/emulators/ares/ares.emulator.yml`) has
no `cores:` key, so this is exactly the safe shape - Registry synthesizes one
implicit `ares` core on each of the ten systems listed in its `systems:`
list, with no cross-talk with any existing emulator on any of them (mesen/
fceumm on `nes`, snes9x on `snes`, genesisplusgx/picodrive on the Mega Drive
family, etc. are all completely untouched).

`custom_features` were deliberately left empty for v1: ares' CLI (per its
wiki) only documents `--system`/`--fullscreen`/`--shader`/`--no-file-prompt`,
and `aresGenerator.py` doesn't do any deeper `settings.bml` configuration
yet - see `standalone-mame.emulator.yml`'s own history (an earlier version
showed inert switchres/gun toggles) for why a non-functional ES toggle is
worse than no toggle at all.

## Packaging checklist

1. **`package/batocera/emulators/ares/`**:
   - `Config.in` - symbol `BR2_PACKAGE_ARES`, `select`s `BR2_PACKAGE_BATOCERA_QT6`
     (this fork's existing Qt6-umbrella Kconfig option, already used by
     duckstation/melonds/dolphin/pcsx2/rpcs3 - reused rather than adding a
     new GTK3 dependency, since GTK3 isn't packaged as a top-level
     `BR2_PACKAGE_GTK3`-style option in this buildroot at all, only as
     `libgtk3`/`libgtk4` with no existing batocera emulator precedent using
     it) and `BR2_PACKAGE_SDL2`.
   - `ares.mk` - `ARES_VERSION = v148`, `ARES_SITE = $(call
     github,ares-emulator,ares,$(ARES_VERSION))` (plain tarball fetch - ares
     has no git submodules, confirmed by a 404 on its `.gitmodules` and by
     everything needed, e.g. `nall`, actually being vendored as a plain
     nested directory in the tarball). Uses `cmake-package` +
     `emulator-info-package`, same shape as `melonds.mk`/`ymir.mk`.
   - `ares.emulator.yml` - the real ES-registration point (see above).
2. **Root `Config.in`**: one `source
   "$BR2_EXTERNAL_BATOCERA_PATH/package/batocera/emulators/ares/Config.in"`
   line, delivered via `board/batocera/x86/local-patches/ares.patch`
   (applied by `./apply-patches.sh`), not a direct commit - same convention
   `standalone-mame.patch`/`manufacturer-systems.patch` already established,
   since `./Config.in` is a file upstream batocera touches constantly.
   Verified: `git apply --check` clean against the current tree, and
   `make x86_64-arcade-config` correctly resolves `BR2_PACKAGE_ARES=y`.
3. **`configs/batocera-x86_64-arcade.board`**: `BR2_PACKAGE_ARES=y`, opt-in
   (not force-selected via any `BATOCERA_*_SYSTEMS` umbrella) - same
   "Option 2: turn on one specific emulator" pattern `standalone-mame`/
   `libretro-geolith` already use in this file.
4. **`.../generators/ares/`**: `aresGenerator.py` (`class AresGenerator`),
   `aresPaths.py` (the `--system` name table + bin path), `__init__.py`.
   Since the module/class names follow configgen's default naming
   convention exactly (`ares.aresGenerator` / `AresGenerator`), **no
   `importer.py` change is needed at all** - same as `gopher64`, unlike
   `standalone-mame`'s hyphen-forced `_GENERATOR_MAP` entry.

## The `ARES_CORES` footgun

`ares/CMakeLists.txt` declares `set(ARES_CORES a26 fc sfc sg ms md ps1 pce ng
msx cv myvision gb gba ws ngp spec n64 CACHE STRING "...")` - a real CMake
*list* (semicolon-joined internally; `set()` with unquoted, space-separated
arguments builds a list, it just happens to print space-joined in a plain
`message()`/summary). The actual per-core gating,
`list(TRANSFORM ARES_CORES STRIP)` followed by `if(fc IN_LIST ARES_CORES)`
for each code, only works against a real semicolon-joined list.

**First attempt got this wrong**: `-DARES_CORES="fc sfc ms md pce n64"`
(space-separated, matching how the default value is commonly *displayed*)
passed `git apply --check`/Kconfig validation fine and CMake accepted it
silently - but it's parsed as a **single one-element list** whose one
element is the literal string `"fc sfc ms md pce n64"`, which matches *none*
of the `IN_LIST` checks. Confirmed by a real build: the "Enabled Cores"
banner was completely empty and all 19 systems (including the six actually
wanted) showed up under "Disabled Cores." Fixed by using semicolons:
`-DARES_CORES="fc;sfc;ms;md;pce;n64"` - re-verified against a real build,
"Enabled Cores" then correctly listed exactly NES/Famicom, Nintendo 64,
PC-Engine/TurboGrafx, SNES/Super Famicom, Sega Master System/Mark III, Sega
Mega Drive/Genesis, nothing else.

## The `sourcery` cross-compilation footgun (fixed)

ares generates a handful of `resource.cpp`/`.hpp` files (icon/embedded
resource data for `ares`, `hiro`, `mia`, `desktop-ui`) via a tiny in-tree
host tool, `tools/sourcery/sourcery.cpp` (~70 lines, depends on nothing but
`nall`'s headers). Its own `tools/sourcery/CMakeLists.txt`:

```cmake
if(NOT (CMAKE_CROSSCOMPILING OR ARES_CROSSCOMPILING))
  add_executable(sourcery sourcery.cpp)
  export(TARGETS sourcery FILE "${CMAKE_BINARY_DIR}/sourceryConfig.cmake")
  ...
else()
  set(sourcery_DIR ${CMAKE_SOURCE_DIR}/build_native)
  find_package(sourcery)
endif()
```

Buildroot's `cmake-package` infra always sets `CMAKE_CROSSCOMPILING=TRUE`
(it always passes a cross-toolchain file, even though this fork's board is
x86_64-only - CMake still considers same-architecture-but-different-sysroot
a cross build). So this package always hits the `else()` branch, expecting a
previously-built native copy at `build_native/` - confirmed as the *intended*
workflow, not a bug, by ares' own cross-compile CI script,
`.github/scripts/build_windows.sh`:

```sh
if [ "$CROSS_COMPILE" = true ]; then
  cmake --preset $NATIVE_PRESET -B build_native
  pushd build_native
  cmake --build . --target sourcery --config RelWithDebInfo
  popd
fi
```

Reconfiguring ares' *entire* CMake tree a second time, natively, just to get
one small tool would drag in the same GTK3/Qt6/OpenGL/etc. discovery the
real (cross) configure already does - fine there, since it degrades
gracefully to a disabled-feature warning, but with no guarantee this build
container has a natively-runnable Qt6/GTK3 in the first place (it doesn't -
this is a Buildroot host container, not a desktop-dev one; see the
librashader section below for the same category of problem hitting the real
build for real).

**The actual fix turned out much smaller than "run CMake twice."** The real
build-time invocation this whole `sourcery_DIR`/`find_package` mechanism
feeds into (`cmake/common/helpers_common.cmake`'s `add_sourcery_command`) is
just a bare shell command:

```cmake
add_custom_command(... COMMAND sourcery resource.bml resource.cpp resource.hpp ...)
```

- a literal `$PATH` lookup, **not** a CMake target reference - confirmed
directly: the real failure was a plain `/bin/sh: 1: sourcery: not found`
during the *build* step, not a configure-time error. So instead of the
two-pass CMake dance, `ares.mk` just compiles `sourcery.cpp` directly with
the host compiler (`$(HOSTCXX)`, bypassing the cross toolchain and the whole
CMake tree entirely - it only needs `nall`'s headers) and drops the result on
`$(HOST_DIR)/bin/sourcery`, which is already on `PATH` for the rest of the
package's build steps:

```make
define ARES_BUILD_NATIVE_SOURCERY
	mkdir -p $(HOST_DIR)/bin
	$(HOSTCXX) -std=c++20 -O2 -DNALL_HEADER_ONLY \
	    -I$(@D) -I$(@D)/nall \
	    $(@D)/tools/sourcery/sourcery.cpp -o $(HOST_DIR)/bin/sourcery
endef
ARES_PRE_BUILD_HOOKS += ARES_BUILD_NATIVE_SOURCERY
```

Two things needed to get this one-file compile to actually link, both
confirmed against real compiler errors, not guessed:

- `-I$(@D)/nall` (not just `-I$(@D)`): `#include <nall/nall.hpp>` resolves
  against `$(@D)/nall/nall/nall.hpp` (yes, doubly-nested - `nall/nall/` is
  the real on-disk path in ares' own tree) - `nall/nall`'s own CMakeLists
  exports its *parent* dir as an interface include path for exactly this
  reason, which a raw compile has to replicate by hand.
- `-DNALL_HEADER_ONLY`: without it, linking fails with `undefined reference
  to nall::main(int, char**)` - `nall/main.hpp` only *declares* that
  function; its definition normally comes from a separately-compiled
  `nall/main.cpp` translation unit (part of the real `nall` CMake target),
  which a single-file raw compile doesn't have. `nall/main.hpp` itself
  documents the `NALL_HEADER_ONLY` fallback (`#include <nall/main.cpp>`)
  for exactly this situation.

Verified end to end: with both fixes, `hiro` (which needs `sourcery`-
generated resources) built successfully in a real `make x86_64-arcade-pkg
PKG=ares` run.

## librashader: the real remaining blocker

`ruby/cmake/os-linux.cmake` (ares' platform input/audio/video abstraction
layer, "ruby"), Linux branch:

```cmake
find_package(librashader)
if(librashader_FOUND AND ARES_ENABLE_LIBRASHADER)
  target_enable_feature(ruby "librashader OpenGL runtime" LIBRA_RUNTIME_OPENGL)
else()
  # continue to define the runtime so openGL compiles
  target_compile_definitions(ruby PRIVATE LIBRA_RUNTIME_OPENGL)
endif()
...
target_link_libraries(ruby PRIVATE ... $<$<BOOL:TRUE>:librashader::librashader> ...)
```

That `# continue to define the runtime so openGL compiles` comment is
upstream being explicit: `LIBRA_RUNTIME_OPENGL` is defined **either way**,
so `ruby/video/opengl/opengl.hpp`'s `#include
<librashader/librashader_ld.h>` is unconditional, and so is the
`target_link_libraries` line linking `librashader::librashader`. **A first
pass at this package mis-read that unconditional link line as an upstream
bug** (every other optional dependency in that same `target_link_libraries`
call - SDL, OpenAL, AO, udev - correctly gates on its own `_FOUND` variable)
and shipped a one-line patch making it conditional too. That patch has since
been **removed** - it was based on a wrong diagnosis (confirmed by actually
reading the comment above it) and wouldn't have fixed anything anyway, since
the `#include` in `opengl.hpp` is unconditional regardless of the link line.
On Linux, with the Qt6/GLX video driver this package builds (the only video
driver `ruby/cmake/os-linux.cmake` compiles - `video/glx.cpp`), librashader
is a genuine, hard, upstream-intended build requirement, not an optional
shader-effects nicety to disable.

**Where librashader is supposed to come from, and why it isn't available
here**: ares vendors only librashader's C headers directly in-tree
(`thirdparty/librashader/include/librashader/librashader_ld.h` - confirmed
present after extraction), not the compiled library.
`cmake/finders/Findlibrashader.cmake` expects the actual compiled library to
already exist as a real system library - confirmed directly by its own
platform-conditional error text:

```cmake
if(CMAKE_HOST_SYSTEM_NAME MATCHES "Darwin|Windows")
  set(librashader_ERROR_REASON "Ensure that ares-deps is provided as part of CMAKE_PREFIX_PATH.")
elseif(CMAKE_HOST_SYSTEM_NAME MATCHES "Linux|FreeBSD")
  set(librashader_ERROR_REASON "Ensure librashader libraries are available in local library paths.")
endif()
```

Windows/macOS get it from upstream's own prebuilt "ares-deps" bundle
(fetched via `deps.json` + `file(DOWNLOAD ...)` at CMake configure time,
gated off entirely by `-DARES_SKIP_DEPS=ON`); Linux/FreeBSD are explicitly
told to provide it themselves. Confirmed two ways, not assumed:

1. A real build with `ARES_SKIP_DEPS` *unset* (i.e. letting the ares-deps
   fetch run) still shows `Could NOT find librashader` - the Linux
   ares-deps archive (`.deps/ares-deps-linux-universal/`, successfully
   fetched/extracted during this check) only contains shader **assets**
   (`share/libretro/shaders/shaders_slang/`), never a compiled librashader
   library, on this platform.
2. librashader's own GitHub releases
   (`SnowflakePowered/librashader`, checked directly against its latest
   release, `librashader-v0.12.0`) publish prebuilt archives for macOS
   (aarch64/x86_64) and Windows (x86_64/win7/aarch64) only - **no Linux
   binary exists to just fetch and drop in**, prebuilt-binary-package style.

**What actually finishing this needs**: a new Buildroot package building
librashader from source - it's a Rust project
(https://github.com/SnowflakePowered/librashader) that produces a C-ABI
dynamic library + matching headers (there's a `librashader-capi` crate in
its own tree for exactly this). This is a genuinely separate, substantial
sub-task - comparable in shape to what `ADD-GOPHER64.md` needed for its own
Cargo-based package (its own toolchain/cross-compilation quirks to work
through) - not a flag, small patch, or quick fix, so it wasn't attempted as
part of this session. Whoever picks this up next: package `librashader`
first (a `cargo-package`-based `.mk`, likely modeled on `gopher64.mk`'s
Cargo plumbing - see `USER-INSTRUCTIONS.md`'s gopher64 section for the
`-flto=thin`/clang-vs-GCC/`RUSTFLAGS`-scoping gotchas that class of package
tends to hit), matching whatever `find_path`/`find_library` in
`cmake/finders/Findlibrashader.cmake` (above) actually expects on disk
(headers under a path containing `librashader/librashader_ld.h`; a library
named `librashader` or `rashader` discoverable via `pkg-config` or the
standard `/usr/lib`/`/usr/local/lib` search paths) - then re-run `make
x86_64-arcade-pkg PKG=ares` from a clean `ares-dirclean` and confirm the
`ruby`/`hiro`/`ares`/`mia`/`desktop-ui` targets actually link and the
install step (see "Open items" below) produces a real, launchable binary.

## What's actually verified

- `make x86_64-arcade-defconfig` + `make x86_64-arcade-config BATCH_MODE=1`
  correctly resolve `BR2_PACKAGE_ARES=y`, `BR2_PACKAGE_BATOCERA_QT6=y`,
  `BR2_PACKAGE_SDL2=y`, `BR2_PACKAGE_QT6BASE=y`, `BR2_PACKAGE_QT6SVG=y`.
- `make x86_64-arcade-show-build-order BATCH_MODE=1` lists `ares` in the
  package graph.
- `git apply --check board/batocera/x86/local-patches/ares.patch` is clean
  against the current tree, and `./apply-patches.sh` reports it as already
  applied alongside the other three local patches with no conflicts.
- A real `make x86_64-arcade-pkg PKG=ares` run, after the `ARES_CORES`
  semicolon fix and the `sourcery` native-bootstrap fix, successfully
  configures (correct "Enabled Cores" banner, exactly the six requested) and
  compiles a substantial fraction of the dependency graph: `thirdparty`
  (tzxfile, sljit, chdr-static/libchdr, ymfm, miniz, zstd, qon), `nall`,
  `libco`, and **`hiro`** (which needs `sourcery`-generated resources, so its
  success specifically confirms that fix) all build cleanly. It currently
  stops at `ruby.cpp` failing to compile on the missing librashader header,
  per above.

## Open items for whoever continues this

1. **librashader** (above) - the actual blocker; nothing past `ruby`/`hiro`
   has been build-tested yet as a result (`ares`, `mia`, `desktop-ui` targets
   are all unverified).
2. **Install-tree layout unconfirmed.** `ares.mk`'s
   `ARES_INSTALL_TARGET_CMDS` copies a `buildroot-build/rundir/` tree
   (matching upstream's own wiki, which documents running
   `./rundir/bin/ares` relative to the build dir - a staged folder bundling
   the binary with resource/database files it needs alongside it, not just
   the executable) - this hasn't been confirmed against a real completed
   build yet, only against the wiki text. Re-check once librashader is
   packaged and a full package build actually finishes.
3. **SDL2 not detected** despite `BR2_PACKAGE_SDL2` selected and `sdl2`
   listed as a dependency - CMake configure shows `Could NOT find SDL
   (missing: SDL_LIBRARY SDL_INCLUDE_DIR) (found version "0.0.0")`. Not
   blocking (Xlib input + ALSA/OSS/PulseAudio audio are already enabled and
   sufficient), but worth a look - likely `FindSDL.cmake` looking for a
   different package/pkg-config name than what this buildroot's `sdl2`
   package provides.
4. **Firmware/BIOS placement not designed at all.** ares (a higan/bsnes
   descendant) uses its own per-system "System" firmware-folder convention
   (inherited from higan), not a single shared BIOS-file convention the way
   most other emulators in this repo work - Mega CD/32X/PC Engine CD in
   particular are likely to need firmware placed in whatever layout ares
   itself expects. Not investigated in this pass - needs a real launch
   attempt (once the build itself is unblocked) to even observe what ares
   asks for.
5. **`aresGenerator.py`'s `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`XDG_CACHE_HOME`
   redirection is unverified.** Written on the assumption that ares (built
   here with `USE_QT6=ON`) honors Qt's `QStandardPaths`, which does respect
   these on Linux - but it's not confirmed whether ares' own `nall`-based
   path resolution (a higan-era codebase, predating this redirection
   becoming a common Linux convention) actually uses `QStandardPaths` at
   all, versus some other mechanism entirely. Needs a real launch to check
   where ares actually leaves its config/save files.
6. **Hotkeys are a minimal placeholder.** `aresGenerator.getHotkeysContext()`
   only maps `exit`; no verified keybinding info exists yet for menu/pause/
   save-state, unlike the fuller hotkey maps other generators in this repo
   provide.
