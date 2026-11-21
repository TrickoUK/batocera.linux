################################################################################
#
# wine-x86
#
################################################################################

# Fork: pinned to the published "44-dev" tarball. Upstream's system version moved
# to 45-dev (2026-11-17) but batocera-linux/wine-x86 has no 45-dev release yet (404).
WINE_X86_VERSION = 44-dev
WINE_X86_SOURCE = wine-x86-$(WINE_X86_VERSION).tar.lzma
WINE_X86_SITE = \
    https://github.com/batocera-linux/wine-x86/releases/download/$(WINE_X86_VERSION)

define WINE_X86_EXTRACT_CMDS
	mkdir -p $(@D)/target && cd $(@D)/target && \
	    tar xf $(DL_DIR)/$(WINE_X86_DL_SUBDIR)/$(WINE_X86_SOURCE)
endef

define WINE_X86_INSTALL_TARGET_CMDS
	cp -prf $(@D)/target/* $(TARGET_DIR)
endef

$(eval $(generic-package))
