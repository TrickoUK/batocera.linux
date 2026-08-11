################################################################################
#
# librashader
#
################################################################################
# Version: Commits on Jul 5, 2026
LIBRASHADER_VERSION = 87e8a97b50516d997defeaa168173dcd185d4022
LIBRASHADER_SITE = $(call github,SnowflakePowered,librashader,$(LIBRASHADER_VERSION))
LIBRASHADER_LICENSE = MPL-2.0 OR GPL-3.0-only
LIBRASHADER_LICENSE_FILES = LICENSE.md LICENSE-GPL.md
LIBRASHADER_INSTALL_STAGING = YES
LIBRASHADER_DEPENDENCIES = host-patchelf

# librashader ships its own build-orchestration crate (librashader-build-script,
# a thin wrapper around `cargo build -p librashader-capi`) rather than using
# cargo-c - this is the exact recipe upstream's own Fedora/OBS packaging uses
# (pkg/librashader.spec), not something invented here. Only the OpenGL
# runtime is needed - ares' Linux "ruby" video-presentation layer is the only
# consumer, and it's GLX/OpenGL-only (its Vulkan-rendered N64 core composites
# through that same outer OpenGL layer, not a separate librashader Vulkan
# runtime).
#
# The build-orchestration crate itself must run natively (it shells out to a
# *second*, cross-compiling `cargo build` internally, driven by its own
# --target flag) - so CARGO_BUILD_TARGET needs to not apply to this
# invocation, overriding what $(PKG_CARGO_ENV) sets for normal
# (single-cargo-call) Rust packages. Setting it to an empty string
# (CARGO_BUILD_TARGET=) does NOT do that - cargo treats an empty value as
# an explicit (invalid) target, failing with "error: target was empty" -
# it has to be genuinely unset via `env -u`. Everything else in
# $(PKG_CARGO_ENV) (the cross linker env var in particular) stays: it's
# named after the specific target triple, so it's inert for this native
# build and picked up by the nested cross build.
define LIBRASHADER_BUILD_CMDS
	cd $(@D) && $(TARGET_MAKE_ENV) $(PKG_CARGO_ENV) \
		env -u CARGO_BUILD_TARGET \
		cargo run --offline --locked -p librashader-build-script -- \
			--profile optimized --target=$(RUSTC_TARGET_NAME) \
			-- --no-default-features --features runtime-opengl
	# cargo's raw cdylib output has no SONAME, so anything linking against
	# it (found via an absolute build-time path, e.g. ares' CMake
	# find_library() result) bakes that literal path into its own
	# DT_NEEDED entry instead of a bare "librashader.so.2" - harmless at
	# build time, but a runtime linker failure on the actual target device,
	# where that build path doesn't exist. Matches upstream's own install
	# recipe (pkg/librashader.spec): patch the SONAME in before anything
	# links against this file.
	$(HOST_DIR)/bin/patchelf --set-soname librashader.so.2 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/optimized/librashader.so
endef

# librashader.so.2 is the real file (SONAME-patched above); librashader.so
# is an unversioned symlink to it - ares' runtime dlopen("librashader.so")
# only ever asks for the unversioned name, resolved via the symlink like
# any other shared library.
define LIBRASHADER_INSTALL_STAGING_CMDS
	$(INSTALL) -D -m 0755 $(@D)/target/$(RUSTC_TARGET_NAME)/optimized/librashader.so \
		$(STAGING_DIR)/usr/lib/librashader.so.2
	ln -sf librashader.so.2 $(STAGING_DIR)/usr/lib/librashader.so
	$(INSTALL) -D -m 0644 $(@D)/include/librashader.h \
		$(STAGING_DIR)/usr/include/librashader/librashader.h
	$(INSTALL) -D -m 0644 $(@D)/include/librashader_ld.h \
		$(STAGING_DIR)/usr/include/librashader/librashader_ld.h
endef

define LIBRASHADER_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/target/$(RUSTC_TARGET_NAME)/optimized/librashader.so \
		$(TARGET_DIR)/usr/lib/librashader.so.2
	ln -sf librashader.so.2 $(TARGET_DIR)/usr/lib/librashader.so
endef

$(eval $(cargo-package))
