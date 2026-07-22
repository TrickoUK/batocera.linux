################################################################################
#
# ares
#
# A multi-system emulator (higan/bsnes descendant), packaged here as an extra,
# opt-in standalone emulator choice for several systems that already have a
# default emulator in this fork - see ADD-ARES.md for the full case study,
# the reasoning behind the ARES_CORES trim below, and the list of open items
# that need a real build/launch to confirm (install-tree layout, firmware
# placement, controller mapping).
#
################################################################################

ARES_VERSION = v148
ARES_SITE = $(call github,ares-emulator,ares,$(ARES_VERSION))
ARES_LICENSE = ISC
ARES_LICENSE_FILE = LICENSE
ARES_EMULATOR_INFO = ares.emulator.yml
ARES_DEPENDENCIES += sdl2 alsa-lib pulseaudio qt6base qt6svg

ARES_SUPPORTS_IN_SOURCE_BUILD = NO

ARES_CONF_OPTS += -DCMAKE_BUILD_TYPE=Release
ARES_CONF_OPTS += -DCMAKE_INSTALL_PREFIX=/usr
ARES_CONF_OPTS += -DBUILD_SHARED_LIBS=OFF
ARES_CONF_OPTS += -DUSE_QT6=ON

# NOT setting -DARES_SKIP_DEPS=ON here, unlike the "keep it offline/
# reproducible" instinct every other CMake package in this tree follows -
# see ADD-ARES.md's "librashader: the real remaining blocker" for the full
# story. Short version: ruby's GLX OpenGL video driver unconditionally
# #includes a librashader header and unconditionally links
# librashader::librashader (ruby/cmake/os-linux.cmake's own comment -
# "continue to define the runtime so openGL compiles" - confirms this is
# deliberate upstream design, not a bug), so librashader isn't an optional
# shader-effects nicety on Linux, it's a hard build requirement. ares vendors
# only librashader's *headers* in-tree (thirdparty/librashader/include/) -
# the compiled library itself is expected to already be a real system
# library on Linux/FreeBSD (Findlibrashader.cmake's own per-platform error
# text: Darwin/Windows are told to provide it via ares-deps/CMAKE_PREFIX_PATH,
# Linux/FreeBSD are told "ensure librashader libraries are available in
# local library paths" - i.e. install it yourself). Confirmed directly:
# upstream's own deps.json-driven "ares-deps" prebuilt-dependency fetch (what
# ARES_SKIP_DEPS turns off) only bundles shader *assets*
# (share/libretro/shaders/) on Linux, never a compiled librashader binary -
# so leaving ARES_SKIP_DEPS unset doesn't actually solve this either. This is
# a real, unresolved packaging gap, not a flag to tune: see ADD-ARES.md.

# Trim the build to just the cores this package actually registers systems
# for (see ares.emulator.yml's systems: list) instead of upstream's full
# default list (which also builds Atari 2600, PlayStation, Neo Geo, MSX,
# ColecoVision, MyVision, Game Boy/Color/Advance, WonderSwan, Neo Geo Pocket,
# ZX Spectrum, and SG-1000 support this fork doesn't need from ares - several
# of those systems already have a different default emulator here). Codes
# confirmed directly against upstream's ares/CMakeLists.txt:
#   fc  = NES/Famicom            sfc = SNES/Super Famicom
#   ms  = Master System          md  = Mega Drive family (Mega Drive, Mega CD,
#                                       32X all live under the same "md" core
#                                       subdirectory upstream, not separate
#                                       ARES_CORES entries)
#   pce = PC Engine family (PC Engine, PC Engine CD, SuperGrafx - same "one
#         core covers the whole family" reasoning as md above)
#   n64 = Nintendo 64
# NOTE: CMake list values are semicolon-separated internally, even though
# upstream's own `set(ARES_CORES a26 fc sfc ... CACHE STRING ...)` default
# renders space-joined in any human-readable summary of it - confirmed
# directly against ares/CMakeLists.txt's `list(TRANSFORM ARES_CORES STRIP)`
# + `if(fc IN_LIST ARES_CORES)` checks, which only work against a real
# semicolon-joined list. A space-joined override is silently accepted by
# CMake as a single one-element list (matching zero of the IN_LIST checks)
# rather than erroring - confirmed the hard way by a real build showing
# every single core, including the six below, listed under "Disabled
# Cores" despite this line being present.
ARES_CONF_OPTS += -DARES_CORES="fc;sfc;ms;md;pce;n64"
ARES_CONF_OPTS += -DARES_BUILD_OPTIONAL_TARGETS=OFF

# ares' own build generates a few small resource.cpp/.hpp files (icons etc.)
# via a tiny in-tree host tool, "sourcery" (tools/sourcery/sourcery.cpp - a
# ~70-line, nall-only, no-GUI-deps CLI). Its own CMakeLists.txt
# (tools/sourcery/CMakeLists.txt) only adds it as a *buildable target* when
# NOT cross-compiling; when CMAKE_CROSSCOMPILING is true (always true for a
# Buildroot cmake-package), it instead expects a previously-built native copy
# importable via `sourcery_DIR = <source>/build_native` +
# `find_package(sourcery)` - upstream's own cross-compile CI script
# (.github/scripts/build_windows.sh) confirms this exact "configure+build a
# native copy in build_native/ first" two-pass convention. Reconfiguring the
# *entire* ares tree natively just for this would drag in the same
# GTK3/Qt6/OpenGL/etc. discovery this package's real (cross) configure does -
# fine there since it degrades gracefully to a disabled-feature warning, but
# with no guarantee a natively-runnable Qt6/GTK3 exists in this build
# container in the first place. Sidestepped entirely: the actual build-time
# invocation this whole mechanism feeds into
# (cmake/common/helpers_common.cmake's `add_sourcery_command`) is just a bare
# `COMMAND sourcery resource.bml resource.cpp resource.hpp` - a literal
# `$PATH` lookup, not a CMake target reference - confirmed directly by a real
# build failing with a plain `/bin/sh: 1: sourcery: not found` rather than a
# configure-time error. So: compile sourcery.cpp directly with the *host*
# compiler (bypassing CMake/the cross toolchain entirely - it only needs
# nall's headers) and drop it on $(HOST_DIR)/bin, which is already on PATH
# for the rest of this package's build steps.
define ARES_BUILD_NATIVE_SOURCERY
	mkdir -p $(HOST_DIR)/bin
	$(HOSTCXX) -std=c++20 -O2 -DNALL_HEADER_ONLY \
	    -I$(@D) -I$(@D)/nall \
	    $(@D)/tools/sourcery/sourcery.cpp -o $(HOST_DIR)/bin/sourcery
endef
ARES_PRE_BUILD_HOOKS += ARES_BUILD_NATIVE_SOURCERY

# NEEDS VERIFICATION AT FIRST REAL BUILD: the exact install-tree shape CMake
# produces isn't confirmed against a real build output yet (only against
# upstream's wiki, which documents running "./rundir/bin/ares" relative to
# the build dir - a staged folder that bundles the binary together with
# ares' own resource files: game/BIOS databases, default shaders, etc. that
# it needs alongside the binary, not just the executable itself). Copying
# the whole rundir/ tree (rather than only the binary, the way a simpler
# single-binary package would) is deliberate - re-check this against
# $(@D)/buildroot-build/ after the first `make x86_64-arcade-pkg PKG=ares`
# and adjust the source path/contents if the real layout differs.
define ARES_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/share/ares
	cp -R $(@D)/buildroot-build/rundir/. $(TARGET_DIR)/usr/share/ares/
	rm -f $(TARGET_DIR)/usr/bin/ares
	ln -sf ../share/ares/bin/ares $(TARGET_DIR)/usr/bin/ares
endef

$(eval $(call register,ares.emulator.yml))
$(eval $(cmake-package))
$(eval $(emulator-info-package))
