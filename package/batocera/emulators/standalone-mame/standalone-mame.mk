################################################################################
#
# standalone-mame (real upstream mamedev/mame)
#
# Second standalone (non-libretro) MAME binary, distinct from
# package/batocera/emulators/mame (which is GroovyMAME, not stock MAME - see
# that package's mame.mk). Installed to a separate path
# ($(TARGET_DIR)/usr/bin/standalone-mame/) so the two never collide.
#
# As of this writing, upstream's latest stable tag (mame0288) happens to be
# the exact version GroovyMAME's gm0288sr222d base is forked from, and still
# uses the same GENie/`makefile`-driven build (no CMakeLists.txt at the repo
# root) - so this largely mirrors mame.mk's build logic rather than
# reinventing it. Re-verify this parity next time STANDALONE_MAME_VERSION is
# bumped: upstream MAME's build system is not guaranteed to stay GENie-based
# forever.
#
################################################################################
STANDALONE_MAME_VERSION = mame0288
STANDALONE_MAME_SITE = $(call github,mamedev,mame,$(STANDALONE_MAME_VERSION))
STANDALONE_MAME_DEPENDENCIES += alsa-lib expat flac fontconfig glm jpeg libpng
STANDALONE_MAME_DEPENDENCIES += pugixml pulseaudio rapidjson sdl2 sdl2_ttf sqlite utf8proc zlib zstd

$(eval $(call register,standalone-mame.emulator.yml))

STANDALONE_MAME_LICENSE = MAME

STANDALONE_MAME_CROSS_OPTS = PRECOMPILE=0 NO_USE_PORTAUDIO=1
STANDALONE_MAME_CFLAGS =
STANDALONE_MAME_LDFLAGS =

# Limit number of jobs not to eat too much RAM - MAME's individual driver
# translation units are enormous regardless of fork/version.
total_memory_kb := $(shell grep MemTotal /proc/meminfo | awk '{print $$2}')
memory_based_jobs := $(shell echo $$(( $(total_memory_kb) / 1024 / 1024 / 2 + 1)))
cpu_threads := $(shell nproc)
jobs := $(shell echo $$(( $(memory_based_jobs) < $(cpu_threads) ? $(memory_based_jobs) : $(cpu_threads) )))
STANDALONE_MAME_JOBS := $(jobs)

# This fork only targets x86_64 - PTR64/desktop X11+OpenGL path only, no
# ARM/RISC-V CFLAGS ladder (compare against mame.mk's much longer version,
# which supports this fork's non-x86_64 boards too).
STANDALONE_MAME_CROSS_ARCH = x86_64
STANDALONE_MAME_CROSS_OPTS += PTR64=1 PLATFORM=x86
STANDALONE_MAME_ARCH = linux_x64

# Pipewire
ifeq ($(BR2_PACKAGE_PIPEWIRE),y)
STANDALONE_MAME_DEPENDENCIES += pipewire
STANDALONE_MAME_CROSS_OPTS += NO_USE_PIPEWIRE=0
STANDALONE_MAME_CFLAGS += -I$(STAGING_DIR)/usr/include/pipewire-0.3 -I$(STAGING_DIR)/usr/include/spa-0.2
else
STANDALONE_MAME_CROSS_OPTS += NO_USE_PIPEWIRE=1
endif

# Wayland
ifeq ($(BR2_PACKAGE_BATOCERA_WAYLAND),y)
STANDALONE_MAME_CROSS_OPTS += USE_WAYLAND=1
else
STANDALONE_MAME_CROSS_OPTS += USE_WAYLAND=0
endif

define STANDALONE_MAME_GENIE
	+cd $(@D) ; \
	PATH="$(HOST_DIR)/bin:$$PATH" \
	$(MAKE) TARGETOS=linux OSD=sdl genie \
	TARGET=mame SUBTARGET=tiny \
	NO_USE_PORTAUDIO=1 NO_X11=1 USE_SDL=1 \
	USE_QTDEBUG=0 DEBUG=0 IGNORE_GIT=1 MPARAM=""
endef

STANDALONE_MAME_PRE_BUILD_HOOKS += STANDALONE_MAME_GENIE

define STANDALONE_MAME_BUILD_CMDS
	+cd $(@D) ; \
	PATH="$(HOST_DIR)/bin:$$PATH" \
	SYSROOT="$(STAGING_DIR)" \
	CFLAGS="--sysroot=$(STAGING_DIR) $(STANDALONE_MAME_CFLAGS) -fpch-preprocess" \
	LDFLAGS="--sysroot=$(STAGING_DIR) $(STANDALONE_MAME_LDFLAGS) -L$(STAGING_DIR)/usr/lib" \
	LIBS="-lz -lzstd -lFLAC -l7z" \
	PKG_CONFIG="$(HOST_DIR)/usr/bin/pkg-config --define-prefix" \
	PKG_CONFIG_PATH="$(STAGING_DIR)/usr/lib/pkgconfig" \
	CCACHE_SLOPPINESS="pch_defines,time_macros" \
	$(MAKE) -j$(STANDALONE_MAME_JOBS) -l$(STANDALONE_MAME_JOBS) $(STANDALONE_MAME_ARCH) \
	TARGETOS=linux OSD=sdl \
	TARGET=mame \
	SUBTARGET=mame \
	OVERRIDE_CC="$(TARGET_CC)" \
	OVERRIDE_CXX="$(TARGET_CXX)" \
	OVERRIDE_LD="$(TARGET_LD)" \
	OVERRIDE_AR="$(TARGET_AR)" \
	OVERRIDE_STRIP="$(TARGET_STRIP)" \
	CROSS_BUILD=1 \
	CROSS_ARCH="$(STANDALONE_MAME_CROSS_ARCH)" \
	$(STANDALONE_MAME_CROSS_OPTS) \
	NO_USE_PORTAUDIO=1 \
	USE_SYSTEM_LIB_ZLIB=1 \
	USE_SYSTEM_LIB_JPEG=1 \
	USE_SYSTEM_LIB_FLAC=1 \
	USE_SYSTEM_LIB_SQLITE3=1 \
	USE_SYSTEM_LIB_RAPIDJSON=1 \
	USE_SYSTEM_LIB_EXPAT=1 \
	USE_SYSTEM_LIB_GLM=1 \
	USE_SYSTEM_LIB_ZSTD=1 \
	USE_SYSTEM_LIB_PUGIXML=1 \
	USE_SYSTEM_LIB_UTF8PROC=1 \
	OPENMP=1 \
	SDL_INSTALL_ROOT="$(STAGING_DIR)/usr" USE_LIBSDL=1 \
	USE_QTDEBUG=0 DEBUG=0 IGNORE_GIT=1 \
	REGENIE=1 \
	LDOPTS="-lasound -lfontconfig" \
	SYMBOLS=0 \
	STRIP_SYMBOLS=1 \
	TOOLS=0 \
	CXXFLAGS="$(TARGET_CXXFLAGS) -Wno-unknown-pragmas"
endef

define STANDALONE_MAME_INSTALL_TARGET_CMDS
	# Create specific directories on target to store the standalone-mame distro
	mkdir -p $(TARGET_DIR)/usr/bin/standalone-mame/
	mkdir -p $(TARGET_DIR)/usr/bin/standalone-mame/hash
	mkdir -p $(TARGET_DIR)/usr/bin/standalone-mame/ini/examples
	mkdir -p $(TARGET_DIR)/usr/bin/standalone-mame/ini/presets
	mkdir -p $(TARGET_DIR)/usr/bin/standalone-mame/language
	mkdir -p $(TARGET_DIR)/usr/bin/standalone-mame/roms

	# Install binary and default distro
	$(INSTALL) -D $(@D)/mame		$(TARGET_DIR)/usr/bin/standalone-mame/mame
	cp $(@D)/COPYING			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp $(@D)/README.md			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp $(@D)/uismall.bdf			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/artwork			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/bgfx			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/hash			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/hlsl			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/ini				$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/keymaps			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/language			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R -u $(@D)/plugins			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/roms			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/samples			$(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(@D)/web				$(TARGET_DIR)/usr/bin/standalone-mame/

	# Delete .po translation files
	find $(TARGET_DIR)/usr/bin/standalone-mame/language -name "*.po" -type f -delete

	# Delete bgfx shaders for DX9/DX11/Metal
	rm -Rf $(TARGET_DIR)/usr/bin/standalone-mame/bgfx/shaders/metal/
	rm -Rf $(TARGET_DIR)/usr/bin/standalone-mame/bgfx/shaders/dx11/

	# Reuse batocera's own coindrop Lua plugin from the groovy-mame package
	# (batocera-authored, not part of upstream MAME's plugins/ dir) instead
	# of duplicating it into this package - referenced read-only, does not
	# modify package/batocera/emulators/mame in any way.
	cp -R -u $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/emulators/mame/coindrop \
	    $(TARGET_DIR)/usr/bin/standalone-mame/plugins

	# Data plugin information (batocera-authored dats/history content, same
	# reuse rationale as coindrop above)
	cp -R $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/emulators/mame/dats \
	    $(TARGET_DIR)/usr/bin/standalone-mame/
	cp -R $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/emulators/mame/history \
	    $(TARGET_DIR)/usr/bin/standalone-mame/
endef

$(eval $(generic-package))
$(eval $(emulator-info-package))
