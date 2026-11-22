ONYX_BOARD_VERSION = 1
ONYX_BOARD_SITE = $(BR2_EXTERNAL_DIAMOND3_PATH)/package/onyx-board/src
ONYX_BOARD_SITE_METHOD = local
ONYX_BOARD_LICENSE = GPL-2.0-only

define ONYX_BOARD_BUILD_CMDS
 $(TARGET_CC) $(TARGET_CFLAGS) -static -Wall -Wextra -o $(@D)/onyx-init $(@D)/init.c $(TARGET_LDFLAGS)
 $(TARGET_CC) $(TARGET_CFLAGS) -DONYX -Wall -Wextra -o $(@D)/onyx-wheel $(BR2_EXTERNAL_DIAMOND3_PATH)/board/common/adc-wheel.c $(TARGET_LDFLAGS) -lm
endef

define ONYX_BOARD_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/onyx-wheel $(TARGET_DIR)/usr/sbin/onyx-wheel
endef

$(eval $(kernel-module))
$(eval $(generic-package))
