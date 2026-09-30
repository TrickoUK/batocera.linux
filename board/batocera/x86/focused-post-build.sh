#!/bin/bash -e

# Post-build hook for this fork's AMD-only focused boards. Runs upstream's
# post-build script unchanged, then prunes firmware for hardware these boards
# never target (no Nvidia driver, no Intel GPU/audio). Kept as a separate
# script, wired in from the board files, so no upstream file needs patching.
# Intel wifi (iwlwifi) and Bluetooth (ibt-*) firmware is deliberately kept:
# those cards are common in AMD machines. radeon/ is kept for old Radeon GPUs.

"$(dirname "$0")/../scripts/post-build-script.sh" "$@"

FW="${TARGET_DIR}/lib/firmware"
rm -rf \
    "${FW}/nvidia" "${FW}/i915" "${FW}/xe" \
    "${FW}"/intel/sof* "${FW}/intel/avs" "${FW}/intel/catpt" "${FW}/intel/ish"
