################################################################################
#
# ares
#
################################################################################
# Version: Commits on Jul 31, 2026
ARES_VERSION = b80f67d38312648d197762121c3a27b02c0887db
ARES_SITE = https://github.com/ares-emulator/ares
ARES_SITE_METHOD = git
ARES_LICENSE = ISC (ares core), multiple (bundled third-party components, see LICENSE)
ARES_LICENSE_FILES = LICENSE
ARES_SUPPORTS_IN_SOURCE_BUILD = NO

ARES_DEPENDENCIES = libgtk3 sdl3 xlib_libX11 xlib_libXrandr librashader

# ares cross-builds a small in-tree resource compiler ("sourcery") that its
# main CMake build invokes via a bare `sourcery` PATH lookup during the
# build (cmake/common/helpers_common.cmake), not via a CMake target
# reference. Upstream's own documented fix (a second, fully native CMake
# configure/build of the whole tree) assumes a native toolchain with every
# GUI dependency available, which a Buildroot container doesn't have.
# Instead, build just the handful of files sourcery actually needs
# (itself + the parts of "nall" and the vendored "sljit" it pulls in)
# directly with the host compiler and drop the result on $(HOST_DIR)/bin,
# which is already on PATH for the rest of the (cross) build.
define ARES_BUILD_HOST_SOURCERY
	mkdir -p $(@D)/build_native
	$(HOSTCC) -O2 -c $(@D)/thirdparty/sljit/sljit_src/sljitLir.c \
		-I$(@D)/thirdparty \
		-DSLJIT_HAVE_CONFIG_PRE=1 -DSLJIT_HAVE_CONFIG_POST=1 \
		-o $(@D)/build_native/sljitLir.o
	$(HOSTCXX) -std=c++23 -O2 -I$(@D)/nall -I$(@D)/thirdparty \
		-DSLJIT_HAVE_CONFIG_PRE=1 -DSLJIT_HAVE_CONFIG_POST=1 \
		$(@D)/tools/sourcery/sourcery.cpp \
		$(@D)/nall/nall/main.cpp \
		$(@D)/nall/nall/nall.cpp \
		$(@D)/nall/nall/sljitAllocator.cpp \
		$(@D)/build_native/sljitLir.o \
		-lpthread -o $(HOST_DIR)/bin/sourcery
	mkdir -p $(@D)/build_native
	echo 'if(NOT TARGET sourcery)' > $(@D)/build_native/sourceryConfig.cmake
	echo '  add_executable(sourcery IMPORTED GLOBAL)' >> $(@D)/build_native/sourceryConfig.cmake
	echo '  set_target_properties(sourcery PROPERTIES IMPORTED_LOCATION "$(HOST_DIR)/bin/sourcery")' >> $(@D)/build_native/sourceryConfig.cmake
	echo 'endif()' >> $(@D)/build_native/sourceryConfig.cmake
endef

ARES_PRE_CONFIGURE_HOOKS += ARES_BUILD_HOST_SOURCERY

# Semicolon-separated CMake list, not space-separated (ARES_CORES is
# consumed via CMake's IN_LIST/foreach, which is picky about this) -
# scoped to n64 (Nintendo 64) and sfc (Super Famicom/SNES) only.
ARES_CONF_OPTS  = -DCMAKE_BUILD_TYPE=Release
ARES_CONF_OPTS += -DARES_CORES="n64;sfc"
ARES_CONF_OPTS += -DARES_ENABLE_LIBRASHADER=ON
# Findlibrashader.cmake's own find_path()/find_library() don't reliably
# locate a real install in this cross-configure (confirmed the hard way
# with the vendored-header fallback case, which failed the same way even
# though the hint should have worked) - pre-seed both cache variables it
# searches for so they short-circuit successfully rather than chase why.
ARES_CONF_OPTS += -Dlibrashader_INCLUDE_DIR=$(STAGING_DIR)/usr/include/librashader
ARES_CONF_OPTS += -Dlibrashader_LIBRARY=$(STAGING_DIR)/usr/lib/librashader.so
ARES_CONF_OPTS += -DARES_BUILD_LOCAL=OFF
ARES_CONF_OPTS += -DARES_ENABLE_MINIMUM_CPU=ON
ARES_CONF_OPTS += -DARES_BUILD_OPTIONAL_TARGETS=OFF
ARES_CONF_OPTS += -DUSE_QT6=OFF
ARES_CONF_OPTS += -DARES_CROSSCOMPILING=ON

$(eval $(cmake-package))
$(eval $(call register,ares.emulator.yml))
$(eval $(emulator-info-package))
