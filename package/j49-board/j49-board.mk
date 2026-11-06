J49_BOARD_VERSION = 1
J49_BOARD_SITE = $(BR2_EXTERNAL_DIAMOND3_PATH)/package/j49-board/src
J49_BOARD_SITE_METHOD = local
J49_BOARD_LICENSE = GPL-2.0-only

define J49_BOARD_BUILD_CMDS
 $(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -o $(@D)/j49-wheel $(@D)/wheel.c $(TARGET_LDFLAGS)
endef

define J49_BOARD_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/j49-wheel $(TARGET_DIR)/usr/sbin/j49-wheel
endef

$(eval $(kernel-module))
$(eval $(generic-package))
