DIAMOND3_BOARD_VERSION = 1
DIAMOND3_BOARD_SITE = $(BR2_EXTERNAL_DIAMOND3_PATH)/package/diamond3-board/src
DIAMOND3_BOARD_SITE_METHOD = local
DIAMOND3_BOARD_LICENSE = GPL-2.0-only

define DIAMOND3_BOARD_BUILD_CMDS
 $(TARGET_CC) $(TARGET_CFLAGS) -static -Wall -Wextra -o $(@D)/diamond3-init $(@D)/init.c $(TARGET_LDFLAGS)
 $(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -o $(@D)/diamond3-wheel $(@D)/wheel.c $(TARGET_LDFLAGS) -lm
endef

define DIAMOND3_BOARD_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/diamond3-wheel $(TARGET_DIR)/usr/sbin/diamond3-wheel
endef

$(eval $(kernel-module))
$(eval $(generic-package))
