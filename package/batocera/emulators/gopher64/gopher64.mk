################################################################################
#
# gopher64
#
################################################################################

# Pinned to the newest tag whose Cargo.toml rust-version (1.95.0) this
# buildroot's toolchain still satisfies (RUST_BIN_VERSION in
# buildroot/package/rust-bin/rust-bin.mk) - v1.1.22 onward requires
# rustc 1.96.0+. Bump this (and re-check rust-version) whenever
# buildroot's own Rust gets upgraded.
GOPHER64_VERSION = v1.1.20
GOPHER64_SITE = https://github.com/gopher64/gopher64.git
GOPHER64_SITE_METHOD = git
# Real git submodules (parallel-rdp-standalone, sse2neon, rcheevos) built
# directly by build.rs via the `cc` crate - a github tarball checkout
# would silently omit these, so this must stay a git checkout, not
# $(call github,...).
GOPHER64_GIT_SUBMODULES = YES
GOPHER64_LICENSE = GPLv3
GOPHER64_EMULATOR_INFO = gopher64.emulator.yml

# host-clang: build.rs uses `bindgen` (via clang-sys) to generate FFI
# bindings for the vendored parallel-rdp/rcheevos C/C++ submodules; this
# needs libclang available on the host at build time, same reason
# duckstation and buildroot's own rust-bindgen package depend on it.
#
# No batocera `sdl3`/`sdl3_ttf` package dependency: gopher64's Cargo.toml
# pins sdl3-sys/sdl3-ttf-sys to `features = ["build-from-source-static"]`
# - it always vendors and statically links its own copy of SDL3 from
# source (version pinned in Cargo.lock), never linking against this
# fork's own SDL3 build at all. Depending on the batocera `sdl3` package
# here would just build an unused second copy.
#
# vulkan-loader: parallel-rdp calls several vkGetPhysicalDevice*/
# vkGetPhysicalDeviceSurface* functions directly (not just through volk's
# dynamically-loaded function pointers), which need an actual link-time
# `-lvulkan` (see GOPHER64_CARGO_ENV below).
GOPHER64_DEPENDENCIES = host-rustc host-rust-bin host-clang vulkan-loader

# build.rs compiles its vendored C/C++ submodules (parallel-rdp, volk,
# rcheevos) via the `cc` crate, and unconditionally passes -flto=thin
# (Clang-only ThinLTO) - GCC (buildroot's default target compiler)
# rejects that flag outright ("unrecognized argument to '-flto=' option:
# 'thin'"). Point just the C/C++ side at buildroot's cross-clang instead,
# the same binary duckstation.mk uses
# (-DCMAKE_C_COMPILER=$(HOST_DIR)/bin/clang); cargo/rustc itself still
# uses the normal gcc-based Rust toolchain/linker.
#
# Plain `clang --target=<rust-triple>` isn't enough on its own: this
# fork uses buildroot's internal toolchain (not BR2_TOOLCHAIN_EXTERNAL),
# so the auto-generated --gcc-install-dir config file
# package/llvm-project/clang/clang.mk sets up for external toolchains
# never gets written, and clang can't find crtbeginS.o/-lgcc without it
# ("cannot find crtbeginS.o", "cannot find -lgcc"). Reproduce the same
# --gcc-install-dir/--target/--sysroot flags by hand instead, computed
# the same way that config file does.
GOPHER64_CC_GCC_INSTALL_DIR = $(shell $(TARGET_CC) -print-search-dirs | awk -F ': ' '$$1=="install" {print $$2}')
GOPHER64_CLANG_CROSS_FLAGS = --target=$(GNU_TARGET_NAME) --gcc-install-dir=$(GOPHER64_CC_GCC_INSTALL_DIR) --sysroot=$(STAGING_DIR)

# The `cc` crate auto-prefers `llvm-ar` for archiving objects it built
# with a clang-family CC, but buildroot's `host-clang` package doesn't
# install an `llvm-ar` alongside `clang`/`clang++`, so it silently fell
# through to some other `ar` that produced an unindexed archive
# ("libvolk.a: error adding symbols: archive has no index; run ranlib to
# add one" at the final link step). Pin AR/RANLIB explicitly to
# buildroot's own cross ar/ranlib (perfectly fine to mix with a
# clang-compiled .o - ar/ranlib don't care which compiler produced them).
#
# The extra -lvulkan/--start-group linker args needed to resolve volk's
# and parallel-rdp's symbols are added via a patch to build.rs itself
# (0003-build-rs-drop-flto-thin.patch, using cargo:rustc-link-arg) rather
# than RUSTFLAGS here: RUSTFLAGS is global to every crate rustc invokes
# in the whole dependency graph, not just gopher64's own binary, and
# broke unrelated dependency crates that happen to build their own
# cdylib (e.g. sevenz-rust2) by handing them link args pointing at
# libraries only gopher64's own build.rs output directory has.
GOPHER64_CARGO_ENV = \
	CC=$(HOST_DIR)/bin/clang \
	CXX=$(HOST_DIR)/bin/clang++ \
	AR=$(TARGET_AR) \
	RANLIB=$(TARGET_RANLIB) \
	CFLAGS="$(TARGET_CFLAGS) $(GOPHER64_CLANG_CROSS_FLAGS)" \
	CXXFLAGS="$(TARGET_CXXFLAGS) $(GOPHER64_CLANG_CROSS_FLAGS)"

# The default cargo-package BUILD/INSTALL_TARGET_CMDS (cargo build/install
# --path ./ --bins) is sufficient here: gopher64's Cargo.toml is a plain
# (non-workspace) manifest with an implicit `gopher64` binary target from
# src/main.rs, so no custom install step is needed (contrast with ruffle,
# whose actual binary lives in a workspace member subdirectory).

$(eval $(cargo-package))
$(eval $(emulator-info-package))
