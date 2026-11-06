STARSHIP_VERSION = 1.27.0
STARSHIP_SITE = https://github.com/starship/starship/releases/download/v$(STARSHIP_VERSION)
STARSHIP_SOURCE = starship-arm-unknown-linux-musleabihf.tar.gz
STARSHIP_LICENSE = ISC
STARSHIP_LICENSE_FILES = LICENSE

define STARSHIP_EXTRACT_CMDS
 $(TAR) -xzf $(STARSHIP_DL_DIR)/$(STARSHIP_SOURCE) -C $(@D)
 $(INSTALL) -m 0644 $(BR2_EXTERNAL_DIAMOND3_PATH)/package/starship/LICENSE $(@D)/LICENSE
endef

define STARSHIP_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/starship $(TARGET_DIR)/usr/bin/starship
 $(INSTALL) -D -m 0644 $(@D)/LICENSE $(TARGET_DIR)/usr/share/licenses/starship/LICENSE
endef

$(eval $(generic-package))
