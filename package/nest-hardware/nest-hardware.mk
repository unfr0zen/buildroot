NEST_HARDWARE_VERSION = 1
NEST_HARDWARE_SITE = $(BR2_EXTERNAL_DIAMOND3_PATH)/package/nest-hardware/src
NEST_HARDWARE_SITE_METHOD = local
NEST_HARDWARE_LICENSE = GPL-2.0-only

define NEST_HARDWARE_BUILD_CMDS
 $(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -o $(@D)/nest-backplate $(@D)/backplate.c $(TARGET_LDFLAGS)
endef

define NEST_HARDWARE_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/nest-backplate $(TARGET_DIR)/usr/sbin/nest-backplate
endef

$(eval $(kernel-module))
$(eval $(generic-package))
