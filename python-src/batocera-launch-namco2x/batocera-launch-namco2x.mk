################################################################################
#
# batocera-launch-namco2x
#
################################################################################

BATOCERA_LAUNCH_NAMCO2X_SETUP_TYPE=hatch
BATOCERA_LAUNCH_NAMCO2X_DEPENDENCIES = \
	python-batocera-common \
	batocera-launch

$(eval $(local-python-package))
