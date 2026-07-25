################################################################################
#
# libretro-ps2
#
################################################################################
# Version: Commits on June 29, 2026
LIBRETRO_PS2_VERSION = b03969a333f38de21f866c2a10da4300d170364d
LIBRETRO_PS2_SITE = https://github.com/libretro/ps2.git
LIBRETRO_PS2_SITE_METHOD = git
LIBRETRO_PS2_GIT_SUBMODULES = YES
LIBRETRO_PS2_LICENSE = GPLv2
LIBRETRO_PS2_DEPENDENCIES = libaio xz host-xxd retroarch
LIBRETRO_PS2_EMULATOR_INFO = pcsx2.libretro.core.yml
LIBRETRO_PS2_SUPPORTS_IN_SOURCE_BUILD = NO

LIBRETRO_PS2_CONF_OPTS += -DCMAKE_BUILD_TYPE=Release
LIBRETRO_PS2_CONF_OPTS += -DBUILD_SHARED_LIBS=OFF
LIBRETRO_PS2_CONF_OPTS += -DLIBRETRO=ON
LIBRETRO_PS2_CONF_OPTS += -DBUILD_REGRESS=OFF
LIBRETRO_PS2_CONF_OPTS += -DBUILD_TOOLS=OFF
LIBRETRO_PS2_CONF_OPTS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5
# Multi-ISA runtime SIMD dispatch links per-tier (sse4/avx/avx2) static libs via
# CMake's $<LINK_LIBRARY:WHOLE_ARCHIVE,...>, which the Unix Makefiles generator
# does not support for the CXX link language (fails the CMake generate step
# regardless of CMake version). We target a single known CPU baseline, so keep
# the old single-build path instead of upstream's new default.
LIBRETRO_PS2_CONF_OPTS += -DDISABLE_ADVANCE_SIMD=OFF

ifeq ($(BR2_PACKAGE_HAS_LIBGL),y)
    LIBRETRO_PS2_CONF_OPTS += -DUSE_OPENGL=ON
else
    LIBRETRO_PS2_CONF_OPTS += -DUSE_OPENGL=OFF
endif

ifeq ($(BR2_PACKAGE_BATOCERA_VULKAN),y)
    LIBRETRO_PS2_CONF_OPTS += -DUSE_VULKAN=ON
else
    LIBRETRO_PS2_CONF_OPTS += -DUSE_VULKAN=OFF
endif

define LIBRETRO_PS2_INSTALL_TARGET_CMDS
	$(INSTALL) -D $(@D)/buildroot-build/bin/pcsx2_libretro.so \
		$(TARGET_DIR)/usr/lib/libretro/pcsx2_libretro.so
    mkdir -p $(TARGET_DIR)/usr/share/batocera/datainit/bios/pcsx2/resources
    cp -f $(@D)/bin/resources/GameIndex.yaml \
        $(TARGET_DIR)/usr/share/batocera/datainit/bios/pcsx2/resources
endef

$(eval $(cmake-package))
$(eval $(emulator-info-package))