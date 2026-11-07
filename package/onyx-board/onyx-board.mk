ONYX_BOARD_VERSION = 1
ONYX_BOARD_SITE = $(BR2_EXTERNAL_DIAMOND3_PATH)/package/onyx-board/src
ONYX_BOARD_SITE_METHOD = local
ONYX_BOARD_LICENSE = GPL-2.0-only

define ONYX_BOARD_BUILD_CMDS
 $(TARGET_CC) $(TARGET_CFLAGS) -static -Wall -Wextra -o $(@D)/onyx-init $(@D)/init.c $(TARGET_LDFLAGS)
endef

$(eval $(kernel-module))
$(eval $(generic-package))
