BTOP_VERSION = 1.4.8
BTOP_SITE = https://github.com/aristocratos/btop/releases/download/v$(BTOP_VERSION)
BTOP_SOURCE = btop-armv7-unknown-linux-musleabi.tar.gz
BTOP_LICENSE = Apache-2.0
BTOP_LICENSE_FILES = LICENSE

define BTOP_EXTRACT_CMDS
 $(TAR) -xzf $(BTOP_DL_DIR)/$(BTOP_SOURCE) -C $(@D) --strip-components=2
endef

define BTOP_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/bin/btop $(TARGET_DIR)/usr/bin/btop
 mkdir -p $(TARGET_DIR)/usr/share/btop
 cp -a $(@D)/themes $(TARGET_DIR)/usr/share/btop/
 $(INSTALL) -D -m 0644 $(@D)/LICENSE $(TARGET_DIR)/usr/share/licenses/btop/LICENSE
endef

$(eval $(generic-package))
