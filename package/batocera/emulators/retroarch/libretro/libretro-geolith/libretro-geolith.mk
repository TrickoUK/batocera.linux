################################################################################
#
# libretro-geolith
#
################################################################################
# Version: Commits on Sep 14, 2026
LIBRETRO_GEOLITH_VERSION = 194024931935eff2092e36fc4f8e53e62ed11097
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
