# ADD-GOPHER64.md

Research and implementation notes for adding **gopher64**
(https://github.com/gopher64/gopher64), a standalone (non-libretro),
Rust/SDL3/Vulkan Nintendo 64 emulator with built-in RetroAchievements
support, as an extra selectable core for the existing `n64` system.
Unlike `ADD-GEOLITH.md` (a libretro core), this is the case study for
adding a **standalone** emulator: a new Cargo-built Buildroot package plus
a new `configgen` Python generator module.

**Status: implemented and built successfully (2026-07-17).** mupen64plus
stays the default n64 emulator; this is purely additive. Opt-in only (not
force-selected via `BATOCERA_NINTENDO_SYSTEMS`), per the fork owner's
explicit choice — see "Scope decisions" below. `make x86_64-arcade-pkg
PKG=gopher64` produces a working `/usr/bin/gopher64` ELF binary (verified
`readelf -d` output: dynamically linked against `libvulkan.so.1`,
`libfreetype.so.6`, `libfontconfig.so.1`, `libstdc++`, `libc` — no
`libSDL3.so` dependency, confirming it statically vendors its own SDL3 as
expected), and `batocera-es-system` correctly lists `gopher64` as a
selectable n64 core (`es_systems.cfg`) with its three custom options
(`es_features.cfg`), alongside mupen64plus/libretro, unaffected. Getting
there needed four non-obvious build fixes beyond the initial package
skeleton — see "Build fixes actually needed" below; the "Open items"
section from the original research pass has been resolved and folded in
below rather than left as speculation.

## What gopher64 is

- Author: gopher64 project (portions adapted from mupen64plus and ares,
  per its `LICENSE`). Cross-platform (Windows/macOS/Linux/Android),
  actively released (tags roughly every few days as of this writing,
  pinned here to `v1.1.20` — the newest tag whose `Cargo.toml`
  `rust-version` (1.95.0) this buildroot's vendored Rust toolchain still
  satisfies; v1.1.22 onward requires 1.96.0+).
- License: GPLv3.
- Rendering: Vulkan only, via a vendored `parallel-rdp-standalone` (LLE RDP
  emulation) — no OpenGL fallback. This fork's x86 target already
  force-selects `BR2_PACKAGE_BATOCERA_VULKAN` (AMD RADV) unconditionally
  (`package/batocera/core/batocera-system/Config.in`, the `BATOCERA_GPU_X86`
  block), so no new GPU-driver work was needed.
- Windowing/input/audio: SDL3 (already packaged in this fork —
  `package/batocera/libraries/sdl3/`, used by `xemu`/`cemu`/`rpcs3`/etc).
- Build system: Cargo (Rust, edition 2024). Three real git submodules
  (`.gitmodules`): `parallel-rdp/parallel-rdp-standalone`,
  `src/compat/sse2neon`, `retroachievements/rcheevos` — all C/C++,
  compiled directly by `build.rs` via the `cc` crate (no CMake step of its
  own), with `bindgen` generating the Rust FFI bindings for them.
- RetroAchievements: built in via the vendored `rcheevos` C library.

## Build system specifics (confirmed by reading gopher64's own
`Cargo.toml`/`build.rs`/`src/lib.rs`/`src/ui.rs`/`src/ui/config.rs`/
`src/retroachievements.rs` directly, not inferred)

- **Must be a git checkout, not a GitHub tarball.** The three submodules
  above are real git submodules; a `$(call github,...)` tarball checkout
  (the shortcut `ruffle.mk` uses) would silently omit them. Buildroot's
  `GIT_SUBMODULES = YES` knob (`buildroot/package/pkg-download.mk`) handles
  the recursive clone automatically.
- **`bindgen` needs libclang on the host at build time** (via the
  `clang-sys` crate, dlopen'd from `build.rs`, not merely a compile-time
  header dependency). `host-clang` is already a proven dependency in this
  repo for exactly this reason — both `duckstation.mk` and buildroot's own
  `rust-bindgen` package (`buildroot/package/rust-bindgen/rust-bindgen.mk`)
  depend on it the same way. Added to `GOPHER64_DEPENDENCIES`.
- **SDL3 linking — corrects the original research pass.** The `sdl3-sys`/
  `sdl3-ttf-sys` crates' own default features (`use-pkg-config`/
  `use-vcpkg`) are irrelevant here: gopher64's own `Cargo.toml` pins them
  to `features = ["build-from-source-static"]` explicitly, overriding the
  crates' defaults. This **always** vendors and statically links SDL3
  from source (a `sdl3-src` crate downloads SDL-3.4.8's own CMakeLists.txt
  tree, built via the `cmake` crate), regardless of any system SDL3.
  Confirmed by the actual build log (a full SDL3 CMake configure/build
  runs as part of `cargo build`) and by the final binary's `readelf -d`
  showing no `libSDL3.so` NEEDED entry. Consequence: **no batocera
  `sdl3`/`sdl3_ttf` package dependency is needed or used** — an earlier
  version of this package's `Config.in`/`.mk` selected/depended on them
  based on the (wrong, for this specific pinned version) assumption that
  pkg-config would find this fork's own SDL3 build; removed once the
  build log made the real behavior clear.
- **No `[[bin]]` in `Cargo.toml`**: the crate is `crate-type = ["cdylib",
  "rlib"]`, but `src/main.rs` exists, so Cargo creates an *implicit*
  binary target named after the package (`gopher64`). This means the
  **default** `cargo-package` `INSTALL_TARGET_CMDS`
  (`cargo install --bins --path ./`, see `buildroot/package/pkg-cargo.mk`)
  is sufficient — no manual `INSTALL_TARGET_CMDS` override needed, unlike
  `ruffle.mk` (whose actual binary lives in a workspace-member
  subdirectory and needs a manual copy).
- **`gui` Cargo feature, left on by default** (`default = ["gui"]` in
  `Cargo.toml`) pulls in `slint` (a full UI toolkit, wgpu/femtovg
  backend), `rfd` (native file dialogs), and `open`. This is gopher64's
  own in-app settings window — batocera never touches it, since configgen
  always launches with a ROM argument and CLI flags. Cross-compiled
  successfully as-is with no extra `Config.in` `select`s beyond what was
  already there (`fontconfig`/`freetype` are already unconditionally
  present in this fork via other packages, so `slint`'s system deps were
  already satisfied); `--no-default-features` was never actually needed.
- CLI: `gopher64 rom.z64 [--fullscreen] [--widescreen] [--overclock]
  [--disable-expansion-pak] [--load-state N] [--ra-username U
  --ra-password P] ...` — boots straight into the game.
- Config: single `config.json` in a config directory resolved via the
  Rust `dirs` crate (`dirs::config_dir().join("gopher64")` on Linux),
  which **honors `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`XDG_CACHE_HOME`** —
  this fork's generator sets those three env vars to redirect into
  `/userdata`, the same idiom `ppssppGenerator.py` already uses
  (`"XDG_CONFIG_HOME": CONFIGS, "XDG_DATA_HOME": SAVES`), rather than
  gopher64's own `portable.txt` mechanism.
- RetroAchievements config: `retroachievements.json` in the config dir —
  `{"username", "token", "enabled", "hardcore", "challenge",
  "leaderboard", "rich_presence"}`. This is a token-file design, not a
  live `--ra-username`/`--ra-password` login — structurally identical to
  `ppssppConfig.py`'s `writeRetroAchievements()`/`ppsspp_retroachievements.dat`
  pattern in this repo, which is what `gopher64Config.py` copies.
- Controllers: identified by `SDL_GetJoystickPathForID` (a device path,
  not a GUID), with per-profile button mappings stored inside
  `config.json` itself (`input.input_profiles`, keyed by profile name;
  `input.input_profile_binding`/`input.controller_assignment` arrays map
  ports 0-3 to a profile + a device path). Different mechanism from the
  `SDL_GAMECONTROLLERCONFIG` env-var trick this repo uses for
  xemu/ppsspp/duckstation.

## Scope decisions (owner's explicit choices, 2026-07-17)

1. **Opt-in only**, not force-selected via `BATOCERA_NINTENDO_SYSTEMS` —
   `BR2_PACKAGE_GOPHER64=y` lives in `configs/batocera-x86_64-arcade.board`
   next to the `LIBRETRO_GEOLITH` opt-in line, same reasoning as Geolith:
   a newer/heavier build chain than this fork has packaged before
   (Cargo + SDL3 + Vulkan + a Slint GUI dependency), so keep blast radius
   small until it's proven to build/run.
2. **RetroAchievements via token file**, not the CLI's live
   `--ra-username`/`--ra-password` login flags — avoids a network login
   call on every single game boot, and reuses the exact same
   `retroachievements`/`retroachievements.username`/`retroachievements.token`/
   `retroachievements.hardcore` global config keys every other emulator's
   RA integration already reads.
3. **Default controller auto-mapping only** — gopher64 ships a built-in
   default Xbox-style N64 mapping (per its wiki) for any pad SDL reports
   as a standard gamepad. `gopher64Generator.py` sets
   `SDL_GAMECONTROLLERCONFIG` (via the existing
   `generate_sdl_game_controller_config()` helper) so batocera's pads are
   recognized as such, but does **not** attempt to translate batocera's
   per-pad config into gopher64's `config.json` `input_profiles` — that's
   a meaningfully bigger effort (device-path-based identification, a
   nontrivial JSON structure) deferred to a future pass if wanted.
4. **`n64` only, not `n64dd`** — the N64 Disk Drive add-on system stays on
   mupen64plus/libretro cores exclusively.

## Files added/changed

- `package/batocera/emulators/gopher64/` — new package: `Config.in`,
  `gopher64.mk` (git checkout w/ submodules, `cargo-package`,
  `host-clang`/`vulkan-loader` deps — no `sdl3`/`sdl3_ttf`, see above),
  `gopher64.emulator.yml` (`custom_features` for widescreen/overclock/
  disable-expansion-pak, `systems: [n64]`), and three source patches
  applied to the extracted upstream tree (`0001`-`0003`, see "Build fixes
  actually needed" below).
- Root `Config.in` — one `source` line for the new package's `Config.in`,
  added next to the `mupen64plus` submenu.
- `configs/batocera-x86_64-arcade.board` — `BR2_PACKAGE_GOPHER64=y` opt-in
  line. (Note: `configs/batocera-x86_64-arcade_defconfig` is a *generated*
  file, produced from the `.board` file by
  `configs/createDefconfig.sh`/the `%-defconfig` Make target — it's
  gitignored (`/configs/batocera-*_defconfig`) and gets silently
  regenerated from the `.board` file, so edit the `.board` file, never the
  `_defconfig` file directly.)
- `package/batocera/emulationstation/batocera-es-system/es_systems.yml` —
  one new `gopher64:` entry under the existing `n64:` block's
  `emulators:` map.
- `package/batocera/core/batocera-configgen/configgen/configgen/generators/gopher64/`
  — new generator module: `gopher64Generator.py` (command + env
  construction), `gopher64Paths.py` (path constants), `gopher64Config.py`
  (RetroAchievements token-file writer). No entry needed in
  `generators/importer.py`'s `_GENERATOR_MAP` — `gopher64` →
  `gopher64/gopher64Generator.py` → `Gopher64Generator` already matches
  the automatic default-naming lookup rule.

## Build fixes actually needed (found only by attempting a real build)

None of these were predictable from reading source alone — each one only
surfaced by running `make x86_64-arcade-pkg PKG=gopher64 BATCH_MODE=1`,
reading the actual failure, and iterating. In order encountered:

1. **rustc version.** gopher64's `Cargo.toml` `rust-version` had already
   moved past what this buildroot's vendored Rust provides
   (`RUST_BIN_VERSION` in `buildroot/package/rust-bin/rust-bin.mk` =
   1.95.0) by the time of implementation. Fixed by pinning
   `GOPHER64_VERSION` to the newest tag that still declares
   `rust-version = "1.95.0"` (checked by fetching `Cargo.toml` from a
   handful of historical tags directly): `v1.1.20`. `v1.1.22` onward
   requires `1.96.0+`. Re-check this whenever bumping the version pin or
   whenever buildroot's own Rust gets upgraded.
2. **`-flto=thin` isn't a GCC flag.** `build.rs` unconditionally passes
   `-flto=thin` (Clang ThinLTO) when compiling the vendored C/C++
   submodules via the `cc` crate; GCC (buildroot's default target
   compiler) rejects it outright. Fixed by pointing just the C/C++ side
   at buildroot's cross-clang (`$(HOST_DIR)/bin/clang`/`clang++`, the
   same binary `duckstation.mk` uses) via `CC`/`CXX` in
   `GOPHER64_CARGO_ENV` — cargo/rustc itself still uses the normal
   gcc-based Rust toolchain/linker. Plain `clang --target=<rust-triple>`
   wasn't enough on its own, since this fork uses buildroot's *internal*
   toolchain (not `BR2_TOOLCHAIN_EXTERNAL`), so the
   `--gcc-install-dir`/config-file mechanism
   `package/llvm-project/clang/clang.mk` sets up for external toolchains
   never runs; `GOPHER64_CC_GCC_INSTALL_DIR`/`GOPHER64_CLANG_CROSS_FLAGS`
   in `gopher64.mk` reproduce the same `--gcc-install-dir`/`--target`/
   `--sysroot` flags by hand.
3. **GNU `ar` can't index LLVM-bitcode archives.** Even with clang
   selected as `CC`, the `cc` crate's archiver auto-detection prefers
   `llvm-ar` for a clang-family compiler; `host-clang` doesn't install
   one, so it silently fell back to something that produced an unindexed
   `libvolk.a` ("archive has no index; run ranlib to add one" at final
   link) — explicitly pinning `AR`/`RANLIB` to buildroot's own cross
   `ar`/`ranlib` didn't fix it either, because the real cause was
   `-flto=thin` producing LLVM-bitcode-only `.o` files that **no**
   GNU-binutils `ar` can index, regardless of which `ar` runs. Fixed by
   dropping the `-flto=thin` flag entirely for the four vendored
   translation units (a source patch, since build.rs hardcodes it with no
   env var or Cargo feature to disable it) — pure optimization, not a
   correctness requirement.
4. **Missing link-time libs/link order**, found in two rounds:
   - `-lvulkan`: parallel-rdp calls a handful of core (non-EXT) `vk*`
     functions directly, not through volk's function-pointer indirection,
     needing an actual link-time Vulkan loader (`vulkan-loader` added to
     `GOPHER64_DEPENDENCIES`).
   - `--start-group`/`--end-group` around `-lvolk -lparallel-rdp
     -lretroachievements`: cargo links these three vendored static libs
     in the same order `build.rs`'s `.compile()` calls happen in
     (`-lvolk` before `-lparallel-rdp`), but `libparallel-rdp.a`'s own
     objects are what reference volk's exported symbols
     (`volkLoadInstance`, `volkInitializeCustom`, the EXT/KHR extension
     trampolines volk.c defines) — GNU `ld` doesn't re-scan an
     already-processed static archive for a later, newly-discovered
     undefined symbol, so without grouping they stayed unresolved.
   - Both were first tried via a blanket `RUSTFLAGS` override in
     `GOPHER64_CARGO_ENV` — **wrong tool**: `RUSTFLAGS` is global to
     every `rustc` invocation in the whole dependency graph, not just
     gopher64's own binary, and broke unrelated dependency crates that
     happen to build their own cdylib (e.g. `sevenz-rust2`) by handing
     them link args pointing at libraries only gopher64's own build.rs
     `OUT_DIR` has. Fixed correctly via `cargo:rustc-link-arg` calls
     added directly to `build.rs` (scoped to just the crate that owns the
     build script), combined into the same patch as the `-flto=thin`
     removal since both touch the same few lines.

**Patch-writing lesson, worth remembering for any future package needing
source patches**: hand-counting unified-diff hunk header line numbers
(`@@ -N,old +N,new @@`) is error-prone and `git apply --check` can
succeed locally on a hunk whose declared counts are subtly wrong in ways
the actual `patch` tool inside the build container then rejects
(`corrupt patch` / `Hunk #1 FAILED`, even though the content is byte-for-
byte correct). The reliable fix: generate patches with a real `diff -u
before after`, never by hand-assembling `+`/`-`/context lines and
guessing the header counts.

## Remaining unconfirmed items (need hands-on testing with a controller
and TV/monitor attached, not just a successful build)

1. Save-file layout under gopher64's `data_dir` (`src/ui/storage.rs`, not
   read in this research pass) — `gopher64Paths.py` namespaces saves under
   `SAVES/n64/gopher64` (separate from mupen64plus's `SAVES/n64`) on the
   assumption formats aren't cross-compatible; unconfirmed.
2. Whether a fresh `config.json` (no prior interactive
   `--configure-input-profile` run) actually auto-populates a working
   default controller profile bound to port 1, or needs a one-time
   `--bind-input-profile`/`--assign-controller` bootstrap — the wiki
   implies the former ("Xbox-style controllers receive automatic default
   mapping") but this is from the GUI/desktop experience, not confirmed
   for a fresh headless config directory.
3. `gopher64`'s `--load-state` takes a numeric slot (0-9), not a file
   path — incompatible with batocera's usual `state_filename` config (a
   full save-state path), so that plumbing was deliberately left out
   rather than guessed at.
4. Actual gameplay/RetroAchievements verification on real hardware
   (correct rendering via KMSDRM+Vulkan, achievements unlocking,
   RetroAchievements token file picked up correctly) — everything
   verified so far is build-time and `es_systems.cfg`/`es_features.cfg`
   generation, not a booted image.
