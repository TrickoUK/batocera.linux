################################################################################
#
# libretro-supermodel
#
################################################################################
# Version: Commits on Aug 22, 2026
LIBRETRO_SUPERMODEL_VERSION = 9f0a51daf6cef6ec2a304538f18c6dbb4c4b9da2
LIBRETRO_SUPERMODEL_SITE = $(call github,libretro,Libretro-Supermodel,$(LIBRETRO_SUPERMODEL_VERSION))
LIBRETRO_SUPERMODEL_LICENSE = GPL-3.0+
LIBRETRO_SUPERMODEL_LICENSE_FILES = Docs/LICENSE.txt
LIBRETRO_SUPERMODEL_DEPENDENCIES += retroarch zlib
LIBRETRO_SUPERMODEL_EMULATOR_INFO = supermodel.libretro.core.yml

LIBRETRO_SUPERMODEL_PLATFORM = $(LIBRETRO_PLATFORM)

# - The Makefile regenerates Bundled{GamesXml,SupermodelIni}.h with xxd whenever
#   Config/*.{xml,ini} looks newer than the (git-tracked) header. The build
#   container has no xxd, so mark the tracked headers up to date instead.
# - CROSS_COMPILE only has to be non-empty: an empty one makes the Makefile add
#   -I/usr/include, i.e. the host's headers, to a cross build.
# - GIT_VERSION would otherwise come from `git rev-parse` in whatever checkout
#   the build directory happens to sit in.
define LIBRETRO_SUPERMODEL_BUILD_CMDS
	touch $(@D)/Src/OSD/libretro/BundledGamesXml.h \
	      $(@D)/Src/OSD/libretro/BundledSupermodelIni.h
	$(TARGET_CONFIGURE_OPTS) $(MAKE) -C $(@D) -f Makefile \
	    platform="$(LIBRETRO_SUPERMODEL_PLATFORM)" \
	    CROSS_COMPILE="$(TARGET_CROSS)" \
	    GIT_VERSION="-$(shell echo $(LIBRETRO_SUPERMODEL_VERSION) | cut -c 1-7)"
endef

# The core's own .info is newer than the libretro-core-info snapshot pinned in
# this tree; without it batocera-launch refuses to start the core.
define LIBRETRO_SUPERMODEL_INSTALL_TARGET_CMDS
	$(INSTALL) -D $(@D)/supermodel_libretro.so \
	    $(TARGET_DIR)/usr/lib/libretro/supermodel_libretro.so
	$(INSTALL) -D -m 0644 $(@D)/supermodel_libretro.info \
	    $(TARGET_DIR)/usr/share/libretro/info/supermodel_libretro.info
endef

$(eval $(generic-package))
$(eval $(emulator-info-package))
