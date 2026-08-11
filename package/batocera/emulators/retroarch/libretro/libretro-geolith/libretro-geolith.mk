################################################################################
#
# libretro-geolith
#
################################################################################
# Version: Commits on Jul 14, 2026
LIBRETRO_GEOLITH_VERSION = c5b57a6b31b7abef4a8a9b521cae58d653e28154
LIBRETRO_GEOLITH_SITE = $(call github,libretro,geolith-libretro,$(LIBRETRO_GEOLITH_VERSION))
LIBRETRO_GEOLITH_LICENSE = BSD-3-Clause
LIBRETRO_GEOLITH_DEPENDENCIES += retroarch
LIBRETRO_GEOLITH_EMULATOR_INFO = geolith.libretro.core.yml

LIBRETRO_GEOLITH_PLATFORM = $(LIBRETRO_PLATFORM)

define LIBRETRO_GEOLITH_BUILD_CMDS
	$(TARGET_CONFIGURE_OPTS) $(MAKE) CC="$(TARGET_CC)" -C $(@D)/libretro \
	    -f Makefile platform="$(LIBRETRO_GEOLITH_PLATFORM)"
endef

define LIBRETRO_GEOLITH_INSTALL_TARGET_CMDS
	$(INSTALL) -D $(@D)/libretro/geolith_libretro.so \
		$(TARGET_DIR)/usr/lib/libretro/geolith_libretro.so
endef

$(eval $(generic-package))
$(eval $(emulator-info-package))
