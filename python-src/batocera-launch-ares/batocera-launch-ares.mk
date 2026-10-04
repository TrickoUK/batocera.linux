################################################################################
#
# batocera-launch-ares
#
################################################################################

BATOCERA_LAUNCH_ARES_SETUP_TYPE=hatch
BATOCERA_LAUNCH_ARES_DEPENDENCIES = \
	python-batocera-common \
	batocera-launch

$(eval $(local-python-package))
