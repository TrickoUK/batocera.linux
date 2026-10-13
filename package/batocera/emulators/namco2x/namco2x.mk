################################################################################
#
# namco2x
#
################################################################################
# Version: Release 0.7.0 on Oct 10, 2026
#
# Prebuilt on purpose: each game's master-DSP and sound programs are translated
# to C from the MAME ROM set at *build* time (tools/gen/c25_translate.py,
# snd_translate.py), so a source build would need the ROMs on the build host.
# The release .deb already carries the compiled binaries.
NAMCO2X_VERSION = 0.7.0
NAMCO2X_SOURCE = namco-2x-systems_$(NAMCO2X_VERSION)_amd64.deb
NAMCO2X_SITE = \
    https://github.com/spacestate1/namco22-decompile/releases/download/$(NAMCO2X_VERSION)
NAMCO2X_LICENSE = MIT
NAMCO2X_EMULATOR_INFO = namco2x.emulator.yml

NAMCO2X_DEPENDENCIES = sdl2 zlib
NAMCO2X_EXTRACT_DEPENDENCIES = host-zstd

# binaries to ship, one per supported game (the generator maps rom -> binary)
NAMCO2X_BINARIES = tc rr ad dd tc2 tw cc propcycl cs21

define NAMCO2X_EXTRACT_CMDS
	mkdir -p $(@D)/deb
	cd $(@D)/deb && $(HOSTAR) x $(NAMCO2X_DL_DIR)/$(NAMCO2X_SOURCE)
	$(HOST_DIR)/bin/zstd -dc $(@D)/deb/data.tar.zst | $(TAR) -x -C $(@D)
endef

define NAMCO2X_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/lib/namco2x
	$(foreach bin,$(NAMCO2X_BINARIES), \
	    $(INSTALL) -m 0755 $(@D)/usr/lib/namco-2x-systems/$(bin) \
	        $(TARGET_DIR)/usr/lib/namco2x/$(bin)$(sep))
	$(INSTALL) -D -m 0644 $(@D)/usr/share/doc/namco-2x-systems/LICENSE \
	    $(TARGET_DIR)/usr/share/namco2x/LICENSE
	# gun BTN_1 (Sinden rear right) -> the coin key; the engine only reads the
	# gun's left/right/middle buttons through the SDL mouse
	$(INSTALL) -D -m 0644 $(NAMCO2X_PKGDIR)/namco22.namco2x.keys \
	    $(TARGET_DIR)/usr/share/evmapy/namco22.namco2x.keys
endef

$(eval $(generic-package))
$(eval $(emulator-info-package))
